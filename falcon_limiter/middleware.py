from falcon import HTTP_429, HTTPTooManyRequests, COMBINED_METHODS
from limits import parse as parse_limits
import logging
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple

if TYPE_CHECKING:
    from falcon_limiter.limiter import Limiter

logger = logging.getLogger(__name__)

_DECORABLE_METHOD_NAME = re.compile(r'^on_({})(_\w+)?$'.format(
    '|'.join(method.lower() for method in COMBINED_METHODS)))


class Middleware:
    """ It integrates a Limiter object with Falcon by turning it into
    a Falcon Middleware
    """

    def __init__(self, limiter: 'Limiter') -> None:
        self.limiter = limiter

    def process_resource(self, req, resp, resource, params):
        """ Determine if the given request is marked for limiting and if yes,
        then whether it should be counted against the limit and check whether it is above the limit
        """
        ########
        # Step 1: determine whether the given responder has a limit setup
        # and if not then short-circuit
        # if there is a limit, then store that, the parsed limit, the key_func and the deduct_when
        # on the resource for each method

        # find out which responder ("on_..." method) is going to be used to process this request
        responder = None
        for _method in dir(resource):
            if _DECORABLE_METHOD_NAME.match(_method) and _method[3:].upper() == req.method.upper():
                responder = _method
                break

        if responder:
            # get the name of the responder wrapper, which for objects decorated with a limiter is 'limit_wrap'
            # see the "Limiter.limit" decorator in limiter.py
            responder_wrapper_name = getattr(getattr(resource, responder), '__name__')

            # is the given method (or its class) decorated?
            if responder_wrapper_name == 'limit_wrap':
                logger.debug(" This endpoint is decorated with a limit")
                # the arguments provided in the decorator (if any):
                decorator_limits = getattr(getattr(resource, responder), '_Limiter__limits')
                decorator_deduct_when = getattr(getattr(resource, responder), '_Limiter__deduct_when')

                # set the 'limits', 'parsed_limits', 'key_func' and 'deduct_when' on the resource if doesn't exist yet
                if not hasattr(resource, f'_{req.method}_limits'):
                    _limits = decorator_limits if decorator_limits else self.limiter.default_limits
                    setattr(resource, f'_{req.method}_limits', _limits)

                    # parse the limits into a list of RateLimitItem objects
                    if _limits:
                        # _limits might be an iterable - in which case we need to turn it into a string
                        if not isinstance(_limits, str):
                            # '_limits' is an iterable
                            _limits = ';'.join(_limits)
                        _parsed_limits = [parse_limits(l.strip()) for l in re.split(';|,', _limits)]
                    else:
                        _parsed_limits = []

                    setattr(resource, f'_{req.method}_parsed_limits', _parsed_limits)
                    logger.debug(f" The limits parsed into RateLimitItem object(s) are: {_parsed_limits}")

                    setattr(resource, f'_{req.method}_key_func', self.limiter.key_func)
                    setattr(resource,
                            f'_{req.method}_deduct_when',
                            decorator_deduct_when if decorator_deduct_when else
                            self.limiter.default_deduct_when if hasattr(self.limiter, 'default_deduct_when') else None)
            else:
                # no limiter was requested on this responder
                logger.debug(" No limiter was requested for this endpoint.")
                return

        _limits = getattr(resource, f'_{req.method}_limits')
        _parsed_limits = getattr(resource, f'_{req.method}_parsed_limits')
        _key_func = getattr(resource, f'_{req.method}_key_func')
        _deduct_when = getattr(resource, f'_{req.method}_deduct_when')
        logger.debug(f" The limits to be used: {_limits}")
        logger.debug(f" The parsed_limits to be used: {_parsed_limits}")
        logger.debug(f" The key_func function to be used: {_key_func}")
        logger.debug(f" The deduct_when function to be used: {_deduct_when}")

        if not _limits:
            logger.debug(f" There was no 'limits' set on this endpoint, so no reason to check the limits.")
            return

        #########
        # Step 2: hit the limit(s) of the given key and throw error 429 if we are above

        # build the key with the key prefix and the key_func provided
        if 'RATELIMIT_KEY_PREFIX' in self.limiter.config and self.limiter.config['RATELIMIT_KEY_PREFIX']:
            _key = "{key_prefix}:{key}".format(
                key_prefix=self.limiter.config['RATELIMIT_KEY_PREFIX'],
                key=_key_func(req, resp, resource, params))
        else:
            _key = str(_key_func(req, resp, resource, params))
        logger.debug(f" Key to be used: {_key}")

        # if 'deduct_when' is set, then we will need the key later in the process_response():
        if _deduct_when:
            req.context.ratelimit_key = _key

        # Are we hitting (eg testing+incrementing) or just testing the limit?
        # When there is a 'deduct_when' then we are only testing here and
        # we will be hitting (eg incrementing) in the process_response()
        _hit_or_test = self.limiter.limiter.test if _deduct_when else self.limiter.limiter.hit

        # hit/test each limit
        for _limit in _parsed_limits:
            # hit/test the given limit for the given key and error out if failing
            # https://limits.readthedocs.io/en/stable/api.html#limits.strategies.RateLimiter.hit
            if not _hit_or_test(_limit, _key):
                logger.debug(f" Reached allowed limit '{_limit}' for key '{_key}'")
                resp.status = HTTP_429
                # outputing message: "Reached allowed allowed limit 5 hits per 1 minute!"
                raise HTTPTooManyRequests(f"Reached allowed limit {str(_limit).replace(' per ', ' hits per ')}!")

    def process_response(self, req, resp, resource, req_succeeded):
        """ Hit the limit after the response was processed if the 'deduct_when' is set,
        as that requires information about the response before it can determine whether this
        request should be counted against the limit
        """

        # when there is a 'deduct_when' then we were only testing the limit in process_resource() and
        # actually NOT hitting (incrementing) the counters. Here in the response we need to increment
        # the counters now by actually "hitting" the limits.
        if hasattr(resource, f'_{req.method}_deduct_when') and getattr(resource, f'_{req.method}_deduct_when'):
            _key = req.context.ratelimit_key
            _deduct_when = getattr(resource, f'_{req.method}_deduct_when')

            # if the deduct_when function returns True, then we hit the limits to increment their counters
            if _deduct_when(req, resp, resource, req_succeeded):
                # hit each limit
                for _limit in getattr(resource, f'_{req.method}_parsed_limits'):
                    # hit the given limit for the given key - but we don't care about the result,
                    # as we only use it to increment their counters
                    self.limiter.limiter.hit(_limit, _key)
