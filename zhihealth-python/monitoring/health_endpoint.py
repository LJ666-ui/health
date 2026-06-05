"""
系统健康检查与就绪探针
提供 /health 和 /ready 端点用于K8s/Docker监控
"""

import time
import platform
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"    # 部分功能受损但仍可用
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """组件健康状态"""
    name: str
    status: HealthStatus
    response_time_ms: float = 0.0
    message: str = ""
    last_check: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'status': self.status.value,
            'response_time_ms': round(self.response_time_ms, 2),
            'message': self.message,
            'last_check': self.last_check.isoformat()
        }


class SystemHealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        self._components: Dict[str, ComponentHealth] = {}
        self._startup_time: datetime = datetime.now()
        self._check_history: List[Dict] = []
        self._max_history_size: int = 100
        
        # 注册内置健康检查项
        self._register_builtin_checks()
    
    def _register_builtin_checks(self):
        """注册默认的健康检查组件"""
        builtin_checks = [
            ('system', self._check_system_resources),
            ('mysql', self._check_mysql_connection),
            ('redis', self._check_redis_connection),
            ('mongodb', self._check_mongodb_connection),
            ('influxdb', self._check_influxdb_connection),
            ('disk_space', self._check_disk_usage),
            ('memory', self._check_memory_status),
        ]
        
        for name, check_func in builtin_checks:
            self.register_component(name, check_func)
    
    def register_component(self, name: str, check_func: callable):
        """
        注册健康检查组件
        
        Args:
            name: 组件名称（唯一标识）
            check_func: 检查函数，返回 (status: HealthStatus, message: str, latency: float)
        """
        self._components[name] = ComponentHealth(
            name=name,
            status=HealthStatus.UNKNOWN,
            check_function=check_func
        )
        logger.debug(f"注册健康检查组件: {name}")
    
    def run_all_checks(self) -> Dict:
        """
        执行所有组件的健康检查
        
        Returns:
            完整的健康报告字典
        """
        results = {}
        
        for name, component in self._components.items():
            try:
                start_time = time.time()
                
                if hasattr(component, 'check_function'):
                    status, message, _ = component.check_function()
                else:
                    status, message = HealthStatus.UNKNOWN, "未配置检查函数"
                
                latency = (time.time() - start_time) * 1000
                
                component.status = status
                component.message = message
                component.response_time_ms = latency
                component.last_check = datetime.now()
                
                results[name] = component.to_dict()
                
            except Exception as e:
                logger.error(f"健康检查异常 [{name}]: {e}")
                results[name] = {
                    'name': name,
                    'status': HealthStatus.UNHEALTHY.value,
                    'response_time_ms': 0,
                    'message': f'检查异常: {str(e)[:200]}',
                    'last_check': datetime.now().isoformat()
                }
        
        # 记录历史
        overall_status = self._calculate_overall_status(results)
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status.value,
            'component_count': len(results),
            'unhealthy_count': sum(1 for r in results.values() 
                                  if r['status'] != HealthStatus.HEALTHY.value)
        }
        
        self._check_history.append(history_entry)
        if len(self._check_history) > self._max_history_size:
            self._check_history.pop(0)
        
        return {
            'status': overall_status.value,
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': (datetime.now() - self._startup_time).total_seconds(),
            'version': '2.0.0',
            'components': results,
            'checks_summary': {
                'total': len(results),
                'healthy': sum(1 for r in results.values() 
                              if r['status'] == HealthStatus.HEALTHY.value),
                'degraded': sum(1 for r in results.values() 
                               if r['status'] == HealthStatus.DEGRADED.value),
                'unhealthy': sum(1 for r in results.values() 
                                if r['status'] == HealthStatus.UNHEALTHY.value)
            }
        }
    
    def _calculate_overall_status(self, components: Dict) -> HealthStatus:
        """计算整体健康状态"""
        statuses = [comp['status'] for comp in components.values()]
        
        if HealthStatus.UNHEALTHY.value in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED.value in statuses or HealthStatus.UNKNOWN.value in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    # ==================== 具体检查实现 ====================
    
    def _check_system_resources(self) -> Tuple[HealthStatus, str, float]:
        """检查系统资源（CPU/内存）"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            
            issues = []
            
            if cpu_percent > 90:
                issues.append(f"CPU使用率过高: {cpu_percent}%")
            if memory.percent > 90:
                issues.append(f"内存使用率过高: {memory.percent}%")
            
            if issues:
                return (
                    HealthStatus.DEGRADED if len(issues) < 2 else HealthStatus.UNHEALTHY,
                    "; ".join(issues), 
                    500
                )
            else:
                return (
                    HealthStatus.HEALTHY,
                    f"CPU:{cpu_percent}% MEM:{memory.percent}%",
                    500
                )
                
        except Exception as e:
            return HealthStatus.UNKNOWN, f"无法获取系统信息: {e}", 0
    
    def _check_mysql_connection(self) -> Tuple[HealthStatus, str, float]:
        """检查MySQL连接"""
        start = time.time()
        try:
            import pymysql
            
            from config.config import get_config
            cfg = get_config()
            
            conn = pymysql.connect(
                host=getattr(cfg, 'mysql_host', 'localhost'),
                port=getattr(cfg, 'mysql_port', 3306),
                user=getattr(cfg, 'mysql_user', 'root'),
                password=getattr(cfg, 'mysql_password', ''),
                database='zhihealth',
                connect_timeout=3,
                read_timeout=3
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
            conn.close()
            
            latency = (time.time() - start) * 1000
            return HealthStatus.HEALTHY, f"MySQL连接正常 ({latency:.0f}ms)", latency
            
        except ImportError:
            return HealthStatus.UNKNOWN, "pymysql未安装", 0
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"MySQL连接失败: {str(e)[:100]}", 0
    
    def _check_redis_connection(self) -> Tuple[HealthStatus, str, float]:
        """检查Redis连接"""
        start = time.time()
        try:
            import redis
            
            r = redis.Redis(
                host='localhost',
                port=6379,
                socket_timeout=2,
                socket_connect_timeout=2
            )
            
            result = r.ping()
            latency = (time.time() - start) * 1000
            
            if result:
                return HealthStatus.HEALTHY, f"Redis连接正常 ({latency:.0f}ms)", latency
            else:
                return HealthStatus.UNHEALTHY, "Redis PING失败", latency
                
        except ImportError:
            return HealthStatus.UNKNOWN, "redis-py未安装", 0
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Redis连接失败: {str(e)[:100]}", 0
    
    def _check_mongodb_connection(self) -> Tuple[HealthStatus, str, float]:
        """检查MongoDB连接"""
        start = time.time()
        try:
            from pymongo import MongoClient
            
            client = MongoClient('mongodb://localhost:27017', 
                               serverSelectionTimeoutMS=3000)
            client.server_info()
            
            latency = (time.time() - start) * 1000
            return HealthStatus.HEALTHY, f"MongoDB连接正常 ({latency:.0f}ms)", latency
            
        except ImportError:
            return HealthStatus.UNKNOWN, "pymongo未安装", 0
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"MongoDB连接失败: {str(e)[:100]}", 0
    
    def _check_influxdb_connection(self) -> Tuple[HealthStatus, str, float]:
        """检查InfluxDB连接"""
        start = time.time()
        try:
            from influxdb_client import InfluxDBClient
            
            client = InfluxDBClient(url="http://localhost:8086",
                                   token="test-token",
                                   org="zhihealth")
            health = client.health()
            
            latency = (time.time() - start) * 1000
            
            if health.status == "pass":
                return HealthStatus.HEALTHY, f"InfluxDB连接正常 ({latency:.0f}ms)", latency
            else:
                return HealthStatus.UNHEALTHY, f"InfluxDB状态: {health.status}", latency
                
        except ImportError:
            return HealthStatus.UNKNOWN, "influxdb-client未安装", 0
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"InfluxDB连接失败: {str(e)[:100]}", 0
    
    def _check_disk_usage(self) -> Tuple[HealthStatus, str, float]:
        """检查磁盘空间"""
        try:
            disk = psutil.disk_usage('/')
            usage_percent = disk.used / disk.total * 100
            
            if usage_percent > 95:
                return HealthStatus.UNHEALTHY, f"磁盘空间严重不足: {usage_percent:.1f}%", 10
            elif usage_percent > 85:
                return HealthStatus.DEGRADED, f"磁盘空间紧张: {usage_percent:.1f}%", 10
            else:
                return HealthStatus.HEALTHY, f"磁盘使用率: {usage_percent:.1f}%", 10
                
        except Exception as e:
            return HealthStatus.UNKNOWN, f"磁盘检查失败: {e}", 0
    
    def _check_memory_status(self) -> Tuple[HealthStatus, str, float]:
        """详细内存状态检查"""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            issues = []
            
            if mem.available < 512 * 1024 * 1024:  # 小于512MB
                issues.append(f"可用内存不足: {mem.available/(1024**3):.1f}GB")
            if swap.percent > 50 and swap.total > 0:
                issues.append(f"Swap使用率高: {swap.percent}%")
            
            if issues:
                return (
                    HealthStatus.DEGRADED,
                    "; ".join(issues),
                    10
                )
            else:
                return (
                    HealthStatus.HEALTHY,
                    f"可用内存: {mem.available/(1024**3):.1f}GB / 总计: {mem.total/(1024**3):.1f}GB",
                    10
                )
                
        except Exception as e:
            return HealthStatus.UNKNOWN, f"内存检查失败: {e}", 0
    
    def get_health_history(self, limit: int = 20) -> List[Dict]:
        """获取最近N次健康检查记录"""
        return self._check_history[-limit:]


# 全局实例
_health_checker: Optional[SystemHealthChecker] = None

def get_health_checker() -> SystemHealthChecker:
    """获取全局健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = SystemHealthChecker()
    return _health_checker


# Flask路由处理器
def create_health_endpoints(app):
    """为Flask应用创建健康检查端点"""
    
    @app.route('/health')
    def health_endpoint():
        """Liveness探针：服务是否存活"""
        checker = get_health_checker()
        report = checker.run_all_checks()
        
        from flask import jsonify
        
        status_code = 200 if report['status'] == 'healthy' else 503
        
        return jsonify(report), status_code
    
    @app.route('/ready')
    def ready_endpoint():
        """Readiness探针：服务是否准备好接收请求"""
        from flask import jsonify
        
        # 简单的快速检查（不执行完整检查）
        basic_checks = {
            'status': 'ready',
            'timestamp': datetime.now().isoformat(),
            'checks_passed': True,
            'message': 'Service is ready to accept traffic'
        }
        
        return jsonify(basic_checks), 200