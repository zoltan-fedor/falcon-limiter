import asyncio
import errno
import warnings
import pytest

from falcon import asgi, App, testing
from falcon_limiter import Limiter, AsyncLimiter
from falcon_limiter.utils import get_remote_addr

try:
    __import__("xprocess")
    from xprocess import ProcessStarter
except ImportError:
    @pytest.fixture(scope="session")
    def xprocess():
        pytest.skip("pytest-xprocess not installed.")

# the different strategies that will be tested
STRATEGIES = [
    'fixed-window',
    'fixed-window-elastic-expiry',
    'moving-window'
]

# which port the Redis server will be listening on
# which is started by xprocess
REDIS_PORT = 63799


@pytest.fixture(autouse=True)
def _ensure_event_loop():
    """Ensure an event loop exists for Python 3.10 compatibility."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())


# parametrized fixture to create limiters with different strategies
@pytest.fixture(params=STRATEGIES)
def limiter(request):
    """ Create a basic limiter
    """
    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"]
    )
    return limiter


# parametrized fixture to create limiters with different strategies
@pytest.fixture(params=STRATEGIES)
def asynclimiter(request):
    """ Create a basic limiter
    """
    limiter = AsyncLimiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"]
    )
    return limiter


@pytest.fixture(scope="class")
def redis_server(xprocess):
    try:
        import redis
    except ImportError:
        pytest.skip("Python package 'redis' is not installed.")

    class Starter(ProcessStarter):
        pattern = "[Rr]eady to accept connections"
        args = ["redis-server", "--port", REDIS_PORT]

    try:
        xprocess.ensure("redis_server", Starter)
    except IOError as e:
        # xprocess raises FileNotFoundError
        if e.errno == errno.ENOENT:
            pytest.skip("Redis is not installed.")
        else:
            raise

    yield
    xprocess.getinfo("redis_server").terminate()


@pytest.fixture()
def app(request, limiter):
    """ Creates a Falcon app with the default limiter
    """

    @limiter.limit()
    class ThingsResource:
        # unmarked methods will use the default limit
        def on_get(self, req, resp):
            resp.text = 'Hello world!'

        # mark this method with a special limit
        # which will overwrite the default
        @limiter.limit(limits="1 per day")
        def on_post(self, req, resp):
            pass

    # a resource with no limits:
    class ThingsResourceNoLimit:
        # unmarked methods will use the default limit
        def on_get(self, req, resp):
            pass

    # add the limiter middleware to the Falcon app
    app = App(middleware=limiter.middleware)

    things = ThingsResource()
    thingsnolimit = ThingsResourceNoLimit()

    app.add_route('/things', things)
    app.add_route('/thingsnolimit', thingsnolimit)

    return app


@pytest.fixture()
def asyncapp(request, asynclimiter):
    """ Creates a Falcon app with the default limiter
    """

    @asynclimiter.limit()
    class ThingsResource:
        # unmarked methods will use the default limit
        async def on_get(self, req, resp):
            resp.text = 'Hello world!'

        # mark this method with a special limit
        # which will overwrite the default
        @asynclimiter.limit(limits="1 per day")
        async def on_post(self, req, resp):
            pass

    # a resource with no limits:
    class ThingsResourceNoLimit:
        # unmarked methods will use the default limit
        async def on_get(self, req, resp):
            pass

    # add the limiter middleware to the Falcon app
    app = asgi.App(middleware=asynclimiter.middleware)

    things = ThingsResource()
    thingsnolimit = ThingsResourceNoLimit()

    app.add_route('/things', things)
    app.add_route('/thingsnolimit', thingsnolimit)

    return app

@pytest.fixture()
def client(app):
    """ Creates a Falcon test client
    """
    return testing.TestClient(app)


@pytest.fixture()
def asyncclient(asyncapp):
    """ Creates a Falcon test client
    """
    return testing.TestClient(asyncapp)

