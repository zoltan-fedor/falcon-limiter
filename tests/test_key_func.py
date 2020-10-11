""" Tests with different key_func
"""
from falcon import API, testing, HTTP_200, HTTP_429
from falcon_limiter import Limiter
from falcon_limiter.utils import get_remote_addr
from time import sleep


def test_get_remote_addr():
    """ Test using the get_remote_addr() key function as default
    """

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"]
    )

    @limiter.limit()
    class ThingsResource:
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


def test_reverse_proxies():
    """ Test using a custom key_func - one which you would use to handle reverse proxies
    """

    def get_access_route_addr(req, resp, resource, params) -> str:
        """ Returns the remote address from the access_routes list discounting 1 reverse proxy
        """
        return req.access_route[-2]

    limiter = Limiter(
        key_func=get_access_route_addr,
        default_limits=["10 per hour", "1 per second"]
    )

    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    # two different source IPs through 1 reverse proxy:
    ip1_header = {"X-FORWARDED-FOR": "10.0.0.1, 1.2.3.4"}
    ip2_header = {"X-FORWARDED-FOR": "10.0.0.2, 1.2.3.4"}

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things', headers=ip1_header)
    assert r.status == HTTP_200

    # the same IP is denied
    r = client.simulate_get('/things', headers=ip1_header)
    assert r.status == HTTP_429

    # but a different IP can still access it
    r = client.simulate_get('/things', headers=ip2_header)
    assert r.status == HTTP_200


def test_limit_by_resource_and_method():
    """ Test using a custom key_func - one which creates different buckets by resource and method
    """

    def get_key(req, resp, resource, params) -> str:
        user_key = get_remote_addr(req, resp, resource, params)
        return f"{user_key}:{resource.__class__.__name__}:{req.method}"

    limiter = Limiter(
        key_func=get_key,
        default_limits=["10 per hour", "1 per second"]
    )

    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        def on_post(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    # but a different endpoint can still be hit
    r = client.simulate_post('/things')
    assert r.status == HTTP_200
