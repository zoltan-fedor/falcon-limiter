Welcome to Falcon-Limiter's documentation!
==========================================

Version: 0.0.1

Falcon-Limiter provides advanced rate limiting support to the
`Falcon web framework <https://github.com/falconry/falcon>`_.

Rate limiting strategies are provided with the help of the popular
`Limits <https://github.com/alisaifee/limits>`_ library.

The library aims to be compatible with CPython 3.6+ and PyPy 3.5+.

.. include:: quickstart.rst


Installation
------------

Install the extension with pip::

    $ pip install Falcon-Limiter


Set Up
------

Rate limiting is managed through a ``Limiter`` instance:

.. code-block:: python

    import falcon
    from falcon_limiter import Limiter
    from falcon_limiter.utils import get_remote_addr

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits="5 per minute,2 per second"
    )

..

The ``Limiter`` instance is a Falcon Middleware and it has a ``limit()`` method which can
be used as a decorator to decorate a whole class or individual methods:

.. code-block:: python

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

    # use the default limit for all methods of this class
    @limiter.limit()
    class ThingsResource2:
        # this will use the default limit from the class
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

        # this will use a custom limit overwriting the one set at class level
        @limiter.limit(limits="3 per minute,1 per second")
        def on_post(self, req, resp):
            resp.body = 'Hello world!'
..

You can provide a config dictionary to the ``Limiter``, see :ref:`config-attributes`:

.. code-block:: python

    import falcon
    from falcon_limiter import Limiter
    from falcon_limiter.utils import get_remote_addr

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits="5 per minute,2 per second",
        config={
            'RATELIMIT_KEY_PREFIX': 'myapp',  # to allow multiple apps in the same Redis db
            'RATELIMIT_STORAGE_URL': f'redis://:{REDIS_PSW}@{REDIS_HOST}:{REDIS_PORT}',
            'RATELIMIT_STRATEGY': 'moving-window'
        }
    )
..

The limiter instance needs to be specified as a middleware when creating the app by
calling ``falcon.API()``:

.. code-block:: python

    import falcon
    from falcon_limiter import Limiter
    from falcon_limiter.utils import get_remote_addr

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits="5 per minute,2 per second"
    )

    @limiter.limit()
    class ThingsResource:
        def on_get(self, req, resp):
            resp.body = 'Hello world!'

    # add the limiter middleware to the Falcon app
    app = falcon.API(middleware=limiter.middleware)
..

.. _ratelimit-string:

Rate limit string notation
==========================

Rate limits are specified as strings following the format:

    [count] [per|/] [n (optional)] [second|minute|hour|day|month|year]

You can combine multiple rate limits by separating them with a delimiter of your
choice.

Examples
--------

* 10 per hour
* 10/hour
* 10/hour;100/day;2000 per year
* 100/day, 500/7days


.. _ratelimit-strategy:

Rate limiting strategies
========================
Falcon-Limiter comes with three different rate limiting strategies built-in, provided
by the `Limits <https://github.com/alisaifee/limits>`_ library.

Pick the one that works for your use-case by specifying it in your config as
``RATELIMIT_STRATEGY`` (one of ``fixed-window``, ``fixed-window-elastic-expiry``,
or ``moving-window``). The default configuration is ``fixed-window``.


Fixed Window
------------
This is the most memory efficient strategy to use as it maintains one counter per resource
and rate limit. It does however have its drawbacks as it allows bursts within each window -
thus allowing an ‘attacker’ to by-pass the limits. The effects of these bursts can be partially
circumvented by enforcing multiple granularities of windows per resource.

For example, if you specify a ``100/minute`` rate limit on a route, this strategy will allow
100 hits in the last second of one window and a 100 more in the first second of the next window.
To ensure that such bursts are managed, you could add a second rate limit of ``2/second`` on
the same route.

Fixed Window with Elastic Expiry
--------------------------------
This strategy works almost identically to the Fixed Window strategy with the exception that
each hit results in the extension of the window. This strategy works well for creating large
penalties for breaching a rate limit.

For example, if you specify a ``100/minute`` rate limit on a route and it is being attacked
at the rate of 5 hits per second for 2 minutes - the attacker will be locked out of the
resource for an extra 60 seconds after the last hit. This strategy helps circumvent bursts.

Moving Window
-------------
.. warning:: The moving window strategy is only implemented for the ``redis`` and ``in-memory``
    storage backends. The strategy requires using a list with fast random access which
    is not very convenient to implement with a memcached storage.

This strategy is the most effective for preventing bursts from by-passing the rate limit as
the window for each limit is not fixed at the start and end of each time unit (i.e. N/second
for a moving window means N in the last 1000 milliseconds). There is however a higher memory
cost associated with this strategy as it requires ``N`` items to be maintained in memory
per resource and rate limit.



.. include:: config.rst


.. include:: recipes.rst



Development
-----------

For development guidelines see
`https://github.com/zoltan-fedor/falcon-limiter#development <https://github.com/zoltan-fedor/falcon-limiter#development>`_


.. _API Reference:

API Reference
-------------

If you are looking for information on a specific function, class or
method of a service, then this part of the documentation is for you.

.. toctree::
   :maxdepth: 2

   api_reference/index


Additional Information
----------------------

.. toctree::
   :maxdepth: 2

   changelog
   license

* :ref:`search`