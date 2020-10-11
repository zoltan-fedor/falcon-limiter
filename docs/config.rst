.. _config-attributes:

Configuring Falcon-Limiter
--------------------------

Config values can be provided as a dictionary to the ``Limiter()``. For example:

.. code-block:: python

    from falcon_limiter import Limiter
    from falcon_limiter.utils import get_remote_addr

    limiter = Limiter(
        key_func=get_remote_addr,
        default_limits="5 per minute,2 per second",
        config={
            'RATELIMIT_KEY_PREFIX': 'myapp',
            'RATELIMIT_STORAGE_URL': 'redis://@redis:6379',
            'RATELIMIT_STRATEGY': 'moving-window'
        }
    )
..


The following configuration values exist for Falcon-Limiter:

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|


================================ ==================================================================
``RATELIMIT_STORAGE_URL``        A storage location conforming to the scheme in :ref:`storage-scheme`.
                                 A basic in-memory storage can be used by specifying ``memory://`` though this
                                 should probably never be used in production. Some supported backends include:

                                 - Memcached: ``memcached://host:port``
                                 - Memcached on Google App Engine: ``gaememcached://host:port``
                                 - Redis listening on TCP: ``redis://host:port``
                                 - Redis listening on a unix domain socket: ``redis+unix:///path/to/socket?db=n``
                                 - Redis with password and db specified: ``redis://:password@host:port?db=n``
                                 - Redis over SSL: ``rediss://host:port``
                                 - Redis Sentinel: ``redis+sentinel://host:26379/my-redis-service`` or ``redis+sentinel://host:26379,host:26380/my-redis-service``
                                 - Redis Cluster: ``redis+cluster://localhost:7000`` or ``redis+cluster://localhost:7000,localhost:70001``
                                 - GAE Memcached: ``gaememcached://host:port``

                                 For more examples and requirements of supported backends please refer to :ref:`storage-scheme`.
``RATELIMIT_STORAGE_OPTIONS``    A dictionary to set extra options to be passed to the
                                 storage implementation upon initialization. (Useful if you're
                                 subclassing :class:`limits.Storage` to create a
                                 subclassing :class:`limits.storage.Storage` to create a
                                 custom Storage backend.)
``RATELIMIT_STRATEGY``           The rate limiting strategy to use. See :ref:`ratelimit-strategy`
                                 for details.
``RATELIMIT_KEY_PREFIX``         If you are using a shared backend - like a Redis instance shared
                                 by multiple apps, then to avoid a potential clash between the ratelimit
                                 records, you should provide a string in ``RATELIMIT_KEY_PREFIX``,
                                 which will be added to the key.
================================ ==================================================================
