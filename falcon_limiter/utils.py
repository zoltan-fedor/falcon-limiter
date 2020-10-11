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
