[![Build Status](https://travis-ci.com/zoltan-fedor/falcon-limiter.svg?branch=master)](https://travis-ci.com/zoltan-fedor/falcon-limiter)
[![codecov](https://codecov.io/gh/zoltan-fedor/falcon-limiter/branch/master/graph/badge.svg)](https://codecov.io/gh/zoltan-fedor/falcon-limiter)
[![Documentation Status](https://readthedocs.org/projects/falcon-limiter/badge/?version=latest)](https://falcon-limiter.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/zoltan-fedor/falcon-limiter)

# Falcon-Limiter

This library provides advanced rate limiting support for the [Falcon web framework](https://github.com/falconry/falcon).

Rate limiting is provided with the help of the popular [Limits](https://github.com/alisaifee/limits) library.

This library aims to be compatible with CPython 3.6+ and PyPy 3.5+.


## Documentation

You can find the documentation of this library on [Read the Docs](https://falcon-limiter.readthedocs.io/).


## Quickstart

Quick example - using `fixed-window` strategy and storing the hits against limits in the memory:
```
import falcon
from falcon_limiter import Limiter
from falcon_limiter.utils import get_remote_addr

limiter = Limiter(
    key_func=get_remote_addr,
    default_limits="5 per minute,2 per second"
)

# use the default limit for all methods of this class
@limiter.limit()
class ThingsResource:
    def on_get(self, req, resp):
        resp.body = 'Hello world!'

# add the limiter middleware to the Falcon app
app = falcon.API(middleware=limiter.middleware)

things = ThingsResource()
app.add_route('/things', things)
```

When making calls against this app, above >5 calls per minute or >2 per seconds you will receive
an HTTP 429 error response with message: `"Reached allowed limit 5 hits per 1 minute!"`

A second, more complicated example - using the `moving-window` strategy with a shared Redis backend
and running the application behind a reverse proxy behind a reverse proxy:
```
import falcon
from falcon_limiter import Limiter

# a custom key function
def get_access_route_addr(req, resp, resource, params) -> str:
    """ Get the requestor's IP by discounting 1 reverse proxy
    """
    return req.access_route[-2]

limiter = Limiter(
    key_func=get_access_route_addr,
    default_limits="5 per minute,2 per second",
    # only count HTTP 200 responses against the limit:
    default_deduct_when=lambda req, resp, resource, req_succeeded: resp.status == falcon.HTTP_200,
    config={
        'RATELIMIT_KEY_PREFIX': 'myapp',  # to allow multiple apps in the same Redis db
        'RATELIMIT_STORAGE_URL': f'redis://:{REDIS_PSW}@{REDIS_HOST}:{REDIS_PORT}',
        'RATELIMIT_STRATEGY': 'moving-window'
    }
)

class ThingsResource:
    # no rate limit on this method
    def on_get(self, req, resp):
        resp.body = 'Hello world!'

    # a more strict rate limit applied to this method
    @limiter.limit(limits="3 per minute,1 per second")
    def on_post(self, req, resp):
        resp.body = 'Hello world!'

# add the limiter middleware to the Falcon app
app = falcon.API(middleware=limiter.middleware)

things = ThingsResource()
app.add_route('/things', things)
```

For more details please read the documentation at [Read the Docs](https://falcon-limiter.readthedocs.io/en/latest/)

## Development

For the development environment we use `Pipenv` and for packaging we use `Flit`.

### Documentation

The documentation is built via Sphinx following the 
[Google docstring style](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html#example-google) 
and hosted on [Read the Docs](https://falcon-limiter.readthedocs.io/en/latest/).

To review the documentation locally before committing:
```
$ make docs
$ cd docs
$ python -m http.server 8088
```

Now you can access the documentation locally under `http://127.0.0.1:8088/_build/html/`

### Development environment

You will need Python 3.6-3.9 and PyPy3 and its source package installed to run
`tox` in all environments.

We do use type hinting and run MyPy on those, but unfortunately MyPy currently breaks
the PyPy tests due to the `typed-ast` package's "bug" (see
https://github.com/python/typed_ast/issues/97). Also with Pipenv you can't 
have a second Pipfile. This is why for now we don't have `mypy` listed as a dev package
in the Pipfile.

## Credits

Our library uses the popular [Limits](https://github.com/alisaifee/limits) library
for most of the backend operations.
