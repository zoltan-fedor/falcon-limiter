"""
    falcon_limiter.async_limiter
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module contains the async Limiter class.

    :copyright: (c) 2022 by Zoltan Fedor.
    :license: MIT, see LICENSE for more details.
"""
import asyncio
import inspect
from limits.storage import storage_from_string, Storage
from limits.aio.strategies import STRATEGIES, RateLimiter
import logging
from typing import Any, Callable, Dict, List, Optional

from falcon_limiter.async_middleware import Middleware, _DECORABLE_METHOD_NAME
from falcon_limiter.utils import get_remote_addr

logger = logging.getLogger(__name__)


class AsyncLimiter:
    """ This is the central class for the limiting

    You need to initialize this object to setup the attributes of the Limiter
    and then supply the object's middleware to the Falcon app.

    Args:
        key_func (callable): A function that will receive the usual Falcon request method arguments
                            (req, resp, resource, params) and expected to return a string which will
                            be used as a representation of the user for whom the rate limit will apply
                            (eg the key).
        default_limits (str): Optional string of limit(s) separated by ";", like '1/second;3 per hour'
        default_deduct_when (callable): A function which determines at response time whether the given request
                                        should be counted against the limit or not. This allows the creation
                                        of strategies incorporating the response status code.
        default_dynamic_limits (callable): A function which builds the 'limits' string dynamically
                                           based on the Falcon request method arguments (req, resp, resource, params).
                                           It is expected to return a 'limits' string like '1/second;3 per hour'.
        config (dict of str): Optional config settings provided as a dictionary

    Attributes:
        key_func (callable): A function that will receive the usual Falcon request method arguments
                             (req, resp, resource, params) and expected to return a string which will
                             be used as a representation of the user for whom the rate limit will apply
                             (eg the key).
        default_limits (str): Optional string of limit(s) separated by ";", like '1/second;3 per hour'
        default_deduct_when (callable): A function which determines at response time whether the given request
                                        should be counted against the limit or not. This allows the creation
                                        of strategies incorporating the response status code.
        default_dynamic_limits (callable): A function which builds the 'limits' string dynamically
                                           based on the Falcon request method arguments (req, resp, resource, params).
                                           It is expected to return a 'limits' string like '1/second;3 per hour'.
        config (dict of str): Config settings stored as a dictionary
        storage (:obj:`Storage`): The storage backend that will be used to store the rate limits.
        limiter (:obj:`RateLimiter`): A `RateLimiter` object from the `limits` library, representing the rate limiting
                                      strategy and storage.
    """

    def __init__(self,
                 key_func: Callable=get_remote_addr,
                 default_limits: str='',
                 default_deduct_when: Callable=None,
                 default_dynamic_limits: Callable=None,
                 config: Optional[Dict[str, Any]]=None) -> None:

        if not config:
            config = {}

        # set the defaults for the config
        config.setdefault('RATELIMIT_STORAGE_URL', 'async+memory://')
        config.setdefault('RATELIMIT_STORAGE_OPTIONS', {})
        config.setdefault('RATELIMIT_STRATEGY', 'fixed-window')
        config.setdefault('RATELIMIT_KEY_PREFIX', '')

        self.key_func = key_func
        self.default_limits = default_limits
        self.default_deduct_when = default_deduct_when
        self.default_dynamic_limits = default_dynamic_limits
        self.config = config

        self.storage = storage_from_string(self.config['RATELIMIT_STORAGE_URL'],
                                           **self.config['RATELIMIT_STORAGE_OPTIONS'])

        self.limiter = STRATEGIES[self.config['RATELIMIT_STRATEGY']](self.storage)
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the async storage backend.

        For network backends exposing an async context manager, this enters the
        underlying client's async context manager. For in-memory backends, this
        is a no-op.

        Can also be used as an async context manager::

            async with limiter:
                # limiter is initialized here
                app = asgi.App(middleware=limiter.middleware)
        """
        async with self._init_lock:
            if self._initialized:
                return

            storage_client = getattr(getattr(self.storage, 'bridge', None), 'storage', None)
            context_enter = getattr(storage_client, '__aenter__', None)
            if context_enter:
                await context_enter()
            elif not self.config['RATELIMIT_STORAGE_URL'].startswith(('memory://', 'async+memory://')):
                logger.warning(
                    "Could not find async context manager on storage backend '%s'. "
                    "The limits library internals may have changed. "
                    "Network-based storage backends may not work correctly.",
                    self.config['RATELIMIT_STORAGE_URL'],
                )

            self._initialized = True

            check = getattr(self.storage, 'check', None)
            if check:
                result = check()
                if inspect.isawaitable(result):
                    result = await result
                if not result:
                    logger.error("The storage backend has failed its check, please verify the provided storage settings!")

    async def close(self) -> None:
        """Close the async storage backend and release resources.

        For network backends exposing an async context manager, this exits the
        underlying client's async context manager.
        """
        async with self._init_lock:
            if not self._initialized:
                return

            storage_client = getattr(getattr(self.storage, 'bridge', None), 'storage', None)
            context_exit = getattr(storage_client, '__aexit__', None)
            if context_exit:
                await context_exit(None, None, None)

            self._initialized = False

    async def __aenter__(self) -> 'AsyncLimiter':
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @property
    def middleware(self) -> 'Middleware':
        """ Falcon middleware integration
        """
        return Middleware(limiter=self)

    def limit(self, limits: str=None, deduct_when: Callable=None,
              key_func: Callable=None, dynamic_limits: Callable=None) -> Callable:
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
            key_func (callable): A function that will receive the usual falcon response method arguments
                                 (req, resp, resource, params) and expected to return a string which will
                                 be used as a representation of the user for whom the rate limit will apply
                                 (eg the key).
            dynamic_limits (callable): A function which builds the 'limits' string dynamically
                                       based on the Falcon request method arguments (req, resp, resource, params).
                                       It is expected to return a 'limits' string like '1/second;3 per hour'.
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
                async def limit_wrap(cls, req, resp, *args, **kwargs):
                    await class_or_method(cls, req, resp, *args, **kwargs)

                # mark the fact that this method has already been decorated:
                limit_wrap.__limits_decorated = True

                # store the arguments of the decorator on the function, so
                # these can be picked up in the process_resource method in middleware.py
                limit_wrap.__limits = limits
                limit_wrap.__deduct_when = deduct_when
                limit_wrap.__key_func = key_func
                limit_wrap.__dynamic_limits = dynamic_limits

                return limit_wrap

        # this is the name which will check for if the decorator was registered with the register()
        # function, as this decorator is not the topmost one
        wrap1._decorator_name = 'limit'  # type: ignore

        # store the arguments of the decorator on the wrap1 function too
        # - for when there are multiple decorators registered with the register() utility,
        # so these can be picked up in the process_resource method in middleware.py
        wrap1._limits = limits  # type: ignore
        wrap1._deduct_when = deduct_when  # type: ignore
        wrap1._key_func = key_func  # type: ignore
        wrap1._dynamic_limits = dynamic_limits  # type: ignore

        return wrap1
