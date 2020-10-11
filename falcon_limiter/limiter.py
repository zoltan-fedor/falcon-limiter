"""
    falcon_limiter.limiter
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module contains the main Limiter class.

    :copyright: (c) 2020 by Zoltan Fedor.
    :license: MIT, see LICENSE for more details.
"""
import inspect
from limits.storage import storage_from_string, Storage
from limits.strategies import STRATEGIES, RateLimiter
import logging
from typing import Any, Callable, Dict, List, Optional

from falcon_limiter.middleware import Middleware, _DECORABLE_METHOD_NAME
from falcon_limiter.utils import get_remote_addr

logger = logging.getLogger(__name__)


class Limiter:
    """ This is the central class for the limiting

    You need to initialize this object to setup the attributes of the Limiter
    and then supply the object's middleware to the Falcon app.

    Args:
        key_func (callable): A function that will receive the usual falcon response method arguments
                            (req, resp, resource, params) and expected to return a string which will
                            be used as a representation of the user for whom the rate limit will apply.
        default_limits (str): Optional string of limit(s) separated by ";", like '1/second;3 per hour'
        default_deduct_when (callable): A function which determines at response time whether the given request
                                        should be counted against the limit or not. This allows the creation
                                        of strategies incorporating the response status code.
        config (dict of str): Optional config settings provided as a dictionary

    Attributes:
        key_func (callable): A function that will receive the usual falcon response method arguments
                             (req, resp, resource, params) and expected to return a string which will
                             be used as a representation of the user for whom the rate limit will apply.
        default_limits (str): Optional string of limit(s) separated by ";", like '1/second;3 per hour'
        config (dict of str): Config settings stored as a dictionary
        storage (:obj:`Storage`): The storage backend that will be used to store the ratelimits.
        limiter (:obj:`RateLimiter`): A `RateLimiter` object from the `limits` library, representing the ratelimiting
                                      strategy and storage.
    """

    def __init__(self,
                 key_func: Callable=get_remote_addr,
                 default_limits: str='',
                 default_deduct_when: Callable=None,
                 config: Optional[Dict[str, Any]]=None) -> None:

        if not config:
            config = {}

        # set the defaults for the config
        config.setdefault('RATELIMIT_STORAGE_URL', 'memory://')
        config.setdefault('RATELIMIT_STORAGE_OPTIONS', {})
        config.setdefault('RATELIMIT_STRATEGY', 'fixed-window')
        config.setdefault('RATELIMIT_KEY_PREFIX', '')

        self.key_func = key_func
        self.default_limits = default_limits
        self.default_deduct_when = default_deduct_when
        self.config = config

        self.storage = storage_from_string(self.config['RATELIMIT_STORAGE_URL'],
                                           **self.config['RATELIMIT_STORAGE_OPTIONS'])

        self.limiter = STRATEGIES[self.config['RATELIMIT_STRATEGY']](self.storage)

        if not self.storage.check():
            logger.error(f"The storage backend has failed its check, please verify the provided storage settings!")

    @property
    def middleware(self) -> 'Middleware':
        """ Falcon middleware integration
        """
        return Middleware(limiter=self)

    def limit(self, limits: str=None, deduct_when: Callable=None):
        """ This is the decorator used to decorate a resource class or the requested
        method of the resource class with the default or with a custom limit


        Args:
            limits (str): Optional string of limit(s) separated by ";", like '1/second;3 per hour'
                          deduct_when (callable): A function that will receive the usual falcon
                          response method arguments (req, resp, resource, params) and expected to return a
                          boolean which is used to determine if the given response qualifies to count
                          against the set limit.
            deduct_when (callable): A function which determines at response time whether the given request
                                    should be counted against the limit or not. This allows the creation
                                    of strategies incorporating the response status code.
        """
        def wrap1(class_or_method, *args):
            # is this about decorating a class or a given method?
            if inspect.isclass(class_or_method):
                # get all methods of the class that needs to be decorated (eg start with "on_"):
                for attr in dir(class_or_method):
                    if callable(getattr(class_or_method, attr)) and _DECORABLE_METHOD_NAME.match(attr):
                        # decorate the given method, but not if it was already
                        # decorated on the method level
                        if not hasattr(getattr(class_or_method, attr), '_Limiter__limits_decorated'):
                            setattr(class_or_method, attr, wrap1(getattr(class_or_method, attr)))

                return class_or_method
            else:  # this is to decorate the individual method
                def limit_wrap(cls, req, resp, *args, **kwargs):
                    class_or_method(cls, req, resp, *args, **kwargs)

                # mark the fact that this method has already been decorated:
                limit_wrap.__limits_decorated = True

                # store the 'limits' an 'deduct_when' arguments of the decorator on the function, so
                # it can be picked up in the process_resource method in middleware.py
                limit_wrap.__limits = limits
                limit_wrap.__deduct_when = deduct_when

                return limit_wrap

        return wrap1
