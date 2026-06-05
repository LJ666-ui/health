"""
数据库查询优化引擎
提供：SQL分析、索引建议、慢查询诊断、连接池管理、批量操作优化
"""

import re
import time
import threading
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from loguru import logger


class QueryOptimizationLevel(Enum):
    """优化级别"""
    NONE = 0                           # 不优化
    BASIC = 1                          # 基础优化（参数化查询）
    INTERMEDIATE = 2                   # 中级（索引提示 + 查询重写）
    ADVANCED = 3                       # 高级（执行计划分析 + 自动分区）


class SlowQueryThreshold(Enum):
    """慢查询阈值"""
    FAST = 0.1                         # <100ms 正常
    NORMAL = 0.5                       # <500ms 可接受
    SLOW = 2.0                         # >2s 需关注
    VERY_SLOW = 10.0                   # >10s 告警


@dataclass
class QueryMetrics:
    """查询性能指标"""
    query_id: str
    sql: str
    execution_time_ms: float
    rows_affected: int = 0
    rows_scanned: int = 0
    rows_returned: int = 0
    
    # 索引使用情况
    index_used: Optional[str] = None
    index_hit_ratio: float = 1.0
    
    # 连接信息
    database: str = "default"
    table: Optional[str] = None
    
    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 优化建议
    suggestions: List[str] = field(default_factory=list)
    
    @property
    def is_slow(self) -> bool:
        return self.execution_time_ms > SlowQueryThreshold.SLOW.value * 1000
    
    @property
    def efficiency(self) -> float:
        if self.rows_scanned == 0:
            return 1.0
        return self.rows_returned / self.rows_scanned


@dataclass 
class IndexSuggestion:
    """索引建议"""
    table_name: str
    column_names: List[str]
    index_type: str = "BTREE"          # BTREE / HASH / FULLTEXT
    is_unique: bool = False
    estimated_impact: str = ""         # 如 "预计提升50%查询速度"
    
    create_sql: str = ""
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'table': self.table_name,
            'columns': self.column_names,
            'type': self.index_type,
            'unique': self.is_unique,
            'impact': self.estimated_impact,
            'sql': self.create_sql,
            'reason': self.reason
        }


class SQLAnalyzer:
    """
    SQL语句静态分析器
    检测潜在的性能问题并给出优化建议
    """
    
    # 反模式检测规则
    ANTI_PATTERNS = {
        r'SELECT\s+\*': {
            'severity': 'warning',
            'message': '避免使用SELECT *，应明确指定需要的列',
            'suggestion': '只查询必要的字段以减少I/O和网络传输'
        },
        r'WHERE\s+.*=\s*[\'"]%.*[\'"]\s*(?:OR|AND)': {
            'severity': 'error',
            'message': '检测到前缀通配符LIKE查询，无法使用索引',
            'suggestion': '考虑使用全文索引或搜索引擎'
        },
        r'ORDER BY RAND\(\)': {
            'severity': 'critical',
            'message': 'ORDER BY RAND() 性能极差，尤其在大表上',
            'suggestion': '使用应用层随机或预生成随机ID列表'
        },
        r'(?i)(?:NOT\s+)?IN\s*\(\s*SELECT': {
            'severity': 'warning',
            'message': '子查询IN可能导致性能问题',
            'suggestion': '考虑使用JOIN替代或使用EXISTS'
        },
        r'(?i)\b(?:HAVING)\b.*(?i)(?:COUNT|SUM|AVG)': {
            'severity': 'info',
            'message': 'HAVING中使用聚合函数可能影响性能',
            'suggestion': '尽量在WHERE中过滤而非HAVING'
        }
    }
    
    @classmethod
    def analyze(cls, sql: str) -> Dict[str, Any]:
        """
        分析SQL语句
        
        Args:
            sql: SQL语句
            
        Returns:
            分析结果字典
        """
        result = {
            'originalSql': sql,
            'normalizedSql': cls._normalize(sql),
            'issues': [],
            'suggestions': [],
            'estimatedComplexity': 'medium',
            'canUseCache': True
        }
        
        # 检测反模式
        for pattern, info in cls.ANTI_PATTERNS.items():
            if re.search(pattern, sql, re.IGNORECASE):
                issue = {
                    'type': info['severity'],
                    'pattern': pattern[:50],
                    'message': info['message'],
                    'suggestion': info['suggestion']
                }
                result['issues'].append(issue)
                result['suggestions'].append(info['suggestion'])
                
                if info['severity'] == 'critical':
                    result['estimatedComplexity'] = 'very_high'
        
        # 检查是否可缓存
        if re.search(r'RAND\(\)|NOW\(\)|CURDATE\(\)', sql, re.IGNORECASE):
            result['canUseCache'] = False
        
        # 表名提取
        tables = cls._extract_tables(sql)
        result['tables'] = tables
        
        # 复杂度评估
        complexity_score = len(result['issues'])
        if complexity_score >= 3:
            result['estimatedComplexity'] = 'high'
        elif complexity_score == 0:
            result['estimatedComplexity'] = 'low'
        
        return result
    
    @classmethod
    def _normalize(cls, sql: str) -> str:
        """标准化SQL（去除多余空格和注释）"""
        normalized = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        normalized = re.sub(r'--.*$', '', normalized, flags=re.MULTILINE)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized.upper()
    
    @classmethod
    def _extract_tables(cls, sql: str) -> List[str]:
        """从SQL中提取涉及的表名"""
        patterns = [
            r'FROM\s+(\w+)',
            r'JOIN\s+(\w+)',
            r'INTO\s+(\w+)',
            r'UPDATE\s+(\w+)'
        ]
        
        tables = []
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)
        
        return list(set(tables))
    
    @classmethod
    def suggest_indexes(cls, sql: str, schema_info: Dict[str, List[str]] = None) -> List[IndexSuggestion]:
        """
        基于SQL模式推荐索引
        
        Args:
            sql: SQL语句
            schema_info: 表结构信息 {table_name: [column_names]}
            
        Returns:
            索引建议列表
        """
        suggestions = []
        tables = cls._extract_tables(sql)
        
        # 提取WHERE条件中的列
        where_columns = re.findall(
            r'WHERE\s+(.+?)(?:\s+GROUP BY|\s+ORDER BY|\s+LIMIT|\s*$)', 
            sql, 
            re.IGNORECASE | re.DOTALL
        )
        
        for where_clause in where_columns:
            columns_in_where = re.findall(r'\b(\w+)\s*(?:=|>|<|>=|<=|LIKE|IN|BETWEEN)', where_clause)
            
            for table in tables:
                if schema_info and table in schema_info:
                    relevant_cols = [c for c in columns_in_where if c in schema_info[table]]
                    
                    if relevant_cols and len(relevant_cols) <= 3:
                        suggestion = IndexSuggestion(
                            table_name=table,
                            column_names=relevant_cols,
                            index_type="BTREE",
                            reason=f"WHERE条件频繁使用列: {', '.join(relevant_cols)}",
                            create_sql=f"CREATE INDEX idx_{table}_{'_'.join(relevant_cols)} ON {table}({', '.join(relevant_cols)})"
                        )
                        suggestions.append(suggestion)
        
        # JOIN条件索引建议
        join_conditions = re.findall(
            r'JOIN\s+(\w+)\s+\w*\s+ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)',
            sql,
            re.IGNORECASE
        )
        
        for join_table, t1, c1, t2, c2 in join_conditions:
            if join_table == t1 and c1 not in [s.column_names[0] for s in suggestions]:
                suggestions.append(IndexSuggestion(
                    table_name=join_table,
                    column_names=[c1],
                    reason=f"JOIN连接条件列",
                    create_sql=f"CREATE INDEX idx_{join_table}_{c1} ON {join_table}({c1})"
                ))
        
        return suggestions


class ConnectionPoolManager:
    """
    数据库连接池管理器
    监控连接状态、自动回收泄漏连接、动态调整池大小
    """
    
    def __init__(self, 
                 min_connections: int = 5,
                 max_connections: int = 20,
                 idle_timeout: int = 300,
                 connection_timeout: int = 30):
        
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self.connection_timeout = connection_timeout
        
        self._active_connections: Dict[str, Dict] = {}
        self._idle_connections: deque = deque()
        self._lock = threading.Lock()
        
        # 统计
        self.stats = {
            'created_total': 0,
            'destroyed_total': 0,
            'checkout_count': 0,
            'return_count': 0,
            'timeout_count': 0
        }
        
        # 启动健康检查线程
        self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_check_thread.start()
        
        logger.info(f"[ConnectionPool] 初始化 | Min: {min_connections} | Max: {max_connections}")
    
    def checkout(self, conn_id: str = None) -> Dict:
        """
        获取连接（从池中取出）
        
        Returns:
            连接元数据字典
        """
        with self._lock:
            conn_id = conn_id or f"conn_{int(time.time()*1000)}_{threading.get_ident()}"
            
            now = time.time()
            
            # 尝试复用空闲连接
            while self._idle_connections:
                idle_conn = self._idle_connections.popleft()
                
                if (now - idle_conn.get('returned_at', 0)) < self.idle_timeout:
                    idle_conn['checked_out_at'] = now
                    idle_conn['status'] = 'active'
                    self._active_connections[idle_conn['id']] = idle_conn
                    self.stats['checkout_count'] += 1
                    
                    return idle_conn
                else:
                    # 过期连接销毁
                    self.stats['destroyed_total'] += 1
            
            # 创建新连接（如果未达上限）
            if len(self._active_connections) < self.max_connections:
                new_conn = {
                    'id': conn_id,
                    'created_at': now,
                    'checked_out_at': now,
                    'status': 'active',
                    'query_count': 0
                }
                
                self._active_connections[conn_id] = new_conn
                self.stats['created_total'] += 1
                self.stats['checkout_count'] += 1
                
                return new_conn
            
            # 达到上限，返回错误或等待
            self.stats['timeout_count'] += 1
            raise Exception(f"连接池已满 ({self.max_connections})，无法获取新连接")
    
    def checkin(self, conn_id: str):
        """归还连接到池中"""
        with self._lock:
            if conn_id not in self._active_connections:
                logger.warning(f"[ConnectionPool] 归还未知连接: {conn_id}")
                return
            
            conn = self._active_connections.pop(conn_id)
            conn['returned_at'] = time.time()
            conn['status'] = 'idle'
            
            self._idle_connections.append(conn)
            self.stats['return_count'] += 1
    
    def get_pool_status(self) -> Dict:
        """获取连接池状态"""
        with self._lock:
            return {
                **self.stats,
                'currentActive': len(self._active_connections),
                'currentIdle': len(self._idle_connections),
                'totalConnections': len(self._active_connections) + len(self._idle_connections),
                'utilizationRate': f"{(len(self._active_connections)/max(self.max_connections,1)*100):.1f}%",
                'config': {
                    'min': self.min_connections,
                    'max': self.max_connections,
                    'idleTimeout': self.idle_timeout
                }
            }
    
    def _health_check_loop(self):
        """定期健康检查循环"""
        while True:
            time.sleep(60)  # 每分钟检查一次
            
            with self._lock:
                now = time.time()
                
                # 回收超时活跃连接（可能是泄漏）
                leaked = [
                    (cid, conn) for cid, conn in self._active_connections.items()
                    if (now - conn.get('checked_out_at', 0)) > self.connection_timeout * 3
                ]
                
                for cid, conn in leaked:
                    logger.warning(f"[ConnectionPool] 检测到疑似泄漏连接: {cid} | "
                                  f"已持有 {(now - conn.get('checked_out_at', 0)):.0f}s")
                    
                    del self._active_connections[cid]
                    self.stats['destroyed_total'] += 1
                
                # 清理过多空闲连接
                excess_idle = len(self._idle_connections) - self.min_connections
                if excess_idle > 0:
                    for _ in range(min(excess_idle, 5)):
                        if self._idle_connections:
                            self._idle_connections.popleft()
                            self.stats['destroyed_total'] += 1


class QueryPerformanceMonitor:
    """
    查询性能监控器
    记录、分析和报告SQL执行性能
    """
    
    def __init__(self, slow_query_threshold_ms: float = 2000, history_size: int = 1000):
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.history_size = history_size
        
        self._query_history: deque = deque(maxlen=history_size)
        self._lock = threading.Lock()
        
        # 统计汇总
        self._summary = defaultdict(lambda: {
            'total_calls': 0,
            'total_time_ms': 0,
            'slow_count': 0,
            'avg_time_ms': 0,
            'max_time_ms': 0,
            'min_time_ms': float('inf')
        })
    
    def record_query(self, metrics: QueryMetrics):
        """记录一次查询"""
        with self._lock:
            self._query_history.append(metrics)
            
            # 更新统计摘要
            summary_key = f"{metrics.database}.{metrics.table or 'unknown'}"
            stat = self._summary[summary_key]
            
            stat['total_calls'] += 1
            stat['total_time_ms'] += metrics.execution_time_ms
            stat['avg_time_ms'] = stat['total_time_ms'] / stat['total_calls']
            stat['max_time_ms'] = max(stat['max_time_ms'], metrics.execution_time_ms)
            stat['min_time_ms'] = min(stat['min_time_ms'], metrics.execution_time_ms)
            
            if metrics.is_slow:
                stat['slow_count'] += 1
                
                logger.warning(
                    f"[SlowQuery] ID: {metrics.query_id} | "
                    f"Time: {metrics.execution_time_ms:.0f}ms | "
                    f"Table: {metrics.table} | "
                    f"Efficiency: {metrics.efficiency:.2%}"
                )
    
    def get_slow_queries(self, limit: int = 20) -> List[QueryMetrics]:
        """获取慢查询列表（按时间排序）"""
        with self._lock:
            sorted_queries = sorted(
                [q for q in self._query_history if q.is_slow],
                key=lambda x: x.execution_time_ms,
                reverse=True
            )
            return sorted_queries[:limit]
    
    def get_top_queries_by_frequency(self, top_n: int = 20) -> List[Tuple[str, Dict]]:
        """获取最频繁的查询类型"""
        from collections import Counter
        
        with self._lock:
            sql_patterns = [q.sql[:80] for q in self._query_history]
            most_common = Counter(sql_patterns).most_common(top_n)
            
            results = []
            for pattern, count in most_common:
                matching_stats = [q for q in self._query_history if q.sql.startswith(pattern)]
                avg_time = sum(q.execution_time_ms for q in matching_stats) / len(matching_stats)
                
                results.append((pattern, {
                    'count': count,
                    'avgTimeMs': round(avg_time, 2),
                    'tables': list(set(q.table for q in matching_stats if q.table))
                }))
            
            return results
    
    def get_performance_summary(self) -> Dict:
        """获取整体性能摘要"""
        with self._lock:
            total_queries = len(self._query_history)
            total_time = sum(q.execution_time_ms for q in self._query_history)
            slow_count = sum(1 for q in self._query_history if q.is_slow)
            
            return {
                'period': {
                    'start': self._query_history[0].timestamp.isoformat() if self._query_history else None,
                    'end': self._query_history[-1].timestamp.isoformat() if self._query_history else None
                },
                'overview': {
                    'totalQueries': total_queries,
                    'totalExecutionTimeMs': round(total_time, 2),
                    'averageQueryTimeMs': round(total_time / total_queries, 2) if total_queries > 0 else 0,
                    'slowQueryCount': slow_count,
                    'slowQueryRate': f"{(slow_count/total_queries*100):.2f}%" if total_queries > 0 else "0%"
                },
                'topSlowQueries': [
                    {
                        'sql': q.sql[:60],
                        'timeMs': round(q.execution_time_ms, 2),
                        'table': q.table,
                        'timestamp': q.timestamp.isoformat()
                    }
                    for q in self.get_slow_queries(5)
                ],
                'tableBreakdown': dict(sorted(
                    self._summary.items(),
                    key=lambda x: x[1]['total_time_ms'],
                    reverse=True
                )[:10])
            }


# 全局实例
_cache_manager_instance = None
_connection_pool = None
_query_monitor = None

def get_cache_manager():
    global _cache_manager_instance
    if _cache_manager_instance is None:
        from .cache_engine import MultiLevelCacheManager, CacheConfig
        _cache_manager_instance = MultiLevelCacheManager(CacheConfig.from_env())
    return _cache_manager_instance

def get_connection_pool() -> ConnectionPoolManager:
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPoolManager()
    return _connection_pool

def get_query_monitor() -> QueryPerformanceMonitor:
    global _query_monitor
    if _query_monitor is None:
        _query_monitor = QueryPerformanceMonitor()
    return _query_monitor