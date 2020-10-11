""" Testing the deduct_when option
"""
from falcon import API, testing, HTTP_200, HTTP_429, HTTP_500
from falcon_limiter import Limiter
from falcon_limiter.utils import get_remote_addr
from time import sleep


def test_deduct_when_http200_as_default_deduct():
    """ Test using the default_deduct_when option to deduct only when the response is 200
    """

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"],
        default_deduct_when=lambda req, resp, resource, req_succeeded: resp.status == HTTP_200
    )

    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        def on_post(self, req, resp):
            resp.body = 'Hello world!'
            resp.status = HTTP_500

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)

    # this is a 500 response, so it should NOT count!
    r = client.simulate_post('/things')
    assert r.status == HTTP_500

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200


def test_deduct_when_http200_as_class_decorator():
    """ Test using the deduct_when option on a class decorator to deduct only when the response is 200
    """

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"]
    )

    @limiter.limit(deduct_when=lambda req, resp, resource, req_succeeded: resp.status == HTTP_200)
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        def on_post(self, req, resp):
            resp.body = 'Hello world!'
            resp.status = HTTP_500

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)

    # this is a 500 response, so it should NOT count!
    r = client.simulate_post('/things')
    assert r.status == HTTP_500

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200



def test_deduct_when_http200_as_method_decorator():
    """ Test using the deduct_when option on a method decorator to deduct only when the response is 200
    """

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"]
    )

    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        @limiter.limit(deduct_when=lambda req, resp, resource, req_succeeded: resp.status == HTTP_200)
        def on_post(self, req, resp):
            resp.body = 'Hello world!'
            resp.status = HTTP_500

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)

    # this is a 500 response, so it should NOT count!
    r = client.simulate_post('/things')
    assert r.status == HTTP_500

    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200
