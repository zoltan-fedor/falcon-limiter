""" The different utility functions available """


def get_remote_addr(req, resp, resource, params) -> str:
    """ Returns the remote address of the request to be used as a key for the limit

    See
    https://falcon.readthedocs.io/en/stable/api/request_and_response.html#falcon.Request.remote_addr

    Do NOT use it when you have reverse proxies in front of your application, as this only
    shows the last IP, alias the IP of the reverse proxy that sent the request to your application.
    In such case you should pick up the IP from the `req.access_route` list.
    """
    return req.remote_addr


def register(*decorators):
    """ This allows us to register multiple decorators and later being able to
    determine which decorators were registered on the given method

    This is necessary, because our decorators from Middlewares are just marking the method,
    so when the Middleware's process_request() method is called it can determine if the given
    endpoint is decorated, so it needs to take action. If there are multiple decorators,
    then it could only tell the topmost.
    Of you register the decorators with this register() method, then it will be able to tell
    that the method is decorated even if the given decorator is NOT the topmost.

    See https://stackoverflow.com/questions/3232024/introspection-to-get-decorator-names-on-a-method

    Use it as:
        class Foo(object):
            @register(many,decos,here)
            def bar(self):
                pass

        # print just the names of the decorators:
        print([d.func_name for d in foo.bar._decorators])
        >> ['many', 'decos', 'here']
    """
    def register_wrapper(func):
        for deco in decorators[::-1]:
            func = deco(func)
        func._decorators = decorators
        return func
    return register_wrapper
