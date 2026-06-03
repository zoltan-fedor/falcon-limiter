""" While the different backends are provided by the 'limits' library,
so strictly speaking we wouldn't need to test it - we are going to test Redis,
our most popular backend
"""
import asyncio
from falcon import asgi, testing, HTTP_200, HTTP_429
from falcon_limiter import AsyncLimiter
from falcon_limiter.utils import get_remote_addr
from tests.conftest import REDIS_PORT


def test_redis(redis_server):
    """ Test using the redis backend
    """
    asyncio.run(_test_redis())


async def _test_redis():
    limiter = AsyncLimiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"],
        config={
            'RATELIMIT_KEY_PREFIX': 'myapp',
            'RATELIMIT_STORAGE_URL': f'async+redis://@localhost:{REDIS_PORT}'
        }
    )

    # Initialize the async Redis backend
    await limiter.initialize()
    await limiter.storage.reset()

    @limiter.limit()
    class ThingsResource:
        async def on_get(self, req, resp):
            resp.text = 'Hello world!'

    app = asgi.App(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    try:
        client = testing.ASGIConductor(app)
        r = await client.simulate_get('/things')
        assert r.status == HTTP_200

        # due to the 1 second default limit on the default limiter
        r = await client.simulate_get('/things')
        assert r.status == HTTP_429

        await asyncio.sleep(1)
        r = await client.simulate_get('/things')
        assert r.status == HTTP_200
    finally:
        await limiter.close()
