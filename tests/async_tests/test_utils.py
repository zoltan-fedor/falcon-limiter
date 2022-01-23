from falcon import asgi, testing
from falcon_limiter.utils import get_remote_addr


def test_get_remote_addr(asynclimiter):
    """ Test the utils.get_remote_addr() function which returns the requestor's ip

    Create an app with the default limiter and a method which is calling the get_remote_addr()
    """

    @asynclimiter.limit()
    class ThingsResource:
        async def on_get(self, req, resp):
            resp.body = 'Hello world!'
            assert '127.0.0.1' == get_remote_addr(req, resp, None, None)

    app = asgi.App(middleware=asynclimiter.middleware)
    things = ThingsResource()
    app.add_route('/things', things)

    client = testing.TestClient(app)
    client.simulate_get('/things')
