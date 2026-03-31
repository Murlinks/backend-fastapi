"""
Redis 缓存配置和连接管理
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
import logging
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis连接池
redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """初始化Redis连接"""
    global redis_pool, redis_client

    last_err: Exception | None = None
    max_attempts = 10  # 约 20-30 秒
    delay_seconds = 2

    for attempt in range(1, max_attempts + 1):
        try:
            redis_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                retry_on_timeout=True,
                decode_responses=True
            )

            redis_client = redis.Redis(connection_pool=redis_pool)

            # 测试连接
            await redis_client.ping()
            logger.info("Redis连接初始化成功")
            return

        except Exception as e:
            last_err = e
            logger.warning(f"Redis连接初始化失败（第 {attempt}/{max_attempts} 次）: {e}")
            await asyncio.sleep(delay_seconds)

    logger.error(f"Redis连接初始化最终失败: {last_err}")
    raise last_err


async def get_redis() -> redis.Redis:
    """获取Redis客户端"""
    if redis_client is None:
        raise RuntimeError("Redis未初始化")
    return redis_client


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.default_ttl = 3600  # 1小时默认过期时间
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            client = await get_redis()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            client = await get_redis()
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, ensure_ascii=False)
            await client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            client = await get_redis()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            client = await get_redis()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"检查缓存存在性失败 {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """递增计数器"""
        try:
            client = await get_redis()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.error(f"递增计数器失败 {key}: {e}")
            return None


# 全局缓存管理器实例
cache_manager = CacheManager()


async def close_redis():
    """关闭Redis连接"""
    global redis_client, redis_pool
    
    if redis_client:
        await redis_client.close()
    
    if redis_pool:
        await redis_pool.disconnect()
    
    logger.info("Redis连接已关闭")