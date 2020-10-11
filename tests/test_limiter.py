""" Test the different scenarios of limiter.py
"""
from falcon import API, testing, HTTP_200, HTTP_429
from falcon_limiter import Limiter
from falcon_limiter.utils import get_remote_addr
from time import sleep


def test_default_limit(limiter):
    """ Test the default limit applied through the class decorator
    """
    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        def some_other_method(self):
            pass

    app = API(middleware=limiter.middleware)
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


def test_no_limit(limiter):
    """ Test a no limit resource even when another resource has a limit
    """
    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    class ThingsResourceNoLimit:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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


def test_limit_on_method(limiter):
    """ Test the limit decorator on the method
    """
    class ThingsResource:
        @limiter.limit()
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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


def test_limit_on_method_overwrite(limiter):
    """ Test the limit decorator on the method overwriting the default limit
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @limiter.limit(limits="2 per second")
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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


def test_limit_on_method_overwrite_multiple(limiter):
    """ Test the limit decorator on the method overwriting the default limit
    with a combined limit
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @limiter.limit(limits="5 per hour;2 per second")
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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


def test_limit_on_method_overwrite_multiple_short_notation(limiter):
    """ Test the limit decorator on the method overwriting the default limit
    with a combined limit
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @limiter.limit(limits="5 per hour;2/second")
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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


def test_limit_as_iterable(limiter):
    """ The limit might be provided as an iterable
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @limiter.limit(limits=["5 per hour", "2 per second"])
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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


def test_limit_w_commas(limiter):
    """ The limit might be provided comma-separated
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @limiter.limit(limits="5 per hour,2 per second")
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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


def test_limit_w_semicol(limiter):
    """ The limit might be provided semicol-separated
    """
    class ThingsResource:
        # the default limit on 'limiter' is 1 per second
        @limiter.limit(limits="5 per hour;2 per second")
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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


def test_limit_class(limiter):
    """ Class level decorator overwriting the default
    """
    # the default limit on 'limiter' is 1 per second
    @limiter.limit(limits="5 per hour;2 per second")
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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


def test_limit_class_and_method(limiter):
    """ Class level decorator gets overwritten by the method level one
    """
    # the default limit on 'limiter' is 1 per second
    @limiter.limit(limits="5 per hour;2 per second")
    class ThingsResource:
        # also the limits are in an unusual order:
        @limiter.limit(limits="3 per second;5 per hour")
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
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

    limiter = Limiter(
        key_func=get_remote_addr
    )

    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    for i in range(5):
        r = client.simulate_get('/things')
        assert r.status == HTTP_200
