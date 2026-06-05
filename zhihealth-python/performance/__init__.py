# ZhiHealth 性能优化模块
# 提供：多级Redis缓存策略、数据库查询优化、连接池管理、性能监控

from .cache_engine import (
    CacheLevel,
    CachePolicy,
    CacheConfig,
    CacheEntry,
    LRUCache,
    MultiLevelCacheManager,
    cached,
    get_cache_manager
)

from .db_optimizer import (
    QueryOptimizationLevel,
    SlowQueryThreshold,
    QueryMetrics,
    IndexSuggestion,
    SQLAnalyzer,
    ConnectionPoolManager,
    QueryPerformanceMonitor,
    get_connection_pool,
    get_query_monitor
)

__all__ = [
    'CacheLevel',
    'CachePolicy', 
    'CacheConfig',
    'CacheEntry',
    'LRUCache',
    'MultiLevelCacheManager',
    'cached',
    'get_cache_manager',
    'QueryOptimizationLevel',
    'SlowQueryThreshold',
    'QueryMetrics',
    'IndexSuggestion',
    'SQLAnalyzer',
    'ConnectionPoolManager',
    'QueryPerformanceMonitor',
    'get_connection_pool',
    'get_query_monitor'
]