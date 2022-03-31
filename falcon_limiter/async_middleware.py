from falcon import HTTP_429, HTTPTooManyRequests, COMBINED_METHODS
from limits import parse as parse_limits
import logging
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple, Iterable, Union

if TYPE_CHECKING:
    from falcon_limiter.async_limiter import AsyncLimiter
    from limits import RateLimitItem

logger = logging.getLogger(__name__)

_DECORABLE_METHOD_NAME = re.compile(r'^on_({})(_\w+)?$'.format(
    '|'.join(method.lower() for method in COMBINED_METHODS)))


class Middleware:
    """ It integrates a Limiter object with Falcon by turning it into
    a Falcon Middleware
    """

    def __init__(self, limiter: 'AsyncLimiter') -> None:
        self.limiter = limiter

    async def process_resource(self, req, resp, resource, params):
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

            # # Get the argument values of wrap1() - which includes all the arguments used in the decorator
            # # see https://stackoverflow.com/questions/43353212/extracting-the-function-and-arguments-from-a-coroutine
            # if hasattr(getattr(resource, responder), 'cr_frame'):
            #     logger.debug(" This endpoint is decorated with a limit")
            # else:
            #     # no limit was requested on this responder as no decorator at all
            #     logger.debug(" No 'limit' was requested for this endpoint.")
            #     return
            #
            # args = getattr(resource, responder).cr_frame.f_locals
            # logger.debug(f"Arguments to the limit() decorator: {args}")
            # decorator_limits = args['limits'] if 'limits' in args else None
            # decorator_deduct_when = args['deduct_when'] if 'deduct_when' in args else None
            # decorator_key_func = args['key_func'] if 'key_func' in args else None
            # decorator_dynamic_limits = args['dynamic_limits'] if 'dynamic_limits' in args else None

            # is the given method (or its class) decorated by the limit_wrap being the topmost decorator?
            if responder_wrapper_name == 'limit_wrap':
                logger.debug(" This endpoint is decorated by 'limit' being the topmost decorator.")

                # the arguments provided in the decorator (if any):
                decorator_limits = getattr(getattr(resource, responder), '_AsyncLimiter__limits')
                decorator_deduct_when = getattr(getattr(resource, responder), '_AsyncLimiter__deduct_when')
                decorator_key_func = getattr(getattr(resource, responder), '_AsyncLimiter__key_func')
                decorator_dynamic_limits = getattr(getattr(resource, responder), '_AsyncLimiter__dynamic_limits')
            else:
                # 'limit_wrap' is not the topmost decorator - let's check whether 'limit' is
                # any of the other decorator on this method (not the topmost):
                # this requires the use of @register(decor1, decor2) as the decorator
                if hasattr(getattr(resource, responder), '_decorators') and \
                        'limit' in [d._decorator_name for d in getattr(resource, responder)._decorators
                                   if hasattr(d, '_decorator_name')]:

                    # pick up the limit decorator attributes from the wrap1 of the decorator:
                    for d in getattr(resource, responder)._decorators:
                        if hasattr(d, '_decorator_name') and getattr(d, '_decorator_name') == 'limit':
                            decorator_limits = getattr(d, '_limits')
                            decorator_deduct_when = getattr(d, '_deduct_when')
                            decorator_key_func = getattr(d, '_key_func')
                            decorator_dynamic_limits = getattr(d, '_dynamic_limits')
                            break

                    logger.debug(" This endpoint is decorated by 'limit', but it is NOT the topmost decorator.")
                else:
                    # no limit was requested on this responder as no decorator at all
                    logger.debug(" No 'limit' was requested for this endpoint.")
                    return

            logger.debug(" This endpoint is decorated with a limit")
            if not hasattr(resource, f'_{req.method}_limits'):
                _limits = decorator_limits if decorator_limits else self.limiter.default_limits
                setattr(resource, f'_{req.method}_limits', _limits)

                # parse the limits into a list of RateLimitItem objects
                _parsed_limits = await self.parse_limits(limits=_limits) if _limits else []

                setattr(resource, f'_{req.method}_parsed_limits', _parsed_limits)
                logger.debug(f" The limits parsed into RateLimitItem object(s) are: {_parsed_limits}")

                setattr(resource,
                        f'_{req.method}_key_func',
                        decorator_key_func if decorator_key_func else
                        self.limiter.key_func if hasattr(self.limiter, 'key_func') else None)
                setattr(resource,
                        f'_{req.method}_deduct_when',
                        decorator_deduct_when if decorator_deduct_when else
                        self.limiter.default_deduct_when if hasattr(self.limiter, 'default_deduct_when') else None)
                setattr(resource,
                        f'_{req.method}_dynamic_limits',
                        decorator_dynamic_limits if decorator_dynamic_limits else
                        self.limiter.default_dynamic_limits if hasattr(self.limiter, 'default_dynamic_limits')
                        else None)

        if not hasattr(resource, f'_{req.method}_limits'):
            logger.debug(" No limits on this resource/method.")
            return

        # get the attributes from the resource
        _limits = getattr(resource, f'_{req.method}_limits')
        _parsed_limits = getattr(resource, f'_{req.method}_parsed_limits')
        _key_func = getattr(resource, f'_{req.method}_key_func')
        _deduct_when = getattr(resource, f'_{req.method}_deduct_when')
        _dynamic_limits = getattr(resource, f'_{req.method}_dynamic_limits')
        logger.debug(f" The limits to be used: {_limits}")
        logger.debug(f" The parsed_limits to be used: {_parsed_limits}")
        logger.debug(f" The key_func function to be used: {_key_func}")
        logger.debug(f" The deduct_when function to be used: {_deduct_when}")
        logger.debug(f" The dynamic_limits function to be used: {_dynamic_limits}")

        # if dynamic limits have been requested, then that will overwrite whatever (if anything)
        # is provided via the 'limits'
        if _dynamic_limits:
            _limits = _dynamic_limits(req, resp, resource, params)
            # parse the limits into a list of RateLimitItem objects
            _parsed_limits = await self.parse_limits(limits=_limits) if _limits else []
        # print(_parsed_limits)

        if not _limits or not _parsed_limits:
            logger.debug(f" There was no 'limits' (or dynamic_limits) set on this endpoint,"
                         f" so no reason to check the limits.")
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
            if not await _hit_or_test(_limit, _key):
                logger.debug(f" Reached allowed limit '{_limit}' for key '{_key}'")
                resp.status = HTTP_429
                # outputing message: "Reached allowed limit 5 hits per 1 minute!"
                raise HTTPTooManyRequests(f"Reached allowed limit {str(_limit).replace(' per ', ' hits per ')}!")


    async def process_response(self, req, resp, resource, req_succeeded):
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
                    await self.limiter.limiter.hit(_limit, _key)

    @staticmethod
    async def parse_limits(limits: Union[str, Iterable[str]]) -> List['RateLimitItem']:
        """ Takes a string of limits (eg '5 per minute,2 per second') or an iterable
        of limits (eg ['5 per minute', '2 per second']) and sends each to be parsed into
        a proper rule and returns a List of these parsed rules.
        """
        # _limits might be an iterable - in which case we need to turn it into a string
        if not isinstance(limits, str):
            # 'limits' is an iterable
            limits = ';'.join(limits)
        return [parse_limits(l.strip()) for l in re.split(';|,', limits)]
