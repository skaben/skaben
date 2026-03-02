import redis
from django.conf import settings
from redis import ConnectionPool

_pool = ConnectionPool(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD
)


def get_redis_client():
    """
    Returns a Redis client object using the shared connection pool.
    """
    return redis.Redis(connection_pool=_pool)
