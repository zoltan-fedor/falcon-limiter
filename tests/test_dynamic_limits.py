""" Testing the dynamic_limits option
"""
from falcon import API, testing, HTTP_200, HTTP_429, HTTP_500
from falcon_limiter import Limiter
from falcon_limiter.utils import get_remote_addr
from time import sleep


def test_default_dynamic_limits():
    """ Test using the default_dynamic_limits option to change the limit per user
    """

    limiter = Limiter(
        key_func=get_remote_addr,
        default_dynamic_limits=lambda req, resp, resource, req_succeeded: '5/second'
            if req.get_header('APIUSER') == 'admin' else '2/second'
    )

    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)

    ####
    # 'normal' user - errors after more than 2 calls per sec
    r = client.simulate_get('/things')
    assert r.status == HTTP_200
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 2/second limit
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    #########
    # 'admin' user should be able to make 5 calls
    admin_header = {"APIUSER": "admin"}
    for i in range(5):
        r = client.simulate_get('/things', headers=admin_header)
        assert r.status == HTTP_200

    # at the 6th hit even the admin user will error:
    r = client.simulate_get('/things', headers=admin_header)
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things', headers=admin_header)
    assert r.status == HTTP_200


def test_dynamic_limits_on_method():
    """ Test using the dynamic_limits param of the method decorators to change the limit per user
    """

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"]
    )

    class ThingsResource:
        @limiter.limit(dynamic_limits=lambda req, resp, resource, req_succeeded: '5/second'
            if req.get_header('APIUSER') == 'admin' else '2/second')
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        def on_post(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)

    ####
    # 'normal' user - errors after more than 2 calls per sec
    r = client.simulate_get('/things')
    assert r.status == HTTP_200
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 2/second limit
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    #########
    # 'admin' user should be able to make 5 calls
    admin_header = {"APIUSER": "admin"}
    for i in range(5):
        r = client.simulate_get('/things', headers=admin_header)
        assert r.status == HTTP_200

    # at the 6th hit even the admin user will error:
    r = client.simulate_get('/things', headers=admin_header)
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things', headers=admin_header)
    assert r.status == HTTP_200

    ########
    # unlimited number of calls to the unlimited on_post() method
    for i in range(8):
        r = client.simulate_post('/things')
        assert r.status == HTTP_200


def test_dynamic_limits_on_method2():
    """ Test using the dynamic_limits param of the method decorators to change the limit per user

    Overwriting the default limits from the class level decortor
    """

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"]
    )

    @limiter.limit()
    class ThingsResource:
        @limiter.limit(dynamic_limits=lambda req, resp, resource, req_succeeded: '5/second'
            if req.get_header('APIUSER') == 'admin' else '2/second')
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        def on_post(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)

    ####
    # 'normal' user - errors after more than 2 calls per sec
    r = client.simulate_get('/things')
    assert r.status == HTTP_200
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 2/second limit
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    #########
    # 'admin' user should be able to make 5 calls
    admin_header = {"APIUSER": "admin"}
    for i in range(5):
        r = client.simulate_get('/things', headers=admin_header)
        assert r.status == HTTP_200

    # at the 6th hit even the admin user will error:
    r = client.simulate_get('/things', headers=admin_header)
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things', headers=admin_header)
    assert r.status == HTTP_200

    ########
    # the on_post() method gets the default limit - 1 per second
    r = client.simulate_post('/things', headers=admin_header)
    assert r.status == HTTP_200

    r = client.simulate_post('/things', headers=admin_header)
    assert r.status == HTTP_429


def test_dynamic_limits_on_class():
    """ Test using the dynamic_limits param of the class decorators to change the limit per user
    """

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits=["10 per hour", "1 per second"]
    )

    @limiter.limit(dynamic_limits=lambda req, resp, resource, req_succeeded: '5/second'
        if req.get_header('APIUSER') == 'admin' else '2/second')
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        @limiter.limit(limits="3/second")
        def on_post(self, req, resp):
            resp.body = 'Hello world!'

    app = API(middleware=limiter.middleware)
    app.add_route('/things', ThingsResource())

    client = testing.TestClient(app)

    ####
    # 'normal' user - errors after more than 2 calls per sec
    r = client.simulate_get('/things')
    assert r.status == HTTP_200
    r = client.simulate_get('/things')
    assert r.status == HTTP_200

    # due to the 2/second limit
    r = client.simulate_get('/things')
    assert r.status == HTTP_429

    #########
    # 'admin' user should be able to make 5 calls
    admin_header = {"APIUSER": "admin"}
    for i in range(5):
        r = client.simulate_get('/things', headers=admin_header)
        assert r.status == HTTP_200

    # at the 6th hit even the admin user will error:
    r = client.simulate_get('/things', headers=admin_header)
    assert r.status == HTTP_429

    sleep(1)
    r = client.simulate_get('/things', headers=admin_header)
    assert r.status == HTTP_200

    ########
    # the on_post() method has a limit of 3/second - for normal users
    for i in range(3):
        r = client.simulate_post('/things')
        assert r.status == HTTP_200

    r = client.simulate_post('/things')
    assert r.status == HTTP_429

    ########
    # the on_post() method has a limit of 3/second - for admin users too
    sleep(1)
    for i in range(3):
        r = client.simulate_post('/things', headers=admin_header)
        assert r.status == HTTP_200

    r = client.simulate_post('/things', headers=admin_header)
    assert r.status == HTTP_429
