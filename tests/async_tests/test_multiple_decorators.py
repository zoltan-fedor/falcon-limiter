""" Testing scenarios when there are multiple decorators in different order
"""
from falcon import asgi, testing, HTTP_200, HTTP_429, HTTP_405
from falcon_limiter import AsyncLimiter
from falcon_limiter.utils import get_remote_addr
from falcon_limiter.utils import register
from time import sleep

import logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


def async_decorator(f):
    """ Just a random decorator for testing purposes
    """
    async def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def sync_decorator(f):
    """ Just a random decorator for testing purposes
    """
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def test_multiple_decorators_on_method(asynclimiter):
    """ Test having multiple decorators on a method
    """
    class ThingsResource:
        @asynclimiter.limit()
        @async_decorator
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

        @async_decorator
        @asynclimiter.limit()
        async def on_post(self, req, resp):
            resp.body = 'Hello world!'

        @register(async_decorator, asynclimiter.limit())
        async def on_put(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    #####
    # test the on_get(), when the other decorator is first
    # THIS WILL WORK - as the @limiter decorator is the first decorator
    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    #####
    # test the on_post(), when the other decorator is first
    # THIS WILL FAIL - meaning no limit is applied, because the @limiter decorator is NOT
    # the first and register() was not used
    sleep(1)
    client = testing.TestClient(app)
    r = client.simulate_post('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter, this should return 429,
    # but because the decorator is not the first, it will not have a rate limit, so
    # it returns 200
    r = client.simulate_post('/things')
    assert r.status == HTTP_200

    #####
    # test the on_putt(), when the other decorator is not the first,
    # but the decorators are registered via register()
    # THIS WILL WORK - as the @limiter decorator is not the first decorator, but the register() was used
    sleep(1)
    client = testing.TestClient(app)
    r = client.simulate_put('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter
    r = client.simulate_put('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_put('/things')
    assert r.status == HTTP_200


def test_multiple_decorators_on_class(asynclimiter):
    """ Test having multiple decorators on a class
    """
    @register(sync_decorator, asynclimiter.limit())
    class ThingsResource:
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200
