
Recipes
=======

Application is served from behind a reverse proxy
-------------------------------------------------

Falcon applications are frequently served from behind loadbalancers and reverse proxies.
In such a case care must be given to pick up the right IP address - the one representing
the requestor and NOT the reverse proxy, otherwise you will be applying a shared rate limit
to all your users coming through that reverse proxy.

Usually the reverse proxy appends the IP address to one of the header (like X-Forwarded-For)
and in Falcon the list of IP addresses from those headers are amde available under the ``access_route``
Request attribute. See https://falcon.readthedocs.io/en/stable/api/request_and_response.html#falcon.Request.access_route

An example recipe to handle a single reverse proxy in front of our application is to provide
a custom key function which derives the requestor's IP address from the ``access_route``:

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
    )

    @limiter.limit()
    class ThingsResource:
        def on_post(self, req, resp):
            resp.body = 'Hello world!'
..

.. note::
    A custom key function must accept the 'usual' Falcon response attributes and return a string:

    `def custom_key_func(req, resp, resource, params) -> str:`


Ratelimit by resource and method
--------------------------------

A custom key function can be useful in other scenarios too, for example when you want to ratelimit
by resource and method. This is the scenario where you would want the ratelimit counted SEPARATELY
for each endpoint.

.. code-block:: python

    def get_key(req, resp, resource, params) -> str:
        """ Build a key from the IP + resource name + method name """
        user_key = get_remote_addr(req, resp, resource, params)
        return f"{user_key}:{resource.__class__.__name__}:{req.method}"

    limiter = Limiter(
        key_func=get_key,
        default_limits=["10 per hour", "2 per minute"]
    )
..


Ratelimit by user instead of IP
-------------------------------

A custom key function can be also be used to implement rate limit by authenticated user instead
of IP. This can be useful in scenarios when the users are coming from a proxied environment (like
most corporate environment), as they will be sharing the same public IP.

First you will need to authenticate your user and place the user id onto the request context,
so then your custom key function can pick it up from there.

.. code-block:: python

    def get_key_(req, resp, resource, params) -> str:
        """ Build a key from the user id stored on the request context
        or the IP when that is user id not available """
        if hasattr(req.context, 'user_id'):
            return req.context.user_id
        else:
            return get_remote_addr(req, resp, resource, params)

    limiter = Limiter(
        key_func=get_key,
        default_limits=["10 per hour", "2 per minute"]
    )
..


Customizing rate limits based on response
-----------------------------------------

For scenarios where the decision to count the current request towards a rate limit can only be
made after the request has completed, a callable can be provided.

The ``deduct_when`` function can be either provided to the ``Limiter`` as ``default_deduct_when``
parameter or to the decorator as ``deduct_when`` parameter.

.. code-block:: python

    import falcon
    from falcon_limiter import Limiter

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "2 per minute"],
        # this will apply to ALL limits:
        default_deduct_when=lambda req, resp, resource, req_succeeded: resp.status == falcon.HTTP_200
    )

    @limiter.limit()
    class ThingsResource:
        # this deduct when only applies to this method
        @limiter.limit(deduct_when=lambda req, resp, resource, req_succeeded: resp.status != falcon.HTTP_500)
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        def on_post(self, req, resp):
            resp.body = 'Hello world!'
..


.. note::
    The deduct_when function must accept the 'usual' Falcon response attributes and return a boolean:

    `def my_deduct_when_func(req, resp, resource, params) -> bool:`
