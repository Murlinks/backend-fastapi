"""
缓存服务 - Redis缓存优化
提供数据缓存、会话管理、热点数据缓存等功能
"""
import json
import logging
from typing import Any, Optional, List, Dict
from datetime import timedelta
import hashlib

from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务类"""
    
    def __init__(self):
        self.default_ttl = 3600  # 默认缓存1小时
        self.session_ttl = 86400  # 会话缓存24小时
        self.hot_data_ttl = 300  # 热点数据缓存5分钟
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
        
        Returns:
            缓存的数据，如果不存在返回None
        """
        try:
            data = await redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 要缓存的数据
            ttl: 过期时间（秒），默认使用default_ttl
        
        Returns:
            是否设置成功
        """
        try:
            ttl = ttl or self.default_ttl
            data = json.dumps(value, ensure_ascii=False)
            await redis_client.setex(key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存数据
        
        Args:
            key: 缓存键
        
        Returns:
            是否删除成功
        """
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        批量删除匹配模式的缓存
        
        Args:
            pattern: 匹配模式，如 "user:*"
        
        Returns:
            删除的键数量
        """
        try:
            keys = await redis_client.keys(pattern)
            if keys:
                return await redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"批量删除缓存失败: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            是否存在
        """
        try:
            return await redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"检查缓存存在性失败: {e}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        value_func: callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取缓存，如果不存在则设置缓存
        
        Args:
            key: 缓存键
            value_func: 获取数据的函数
            ttl: 过期时间（秒）
        
        Returns:
            缓存的数据或新获取的数据
        """
        # 尝试从缓存获取
        cached_data = await self.get(key)
        if cached_data is not None:
            return cached_data
        
        # 缓存不存在，调用函数获取数据
        try:
            data = await value_func()
            await self.set(key, data, ttl)
            return data
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            raise
    
    async def cache_user_expenses(
        self,
        user_id: str,
        expenses: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ) -> bool:
        """
        缓存用户支出数据
        
        Args:
            user_id: 用户ID
            expenses: 支出数据列表
            ttl: 过期时间（秒）
        
        Returns:
            是否缓存成功
        """
        key = f"user:{user_id}:expenses"
        return await self.set(key, expenses, ttl or self.hot_data_ttl)
    
    async def get_user_expenses(
        self,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取用户支出缓存
        
        Args:
            user_id: 用户ID
        
        Returns:
            支出数据列表
        """
        key = f"user:{user_id}:expenses"
        return await self.get(key)
    
    async def cache_budget_summary(
        self,
        user_id: str,
        summary: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        缓存预算摘要
        
        Args:
            user_id: 用户ID
            summary: 预算摘要数据
            ttl: 过期时间（秒）
        
        Returns:
            是否缓存成功
        """
        key = f"user:{user_id}:budget_summary"
        return await self.set(key, summary, ttl or self.hot_data_ttl)
    
    async def get_budget_summary(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取预算摘要缓存
        
        Args:
            user_id: 用户ID
        
        Returns:
            预算摘要数据
        """
        key = f"user:{user_id}:budget_summary"
        return await self.get(key)
    
    async def cache_ai_response(
        self,
        prompt: str,
        response: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        缓存AI响应
        
        Args:
            prompt: 用户输入的提示
            response: AI响应
            ttl: 过期时间（秒）
        
        Returns:
            是否缓存成功
        """
        # 使用MD5哈希作为缓存键
        key = f"ai_response:{hashlib.md5(prompt.encode()).hexdigest()}"
        return await self.set(key, response, ttl or self.default_ttl)
    
    async def get_ai_response(
        self,
        prompt: str
    ) -> Optional[str]:
        """
        获取AI响应缓存
        
        Args:
            prompt: 用户输入的提示
        
        Returns:
            AI响应
        """
        key = f"ai_response:{hashlib.md5(prompt.encode()).hexdigest()}"
        return await self.get(key)
    
    async def cache_category_stats(
        self,
        user_id: str,
        stats: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        缓存分类统计
        
        Args:
            user_id: 用户ID
            stats: 分类统计数据
            ttl: 过期时间（秒）
        
        Returns:
            是否缓存成功
        """
        key = f"user:{user_id}:category_stats"
        return await self.set(key, stats, ttl or self.hot_data_ttl)
    
    async def get_category_stats(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取分类统计缓存
        
        Args:
            user_id: 用户ID
        
        Returns:
            分类统计数据
        """
        key = f"user:{user_id}:category_stats"
        return await self.get(key)
    
    async def invalidate_user_cache(self, user_id: str) -> int:
        """
        使所有用户相关缓存失效
        
        Args:
            user_id: 用户ID
        
        Returns:
            删除的键数量
        """
        pattern = f"user:{user_id}:*"
        return await self.delete_pattern(pattern)
    
    async def cache_hot_data(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        缓存热点数据（高频访问的数据）
        
        Args:
            key: 缓存键
            value: 要缓存的数据
            ttl: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        return await self.set(f"hot:{key}", value, ttl or self.hot_data_ttl)
    
    async def get_hot_data(
        self,
        key: str
    ) -> Optional[Any]:
        """
        获取热点数据缓存
        
        Args:
            key: 缓存键
        
        Returns:
            缓存的数据
        """
        return await self.get(f"hot:{key}")
    
    async def increment(
        self,
        key: str,
        amount: int = 1
    ) -> int:
        """
        增加计数器
        
        Args:
            key: 缓存键
            amount: 增加的数值
        
        Returns:
            增加后的值
        """
        try:
            return await redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"增加计数器失败: {e}")
            return 0
    
    async def get_counter(
        self,
        key: str
    ) -> int:
        """
        获取计数器值
        
        Args:
            key: 缓存键
        
        Returns:
            计数器值
        """
        try:
            value = await redis_client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"获取计数器失败: {e}")
            return 0
    
    async def set_session(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置会话数据
        
        Args:
            session_id: 会话ID
            session_data: 会话数据
            ttl: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        key = f"session:{session_id}"
        return await self.set(key, session_data, ttl or self.session_ttl)
    
    async def get_session(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取会话数据
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话数据
        """
        key = f"session:{session_id}"
        return await self.get(key)
    
    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话数据
        
        Args:
            session_id: 会话ID
        
        Returns:
            是否删除成功
        """
        key = f"session:{session_id}"
        return await self.delete(key)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        try:
            info = await redis_client.info("stats")
            return {
                "total_keys": info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0) / 
                    (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                ) if info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0) > 0 else 0
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}


# 全局缓存服务实例
cache_service = CacheService()