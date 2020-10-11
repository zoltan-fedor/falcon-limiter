Quickstart
----------

Quick example - using `fixed-window` strategy and storing the hits against limits in the memory:

.. code-block:: python

    import falcon
    from falcon_limiter import Limiter
    from falcon_limiter.utils import get_remote_addr

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits="5 per minute,2 per second"
    )

    # use the default limit for all methods of this class
    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    # add the limiter middleware to the Falcon app
    app = falcon.API(middleware=limiter.middleware)

    things = ThingsResource()
    app.add_route('/things', things)
..

When making calls against this app, above >5 calls per minute or >2 per seconds you will receive
an HTTP 429 error response with message: `"Reached allowed limit 5 hits per 1 minute!"`


A second, more complicated example - using the `moving-window` strategy with a shared Redis backend
and running the application behind a reverse proxy:

.. code-block:: python

    import falcon
    from falcon_limiter import Limiter

    # a custom key function
    def get_access_route_addr(req, resp, resource, params) -> str:
        """ Get the requestor's IP by discounting 1 reverse proxy
        """
        return req.access_route[-2]

    limiter = Limiter(
        key_func=get_access_route_addr,
        default_limits="5 per minute,2 per second",
        # only count HTTP 200 responses against the limit:
        default_deduct_when=lambda req, resp, resource, req_succeeded: resp.status == falcon.HTTP_200,
        config={
            'RATELIMIT_KEY_PREFIX': 'myapp',  # to allow multiple apps in the same Redis db
            'RATELIMIT_STORAGE_URL': f'redis://:{REDIS_PSW}@{REDIS_HOST}:{REDIS_PORT}',
            'RATELIMIT_STRATEGY': 'moving-window'
        }
    )

    class ThingsResource:
        # no rate limit on this method
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        # a more strict rate limit applied to this method
        @limiter.limit(limits="3 per minute,1 per second")
        def on_post(self, req, resp):
            resp.body = 'Hello world!'

    # add the limiter middleware to the Falcon app
    app = falcon.API(middleware=limiter.middleware)

    things = ThingsResource()
    app.add_route('/things', things)
..
