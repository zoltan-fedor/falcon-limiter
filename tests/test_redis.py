""" While the different backends are provided by the 'limits' library,
so strictly speaking we wouldn't need to test it - we are going to test Redis,
our most popular backend
"""
from falcon import API, testing, HTTP_200, HTTP_429
from falcon_limiter import Limiter
from falcon_limiter.utils import get_remote_addr
from time import sleep
from tests.conftest import REDIS_PORT


def test_redis(redis_server):
    """ Test using the redis backend
    """

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"],
        config={
            'RATELIMIT_KEY_PREFIX': 'myapp',
            'RATELIMIT_STORAGE_URL': f'redis://@localhost:{REDIS_PORT}'
        }
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
