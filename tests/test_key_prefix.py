""" Tests the use of the key_prefix
"""
from falcon import API, testing, HTTP_200, HTTP_429
from falcon_limiter import Limiter
from falcon_limiter.utils import get_remote_addr
from time import sleep


def test_different_key_prefixes():
    """ Test using different key_prefixes
    """

    limiter1 = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"],
        config={
            'RATELIMIT_KEY_PREFIX': 'app1'
        }
    )

    @limiter1.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app1 = API(middleware=limiter1.middleware)
    app1.add_route('/things', ThingsResource())

    client1 = testing.TestClient(app1)
    r = client1.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter
    r = client1.simulate_get('/things')
    assert r.status == HTTP_429


    #####
    # app2 - with a different key

    limiter2 = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"],
        config={
            'RATELIMIT_KEY_PREFIX': 'app2'
        }
    )

    @limiter2.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app2 = API(middleware=limiter2.middleware)
    app2.add_route('/things', ThingsResource())

    client2 = testing.TestClient(app2)
    r = client2.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 1 second default limit on the default limiter
    r = client2.simulate_get('/things')
    assert r.status == HTTP_429
