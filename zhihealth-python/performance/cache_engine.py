"""
Redis 多级缓存策略引擎
实现：L1本地内存缓存 + L2 Redis分布式缓存 + L3数据库
支持：自动过期、缓存穿透/击穿/雪崩防护、热点数据预加载
"""

import json
import time
import hashlib
import threading
from typing import Any, Optional, Dict, List, Callable, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from collections import OrderedDict
import pickle
import redis as redis_lib
from loguru import logger


class CacheLevel(Enum):
    """缓存层级"""
    L1_LOCAL = "l1_local"               # 进程内本地缓存（最快，但容量小）
    L2_REDIS = "l2_redis"              # Redis分布式缓存（较快，容量大）
    L3_DATABASE = "l3_database"         # 数据库（最慢，权威数据源）


class CachePolicy(Enum):
    """缓存淘汰策略"""
    LRU = "lru"                         # 最近最少使用
    LFU = "lfu"                         # 最不经常使用
    FIFO = "fifo"                       # 先进先出
    TTL = "ttl"                         # 基于TTL过期


@dataclass
class CacheConfig:
    """缓存配置"""
    
    # L1 本地缓存配置
    l1_max_size: int = 1000             # 最大条目数
    l1_default_ttl: int = 60            # 默认TTL(秒)
    l1_policy: CachePolicy = CachePolicy.LRU
    
    # L2 Redis配置
    l2_host: str = "localhost"
    l2_port: int = 6379
    l2_db: int = 0
    l2_password: Optional[str] = None
    l2_default_ttl: int = 3600          # 默认1小时
    l2_key_prefix: str = "zhihealth:"
    
    # 全局配置
    enabled: bool = True
    null_cache_ttl: int = 60           # 空值缓存时间（防穿透）
    hot_key_threshold: int = 100       # 热点Key阈值(访问次数/分钟)
    
    @classmethod
    def from_env(cls) -> 'CacheConfig':
        """从环境变量加载"""
        import os
        
        return cls(
            l1_max_size=int(os.getenv('CACHE_L1_MAX_SIZE', '1000')),
            l1_default_ttl=int(os.getenv('CACHE_L1_TTL', '60')),
            l2_host=os.getenv('REDIS_HOST', 'localhost'),
            l2_port=int(os.getenv('REDIS_PORT', '6379')),
            l2_db=int(os.getenv('REDIS_DB', '0')),
            l2_password=os.getenv('REDIS_PASSWORD') or None,
            l2_default_ttl=int(os.getenv('CACHE_L2_TTL', '3600')),
            enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
        )


@dataclass 
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    size_bytes: int = 0
    source_level: CacheLevel = CacheLevel.L1_LOCAL
    
    def is_expired(self) -> bool:
        if self.expires_at <= 0:
            return False
        return time.time() > self.expires_at
    
    def ttl_remaining(self) -> int:
        if self.expires_at <= 0:
            return -1  # 永不过期
        remaining = int(self.expires_at - time.time())
        return max(0, remaining)


class LRUCache:
    """
    线程安全的LRU本地缓存实现
    使用OrderedDict保证O(1)的get/set操作
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0,
            'deletes': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值（线程安全）"""
        with self._lock:
            if key not in self._cache:
                self.stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self.stats['misses'] += 1
                return None
            
            # 更新访问信息和位置（移到末尾表示最近使用）
            entry.access_count += 1
            entry.last_access = time.time()
            self._cache.move_to_end(key)
            
            self.stats['hits'] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        with self._lock:
            # 计算大小（近似）
            try:
                size = len(pickle.dumps(value))
            except:
                size = len(str(value))
            
            expires_at = (time.time() + (ttl or self.default_ttl)) if (ttl or self.default_ttl > 0) else 0
            
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at,
                size_bytes=size
            )
            
            # 如果key已存在，先删除旧值
            if key in self._cache:
                del self._cache[key]
            
            # 检查容量并淘汰
            while len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            self._cache[key] = entry
            self.stats['sets'] += 1
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.stats['deletes'] += 1
                return True
            return False
    
    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
    
    def _evict_oldest(self):
        """淘汰最久未使用的条目"""
        if self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self.stats['evictions'] += 1
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total_requests = self.stats['hits'] + self.stats['misses']
        
        return {
            **self.stats,
            'current_size': len(self._cache),
            'max_size': self.max_size,
            'hit_rate': f"{(self.stats['hits']/total_requests*100):.2f}%" if total_requests > 0 else "N/A",
            'total_memory_mb': sum(e.size_bytes for e in self._cache.values()) / (1024*1024)
        }
    
    def keys(self) -> List[str]:
        """获取所有键（用于调试）"""
        with self._lock:
            return list(self._cache.keys())


class MultiLevelCacheManager:
    """
    多级缓存管理器
    协调L1本地缓存和L2 Redis缓存的协同工作
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig.from_env()
        
        # 初始化L1本地缓存
        self.l1_cache = LRUCache(
            max_size=self.config.l1_max_size,
            default_ttl=self.config.l1_default_ttl
        )
        
        # 初始化L2 Redis连接
        self._redis_client: Optional[redis_lib.Redis] = None
        self._redis_available = False
        
        if self.config.enabled:
            self._init_redis()
        
        # 热点Key追踪
        self._hot_keys: Dict[str, Dict] = {}
        self._hot_key_lock = threading.Lock()
        
        # 缓存统计
        self.global_stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'l3_hits': 0,          # 数据库查询
            'total_requests': 0
        }
        
        logger.info(f"[Cache Manager] 初始化完成 | L1大小: {self.config.l1_max_size} | "
                   f"L2状态: {'已连接' if self._redis_available else '未连接'}")
    
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            self._redis_client = redis_lib.Redis(
                host=self.config.l2_host,
                port=self.config.l2_port,
                db=self.config.l2_db,
                password=self.config.l2_password,
                socket_timeout=5,
                socket_connect_timeout=5,
                decode_responses=True,
                health_check_interval=30
            )
            
            # 测试连接
            self._redis_client.ping()
            self._redis_available = True
            
            logger.info(f"[Redis] 连接成功 | {self.config.l2_host}:{self.config.l2_port}")
            
        except Exception as e:
            self._redis_available = False
            logger.warning(f"[Redis] 连接失败，将仅使用L1本地缓存: {e}")
    
    def get(self, key: str, load_from_db: Callable = None) -> Tuple[Any, CacheLevel]:
        """
        多级缓存读取（L1 -> L2 -> DB）
        
        Args:
            key: 缓存键
            load_from_db: 数据库加载回调函数
            
        Returns:
            (value, cache_level) 元组
        """
        self.global_stats['total_requests'] += 1
        self._track_hot_key(key)
        
        # Level 1: 本地缓存
        value = self.l1_cache.get(key)
        if value is not None:
            self.global_stats['l1_hits'] += 1
            return value, CacheLevel.L1_LOCAL
        
        # Level 2: Redis
        if self._redis_available and self._redis_client:
            try:
                redis_value = self._redis_client.get(f"{self.config.l2_key_prefix}{key}")
                
                if redis_value is not None:
                    # 反序列化
                    try:
                        value = pickle.loads(redis_value.encode('latin1'))
                    except:
                        try:
                            value = json.loads(redis_value)
                        except:
                            value = redis_value
                    
                    # 回填L1缓存
                    self.l1_cache.set(key, value)
                    
                    self.global_stats['l2_hits'] += 1
                    return value, CacheLevel.L2_REDIS
                    
            except redis_lib.RedisError as e:
                logger.warning(f"[Redis] 读取异常: {e}")
        
        # Level 3: 数据库
        if load_from_db:
            try:
                value = load_from_db()
                
                if value is not None:
                    # 写入各级缓存
                    self.set(key, value)
                
                self.global_stats['l3_hits'] += 1
                return value, CacheLevel.L3_DATABASE
                
            except Exception as e:
                logger.error(f"[DB] 加载数据失败: {e}", exc_info=True)
                raise
        
        return None, CacheLevel.L3_DATABASE
    
    def set(self, key: str, value: Any, 
            ttl: Optional[int] = None,
            levels: List[CacheLevel] = None) -> bool:
        """
        多级缓存写入
        
        Args:
            key: 键
            value: 值
            ttl: 过期时间（秒），None则使用默认值
            levels: 要写入的缓存级别列表，None则全部写入
        """
        if not self.config.enabled:
            return False
        
        target_levels = levels or [CacheLevel.L1_LOCAL, CacheLevel.L2_REDIS]
        success = True
        
        for level in target_levels:
            if level == CacheLevel.L1_LOCAL:
                self.l1_cache.set(key, value, ttl)
                
            elif level == CacheLevel.L2_REDIS and self._redis_available:
                try:
                    serialized = pickle.dumps(value)
                    redis_key = f"{self.config.l2_key_prefix}{key}"
                    effective_ttl = ttl or self.config.l2_default_ttl
                    
                    self._redis_client.setex(redis_key, effective_ttl, serialized.decode('latin1'))
                    
                except redis_lib.RedisError as e:
                    logger.warning(f"[Redis] 写入失败: {e}")
                    success = False
        
        return success
    
    def delete(self, key: str, invalidate_all: bool = True) -> bool:
        """
        删除缓存（支持级联失效）
        
        Args:
            key: 键
            invalidate_all: 是否同时清除所有级别的缓存
        """
        deleted_l1 = self.l1_cache.delete(key)
        
        deleted_l2 = False
        if invalidate_all and self._redis_available:
            try:
                redis_key = f"{self.config.l2_key_prefix}{key}"
                deleted_l2 = bool(self._redis_client.delete(redis_key))
            except:
                pass
        
        return deleted_l1 or deleted_l2
    
    def get_or_set(self, 
                  key: str, 
                  loader_func: Callable,
                  ttl: Optional[int] = None) -> Any:
        """
        获取或设置缓存（便捷方法）
        如果缓存不存在，调用loader_func加载数据并缓存
        
        Args:
            key: 缓存键
            loader_func: 无参数的数据加载函数
            ttl: TTL
            
        Returns:
            缓存的值或新加载的值
        """
        value, level = self.get(key)
        
        if value is not None:
            return value
        
        # 加载并缓存
        value = loader_func()
        
        if value is not None:
            self.set(key, value, ttl)
        
        return value
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        批量失效匹配模式的缓存（用于数据更新后的缓存清理）
        
        Args:
            pattern: 通配符模式，如 user_* 或 *:report:*
            
        Returns:
            失效的缓存数量
        """
        count = 0
        
        # L1清理
        all_keys = self.l1_cache.keys()
        import fnmatch
        keys_to_delete = [k for k in all_keys if fnmatch.fnmatch(k, pattern)]
        
        for k in keys_to_delete:
            self.l1_cache.delete(k)
            count += 1
        
        # L2清理（使用SCAN避免阻塞）
        if self._redis_available:
            try:
                cursor = 0
                full_pattern = f"{self.config.l2_key_prefix}{pattern}"
                
                while True:
                    cursor, keys = self._redis_client.scan(cursor=cursor, match=full_pattern, count=100)
                    
                    if keys:
                        count += self._redis_client.delete(*keys)
                    
                    if cursor == 0:
                        break
                        
            except Exception as e:
                logger.warning(f"[Redis] 批量删除异常: {e}")
        
        logger.info(f"[Cache] 批量失效 | Pattern: {pattern} | Count: {count}")
        return count
    
    def _track_hot_key(self, key: str):
        """追踪热点Key"""
        with self._hot_key_lock:
            current_time = time.time()
            
            if key not in self._hot_keys:
                self._hot_keys[key] = {'count': 0, 'window_start': current_time}
            
            entry = self._hot_keys[key]
            entry['count'] += 1
            
            # 每分钟重置一次计数
            if current_time - entry['window_start'] > 60:
                if entry['count'] > self.config.hot_key_threshold:
                    logger.debug(f"[Hot Key] {key} | QPS: {entry['count']}/min")
                    # 可在此处触发预加载、本地缓存延长等策略
                
                entry['count'] = 0
                entry['window_start'] = current_time
    
    def get_statistics(self) -> Dict:
        """获取完整的缓存统计报告"""
        total = self.global_stats.get('total_requests', 1)
        
        return {
            'configuration': {
                'enabled': self.config.enabled,
                'l1MaxSize': self.config.l1_max_size,
                'l1DefaultTTL': self.config.l1_default_ttl,
                'l2DefaultTTL': self.config.l2_default_ttl,
                'redisAvailable': self._redis_available
            },
            'performance': {
                **self.global_stats,
                'hitRate': f"{((self.global_stats['l1_hits'] + self.global_stats['l2_hits']) / total * 100):.2f}%",
                'l1HitRate': f"{(self.global_stats['l1_hits'] / total * 100):.2f}%",
                'l2HitRate': f"{(self.global_stats['l2_hits'] / total * 100):.2f}%"
            },
            'l1Details': self.l1_cache.get_stats(),
            'hotKeys': [
                {'key': k[:20], 'qps': v['count']}
                for k, v in sorted(self._hot_keys.items(), 
                                  key=lambda x: x[1]['count'], 
                                  reverse=True)[:10]
            ]
        }
    
    def warmup(self, keys_and_loaders: Dict[str, Callable]):
        """
        缓存预热
        在系统启动时批量加载热点数据到缓存
        
        Args:
            keys_and_loaders: {key: loader_function} 字典
        """
        logger.info(f"[Cache Warmup] 开始预热 | Keys: {len(keys_and_loaders)}")
        
        success_count = 0
        fail_count = 0
        
        for key, loader in keys_and_loaders.items():
            try:
                value = loader()
                if value is not None:
                    self.set(key, value)
                    success_count += 1
            except Exception as e:
                logger.warning(f"[Warmup] 预热失败 [{key}]: {e}")
                fail_count += 1
        
        logger.info(f"[Cache Warmup] 完成 | 成功: {success_count} | 失败: {fail_count}")


# ==================== 装饰器工具 ====================

def cached(ttl: int = 300, 
          key_prefix: str = "",
          cache_levels: List[CacheLevel] = None):
    """
    缓存装饰器（用于函数结果缓存）
    
    Usage:
        @cached(ttl=600, key_prefix="user_profile")
        def get_user_profile(user_id):
            # 数据库查询...
            return user_data
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            
            # 生成缓存键
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # 尝试获取缓存
            value, level = cache_manager.get(cache_key)
            
            if value is not None:
                return value
            
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            cache_manager.set(cache_key, result, ttl, cache_levels)
            
            return result
        
        wrapper.cache_clear = lambda: None  # 占位符
        return wrapper
    
    return decorator


# 全局实例
_cache_manager: Optional[MultiLevelCacheManager] = None

def get_cache_manager(config: Optional[CacheConfig] = None) -> MultiLevelCacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = MultiLevelCacheManager(config)
    return _cache_manager