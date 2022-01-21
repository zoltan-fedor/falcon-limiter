
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
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        # this endpoint is routed differently (through 2 proxies), so it
        # requires a custom key function specific to this method
        @limiter.limit(key_func=lambda req, resp, resource, params: req.access_route[-3])
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


Dynamic limits
--------------

With the use of the ``default_dynamic_limits`` and ``dynamic_limits`` parameters you can
define the limits dynamically, at the time of the processing of the request.

This allows you to define different limits by users - for example allowing an admin user
higher limit than others, or differentiating the limits based on the 'subscription' the
given requester belongs to.

.. code-block:: python

    from falcon_limiter.utils import get_remote_addr

    limiter = Limiter(
        key_func=get_remote_addr,
        # the default limit is 9999/second for admin and
        # 20/minute,2/second for everybody else:
        default_dynamic_limits=lambda req, resp, resource, params:
            '9999/second' if req.context.user == 'admin'
            else '20/minute,2/second'
    )

    @limiter.limit()
    class ThingsResource:
        # this endpoint gets a 5/second limit for those sending
        the APIUSER=admin header:
        @limiter.limit(dynamic_limits=lambda req, resp, resource, params:
            '5/second'if req.get_header('APIUSER') == 'admin'
            else '20/minute,2/second'
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        def on_post(self, req, resp):
            resp.body = 'Hello world!'

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
        default_deduct_when=lambda req, resp, resource, req_succeeded:
            resp.status == falcon.HTTP_200
    )

    @limiter.limit()
    class ThingsResource:
        # this deduct when only applies to this method
        @limiter.limit(deduct_when=lambda req, resp, resource, req_succeeded:
            resp.status != falcon.HTTP_500)
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        def on_post(self, req, resp):
            resp.body = 'Hello world!'
..


Multiple decorators
-------------------

For scenarios where there is a need for multiple decorators and the ``@limiter.limit()`` cannot be the
topmost one, we need to register the decorators a special way.

This scenario is complicated because our ``@limiter.limit()`` just marks the fact that the given
method is decorated with a limit, which later gets picked up by the middleware and triggers the rate limiting.
If the ``@limiter.limit()`` is the topmost
decorator then it is easy to pick that up, but if there are other decorators 'ahead' it, then those
will 'hide' the  ``@limiter.limit()``. This is because decorators in Python are just syntactic sugar
for nested function calls.

To be able to tell if the given endpoint was decorated by the ``@limiter.limit()`` decorator when that is NOT
the topmost decorator, you need to decorate your method by registering your decorators using the
``@register()`` helper decorator.

See more about this issue at
https://stackoverflow.com/questions/3232024/introspection-to-get-decorator-names-on-a-method


.. code-block:: python

    import falcon
    from falcon_limiter import Limiter
    from falcon_limiter.utils import register

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "2 per minute"]
    )


    class ThingsResource:
        # this is fine, as the @limiter.limit() is the topmost decorator:
        @limiter.limit()
        @another_decorator
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        # the @limiter.limit() is NOT the topmost decorator, so
        # this would NOT work - the limit would be ignored!!!!
        # DO NOT DO THIS:
        @another_decorator
        @limiter.limit()
        def on_post(self, req, resp):
            resp.body = 'WARNING: NO LIMITS ON THIS!'

        # instead register your decorators this way:
        @register(another_decorator, limiter.limit())
        def on_post(self, req, resp):
            resp.body = 'This is properly limited'

    app = falcon.API(middleware=limiter.middleware)
..



.. note::
    The deduct_when function must accept the 'usual' Falcon response attributes and return a boolean:

    `def my_deduct_when_func(req, resp, resource, params) -> bool:`
