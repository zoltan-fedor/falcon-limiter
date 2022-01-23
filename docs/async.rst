
async (experimental)
--------------------

.. versionadded:: 1.0
.. warning:: Experimental

Async (ASGI) support has been added in experimental mode, thanks to the
`Limits <https://github.com/alisaifee/limits>`_ library.

This was
implemented by the addition of ``falcon.limiter.AsyncLimiter`` module,
which copies the functionalities of ``falcon.limiter.Limiter``.

Use ``falcon.limiter.AsyncLimiter`` for Async (ASGI) and
``falcon.limiter.Limiter`` for WSGI.


The following async storage backends are implemented:

 - In-Memory
 - Redis (via `coredis <https://coredis.readthedocs.org>`_)
 - Memcached (via `emcache <https://emcache.readthedocs.org>`_)
 - MongoDB (via `motor <https://motor.readthedocs.org>`_)


Async examples
^^^^^^^^^^^^^^

A few examples to demonstrate the use of the async module.


1. A basic example using the In-Memory storage option

.. code-block:: python

    import falcon.asgi
    from falcon_limiter import AsyncLimiter
    from falcon_limiter.utils import get_remote_addr

    limiter = AsyncLimiter(
        key_func=get_remote_addr,
        default_limits="5 per minute,2 per second"
    )

    # use the default limit for all methods of this class
    @limiter.limit()
    class ThingsResource:
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    # add the limiter middleware to the Falcon app
    app = falcon.asgi.App(middleware=limiter.middleware)

    things = ThingsResource()
    app.add_route('/things', things)
..


2. Redis storage

.. code-block:: python

    import falcon.asgi
    from falcon_limiter import AsyncLimiter
    from falcon_limiter.utils import get_remote_addr
    import logging

    # include ERROR logs
    logging.basicConfig()
    logging.getLogger().setLevel(logging.ERROR)

    limiter = AsyncLimiter(
        key_func=get_remote_addr,
        default_limits=["500 per hour", "20 per minute"],
        config={
            'RATELIMIT_KEY_PREFIX': 'myapp',
            'RATELIMIT_STORAGE_URL': 'async+redis://:MyRedisPassword@localhost:6379'
        }
    )

    # The deduct_when function is NOT async!
    def deduct_when_func(req, resp, resource, req_succeeded):
        return resp.status == falcon.HTTP_200

    class ThingsResource:
        @limiter.limit(limits="2 per hour;1 per minute",
                       deduct_when=deduct_when_func)
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    # add the limiter middleware to the Falcon app
    app = falcon.asgi.App(middleware=limiter.middleware)

    things = ThingsResource()
    app.add_route('/things', things)
..


Please note, that when using the ``AsyncLimiter``, then a class-level decorator will overwrite
all method-level decorators of that class. This behaviour is different from the WSGI (eg sync)
``Limiter``, where method-level decorators overwrite the class level one.


