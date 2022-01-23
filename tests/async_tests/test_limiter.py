""" Test the different scenarios of limiter.py
"""
from falcon import asgi, testing, HTTP_200, HTTP_429, HTTP_405
from falcon_limiter import AsyncLimiter
from falcon_limiter.utils import get_remote_addr
from time import sleep


def test_default_limit(asynclimiter):
    """ Test the default limit applied through the class decorator
    """
    @asynclimiter.limit()
    class ThingsResource:
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

        async def some_other_method(self):
            pass

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


def test_no_limit(asynclimiter):
    """ Test a no limit resource even when another resource has a limit
    """
    @asynclimiter.limit()
    class ThingsResource:
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    class ThingsResourceNoLimit:
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())
    app.add_route('/thingsnolimit', ThingsResourceNoLimit())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    for i in range(3):
        r = client.simulate_get('/thingsnolimit')
        assert r.status == HTTP_200


def test_limit_on_method(asynclimiter):
    """ Test the limit decorator on the method
    """
    class ThingsResource:
        @asynclimiter.limit()
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


def test_limit_on_method_overwrite(asynclimiter):
    """ Test the limit decorator on the method overwriting the default limit
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @asynclimiter.limit(limits="2 per second")
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200


def test_limit_on_method_overwrite_multiple(asynclimiter):
    """ Test the limit decorator on the method overwriting the default limit
    with a combined limit
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @asynclimiter.limit(limits="5 per hour;2 per second")
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200


def test_limit_on_method_overwrite_multiple_short_notation(asynclimiter):
    """ Test the limit decorator on the method overwriting the default limit
    with a combined limit
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @asynclimiter.limit(limits="5 per hour;2/second")
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200


def test_limit_as_iterable(asynclimiter):
    """ The limit might be provided as an iterable
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @asynclimiter.limit(limits=["5 per hour", "2 per second"])
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200


def test_limit_w_commas(asynclimiter):
    """ The limit might be provided comma-separated
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @asynclimiter.limit(limits="5 per hour,2 per second")
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200


def test_limit_w_semicol(asynclimiter):
    """ The limit might be provided semicol-separated
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @asynclimiter.limit(limits="5 per hour;2 per second")
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200


def test_limit_class(asynclimiter):
    """ Class level decorator overwriting the default
    """
    # the default limit on 'limiter' is 1 per second
    @asynclimiter.limit(limits="5 per hour;2 per second")
    class ThingsResource:
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200


def test_limit_class_and_method(asynclimiter):
    """ Class level decorator overwrites the method level one

    IMPORTANT - this is different from the sync version of the limiter,
    where the class level decorator gets overwritten by the method level one
    """
    # also the limits are in an unusual order:
    @asynclimiter.limit(limits="3 per second;5 per hour")
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @asynclimiter.limit(limits="5 per hour;2 per second")
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200


def test_empy_limits():
    """ Test incorrect setup - empty limits!

    In this case there are NO limits applied
    """

    limiter = AsyncLimiter(
        key_func=get_remote_addr
    )

    @limiter.limit()
    class ThingsResource:
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    for i in range(5):
        r = client.simulate_get('/things')
        assert r.status == HTTP_200


def test_undefined_endpointasync(asynclimiter):
    """ Test calling a method which is not defined at all

    Our module should not error, but we should leave it to Falcon to handle it - and return a 405.
    """
    @asynclimiter.limit()
    class ThingsResource:
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = asgi.App(middleware=asynclimiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_post('/things')
    assert r.status == HTTP_405
