"""
ZhiHealth 定时任务调度器
支持Cron表达式、固定间隔、一次性任务的自动化调度
用于ETL流程、AI分析、数据备份、健康检查等定时执行
"""

import json
import os
import time
import threading
import signal
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
from loguru import logger

try:
    from croniter import croniter
    CRON_AVAILABLE = True
except ImportError:
    CRON_AVAILABLE = False


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class TaskType(Enum):
    """任务类型"""
    ONCE = "once"                    # 一次性任务
    INTERVAL = "interval"            # 固定间隔
    DAILY = "daily"                  # 每日
    WEEKLY = "weekly"                # 每周
    MONTHLY = "monthly"              # 每月
    CRON = "cron"                    # Cron表达式


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    output: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': round(self.duration_seconds, 2),
            'output': str(self.output)[:500] if self.output else None,
            'error': str(self.error)[:500] if self.error else None,
            'retry_count': self.retry_count
        }


@dataclass 
class ScheduledTask:
    """计划任务定义"""
    task_id: str
    name: str
    description: str
    task_type: TaskType
    func: Callable
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    
    # 调度配置
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 3600
    
    # 时间配置（根据task_type使用不同字段）
    interval_seconds: Optional[int] = None      # INTERVAL类型
    run_at_hour: Optional[int] = None           # DAILY类型 (24小时制)
    run_at_minute: Optional[int] = None         # DAILY/WEEKLY/MONTHLY
    day_of_week: Optional[int] = None           # WEEKLY (0=周一, 6=周日)
    day_of_month: Optional[int] = None          # MONTHLY (1-31)
    cron_expression: Optional[str] = None       # CRON类型
    
    # 执行控制
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_result: Optional[TaskResult] = None
    run_history: List[TaskResult] = field(default_factory=list)
    max_history: int = 50
    
    # 统计信息
    total_runs: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_duration: float = 0.0
    
    def calculate_next_run(self) -> Optional[datetime]:
        """计算下次执行时间"""
        now = datetime.now()
        
        if self.task_type == TaskType.ONCE:
            if self.last_run is not None:
                return None  # 已执行过，不再运行
            return now + timedelta(seconds=10)  # 立即执行
            
        elif self.task_type == TaskType.INTERVAL:
            if self.interval_seconds is None:
                return None
            base_time = self.last_run or now
            return base_time + timedelta(seconds=self.interval_seconds)
            
        elif self.task_type == TaskType.DAILY:
            hour = self.run_at_hour or 2      # 默认凌晨2点
            minute = self.run_at_minute or 0
            
            next_date = now.date()
            next_time = datetime(next_date.year, next_date.month, next_date.day, hour, minute)
            
            if next_time <= now:
                next_time += timedelta(days=1)
                
            return next_time
            
        elif self.task_type == TaskType.WEEKLY:
            dow = self.day_of_week or 0  # 默认周一
            hour = self.run_at_hour or 2
            minute = self.run_at_minute or 0
            
            days_ahead = dow - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
                
            next_date = now + timedelta(days=days_ahead)
            next_time = datetime(
                next_date.year, next_date.month, next_date.day,
                hour, minute
            )
            
            return next_time
            
        elif self.task_type == TaskType.MONTHLY:
            dom = self.day_of_month or 1   # 默认每月1号
            hour = self.run_at_hour or 2
            minute = self.run_at_minute or 0
            
            year, month = now.year, now.month
            day = min(dom, 28)  # 避免无效日期
            
            next_time = datetime(year, month, day, hour, minute)
            if next_time <= now:
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
                day = min(dom, 28)
                next_time = datetime(year, month, day, hour, minute)
                
            return next_time
            
        elif self.task_type == TaskType.CRON:
            if not CRON_AVAILABLE or not self.cron_expression:
                logger.warning(f"Cron库未安装或未配置cron表达式: {self.task_id}")
                return None
                
            try:
                cron = croniter(self.cron_expression, now)
                return cron.get_next(datetime)
            except Exception as e:
                logger.error(f"Cron解析失败 {self.task_id}: {e}")
                return None
                
        else:
            return None


class TaskScheduler:
    """任务调度器 - 核心调度引擎"""
    
    def __init__(self, max_workers: int = 4):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running_tasks: Dict[str, Future] = {}
        self._stop_event = threading.Event()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._started = False
        
        # 注册内置任务
        self._register_builtin_tasks()
        
    def _register_builtin_tasks(self):
        """注册内置预置任务"""
        
        # ETL数据管道任务
        self.register_task(ScheduledTask(
            task_id="etl_daily_pipeline",
            name="每日数据ETL处理",
            description="每天凌晨2点自动执行完整ETL流程，从MySQL抽取数据并加载到各目标存储",
            task_type=TaskType.DAILY,
            func=self._run_etl_pipeline,
            run_at_hour=2,
            run_at_minute=0,
            timeout_seconds=1800,
            max_retries=2
        ))
        
        # AI综合分析任务
        self.register_task(ScheduledTask(
            task_id="ai_weekly_analysis",
            name="每周AI智能分析",
            description="每周一凌晨3点执行全面的AI分析，生成用户健康报告",
            task_type=TaskType.WEEKLY,
            func=self._run_ai_analysis,
            day_of_week=0,
            run_at_hour=3,
            run_at_minute=0,
            timeout_seconds=3600,
            max_retries=3
        ))
        
        # 数据备份任务
        self.register_task(ScheduledTask(
            task_id="backup_daily",
            name="每日数据备份",
            description="每天凌晨4点备份数据库和关键文件",
            task_type=TaskType.DAILY,
            func=self._run_data_backup,
            run_at_hour=4,
            run_at_minute=30,
            timeout_seconds=1200,
            max_retries=2
        ))
        
        # 健康检查任务
        self.register_task(ScheduledTask(
            task_id="health_check",
            name="系统健康检查",
            description="每5分钟检查所有系统组件状态",
            task_type=TaskType.INTERVAL,
            interval_seconds=300,
            func=self._run_health_check,
            timeout_seconds=60,
            max_retries=1
        ))
        
        # 数据清理任务
        self.register_task(ScheduledTask(
            task_id="cleanup_old_data",
            name="历史数据清理",
            description="每月1号清理90天前的日志和临时数据",
            task_type=TaskType.MONTHLY,
            func=self._run_cleanup,
            day_of_month=1,
            run_at_hour=5,
            run_at_minute=0,
            timeout_seconds=600,
            max_retries=1
        ))
        
        # 实时告警扫描任务
        self.register_task(ScheduledTask(
            task_id="alert_scan",
            name="实时异常扫描",
            description="每分钟扫描最新数据并触发告警规则",
            task_type=TaskType.INTERVAL,
            interval_seconds=60,
            func=self._run_alert_scan,
            timeout_seconds=60,
            max_retries=1
        ))
        
        logger.info(f"已注册 {len(self.tasks)} 个内置任务")
    
    def register_task(self, task: ScheduledTask):
        """注册新任务"""
        task.next_run = task.calculate_next_run()
        self.tasks[task.task_id] = task
        logger.info(f"注册任务: [{task.task_id}] {task.name} | 下次执行: {task.next_run}")
    
    def unregister_task(self, task_id: str):
        """移除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"已移除任务: {task_id}")
    
    def enable_task(self, task_id: str):
        """启用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self.tasks[task_id].next_run = self.tasks[task_id].calculate_next_run()
            logger.info(f"已启用任务: {task_id}")
    
    def disable_task(self, task_id: str):
        """禁用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            logger.info(f"已禁用任务: {task_id}")
    
    def trigger_task_now(self, task_id: str) -> bool:
        """立即触发任务执行"""
        if task_id not in self.tasks:
            logger.error(f"任务不存在: {task_id}")
            return False
            
        task = self.tasks[task_id]
        if task_id in self.running_tasks and not self.running_tasks[task_id].done():
            logger.warning(f"任务正在运行中: {task_id}")
            return False
            
        self._execute_task(task)
        return True
    
    def _execute_task(self, task: ScheduledTask):
        """执行单个任务（异步）"""
        if not task.enabled:
            logger.debug(f"任务已禁用，跳过: {task.task_id}")
            return
            
        def run_with_timeout():
            result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                start_time=datetime.now()
            )
            
            try:
                output = task.func(*task.args, **task.kwargs)
                result.status = TaskStatus.SUCCESS
                result.output = output
                task.success_count += 1
                
            except Exception as e:
                result.status = TaskStatus.FAILED
                result.error = str(e)
                task.failure_count += 1
                logger.error(f"任务执行失败 [{task.task_id}]: {e}", exc_info=True)
                
            finally:
                result.end_time = datetime.now()
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()
                
                task.last_run = result.start_time
                task.last_result = result
                task.total_runs += 1
                task.run_history.append(result)
                
                # 限制历史记录数量
                if len(task.run_history) > task.max_history:
                    task.run_history = task.run_history[-task.max_history:]
                    
                # 更新平均耗时
                durations = [r.duration_seconds for r in task.run_history[-10:]]
                task.average_duration = sum(durations) / len(durations) if durations else 0
                
                # 计算下次执行时间
                task.next_run = task.calculate_next_run()
                
                if task_id := task.task_id in self.running_tasks:
                    del self.running_tasks[task_id]
                    
            return result
        
        future = self.executor.submit(run_with_timeout)
        self.running_tasks[task.task_id] = future
        logger.info(f"[{task.task_id}] 任务已提交执行")
    
    def _scheduler_loop(self):
        """主调度循环"""
        logger.info("调度器启动，开始监控任务...")
        
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                
                for task_id, task in list(self.tasks.items()):
                    if not task.enabled:
                        continue
                        
                    if task.next_run and now >= task.next_run:
                        if task_id not in self.running_tasks or self.running_tasks[task_id].done():
                            self._execute_task(task)
                            
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"调度循环异常: {e}", exc_info=True)
                time.sleep(5)
                
        logger.info("调度器已停止")
    
    def start(self):
        """启动调度器"""
        if self._started:
            logger.warning("调度器已在运行中")
            return
            
        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        self._started = True
        
        logger.info("="*70)
        logger.info("  ZhiHealth 定时任务调度器已启动")
        logger.info(f"  已注册任务数: {len(self.tasks)}")
        logger.info(f"  工作线程数: {self.executor._max_workers}")
        logger.info("="*70)
    
    def stop(self):
        """停止调度器"""
        self._stop_event.set()
        self._started = False
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=10)
            
        self.executor.shutdown(wait=False, cancel_futures=True)
        logger.info("调度器已停止")
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        active_tasks = sum(1 for t in self.tasks.values() if t.enabled)
        running_now = [tid for tid, f in self.running_tasks.items() if not f.done()]
        
        return {
            'status': 'running' if self._started else 'stopped',
            'total_tasks': len(self.tasks),
            'active_tasks': active_tasks,
            'running_now': running_now,
            'uptime_info': self._get_uptime(),
            'tasks_summary': [
                {
                    'id': t.task_id,
                    'name': t.name,
                    'type': t.task_type.value,
                    'enabled': t.enabled,
                    'next_run': t.next_run.isoformat() if t.next_run else None,
                    'last_run': t.last_run.isoformat() if t.last_run else None,
                    'total_runs': t.total_runs,
                    'success_rate': f"{(t.success_count/max(t.total_runs,1)*100):.1f}%",
                    'avg_duration': f"{t.average_duration:.2f}s",
                    'status': 'RUNNING' if t.task_id in running_now else 'IDLE'
                }
                for t in sorted(self.tasks.values(), key=lambda x: x.name)
            ]
        }
    
    def get_task_history(self, task_id: str, limit: int = 20) -> List[Dict]:
        """获取任务执行历史"""
        if task_id not in self.tasks:
            return []
            
        history = self.tasks[task_id].run_history[-limit:]
        return [r.to_dict() for r in reversed(history)]
    
    def _get_uptime(self) -> str:
        """获取运行时长（简化版）"""
        return "N/A" if not self._started else "running"
    
    # ==================== 内置任务实现 ====================
    
    def _run_etl_pipeline(self) -> Dict:
        """执行ETL数据管道"""
        from etl.etl_pipeline import ETPipeline
        
        pipeline = ETPipeline()
        stats = pipeline.run_full_pipeline(source_table='health_record')
        pipeline.close_connections()
        
        return {
            'message': 'ETL流程完成',
            'stats': stats
        }
    
    def _run_ai_analysis(self) -> Dict:
        """执行AI分析"""
        from ai.ml_engine import AIEngine
        from etl.etl_pipeline import ETPipeline
        
        engine = AIEngine()
        pipeline = ETPipeline()
        
        df = pipeline.extract_from_mysql(batch_size=10000)
        pipeline.close_connections()
        
        results = engine.run_comprehensive_analysis(df.head(5000))
        
        report_path = engine.generate_ai_report(
            df, 
            output_path=f"reports/ai_auto_{datetime.now().strftime('%Y%m%d')}.txt"
        )
        
        return {
            'message': 'AI分析完成',
            'records_processed': len(df),
            'report_saved': report_path is not None
        }
    
    def _run_data_backup(self) -> Dict:
        """执行数据备份"""
        backup_dir = f"backups/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_files = []
        
        # 备份关键目录
        dirs_to_backup = ['ai/models', 'reports', 'logs']
        for dir_name in dirs_to_backup:
            src_dir = dir_name
            if os.path.exists(src_dir):
                import shutil
                dst = os.path.join(backup_dir, dir_name)
                shutil.copytree(src_dir, dst, ignore=shutil.ignore_patterns('*.pyc'))
                backup_files.append(dir_name)
                
        return {
            'message': '数据备份完成',
            'backup_location': backup_dir,
            'backed_up_items': backup_files
        }
    
    def _run_health_check(self) -> Dict:
        """系统健康检查"""
        checks = {}
        
        # MySQL连接测试
        checks['mysql'] = {'status': 'unknown'}
        try:
            from etl.etl_pipeline import ETPipeline
            p = ETPipeline()
            checks['mysql']['status'] = 'connected' if p._connect_mysql() else 'failed'
            p.close_connections()
        except Exception as e:
            checks['mysql']['status'] = 'error'
            checks['mysql']['error'] = str(e)[:100]
            
        # Redis连接测试
        checks['redis'] = {'status': 'unknown'}
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_timeout=3)
            r.ping()
            checks['redis']['status'] = 'connected'
        except Exception as e:
            checks['redis']['status'] = 'disconnected'
            
        # MongoDB连接测试
        checks['mongodb'] = {'status': 'unknown'}
        try:
            from pymongo import MongoClient
            client = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=3000)
            client.server_info()
            checks['mongodb']['status'] = 'connected'
        except Exception as e:
            checks['mongodb']['status'] = 'disconnected'
            
        # InfluxDB连接测试
        checks['influxdb'] = {'status': 'unknown'}
        try:
            from influxdb_client import InfluxDBClient
            c = InfluxDBClient(url='http://localhost:8086', token='test', org='zhihealth')
            c.health()
            checks['influxdb']['status'] = 'connected'
        except Exception as e:
            checks['influxdb']['status'] = 'disconnected'
            
        all_healthy = all(c.get('status') == 'connected' for c in checks.values())
        
        return {
            'overall_status': 'healthy' if all_healthy else 'degraded',
            'checks': checks,
            'timestamp': datetime.now().isoformat()
        }
    
    def _run_cleanup(self) -> Dict:
        """清理旧数据"""
        cleaned = {}
        
        # 清理旧日志
        log_dir = 'logs'
        if os.path.exists(log_dir):
            count = 0
            cutoff = datetime.now() - timedelta(days=90)
            for f in os.listdir(log_dir):
                fpath = os.path.join(log_dir, f)
                if os.path.isfile(fpath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        os.remove(fpath)
                        count += 1
            cleaned['old_logs_deleted'] = count
            
        # 清理旧报告
        report_dir = 'reports'
        if os.path.exists(report_dir):
            count = 0
            cutoff = datetime.now() - timedelta(days=180)
            for f in os.listdir(report_dir):
                fpath = os.path.join(report_dir, f)
                if os.path.isfile(fpath):
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        os.remove(fpath)
                        count += 1
            cleaned['old_reports_deleted'] = count
            
        return {
            'message': '数据清理完成',
            'cleaned_items': cleaned
        }
    
    def _run_alert_scan(self) -> Dict:
        """实时异常扫描"""
        from alerting.alert_engine import AlertEngine
        from etl.etl_pipeline import ETPipeline
        
        engine = AlertEngine()
        pipeline = ETPipeline()
        
        try:
            df = pipeline.extract_from_mysql(batch_size=200)
            pipeline.close_connections()
            
            if df.empty:
                return {'message': '无新数据需要扫描', 'alerts_found': 0}
                
            recent_records = df.tail(20).to_dict("orient='records'")
            result = engine.process_batch(recent_records)
            
            return {
                'message': '异常扫描完成',
                **result
            }
            
        except Exception as e:
            return {
                'message': f'扫描异常: {str(e)}',
                'alerts_found': 0
            }


# 全局调度器实例
_global_scheduler: Optional[TaskScheduler] = None

def get_scheduler() -> TaskScheduler:
    """获取全局调度器实例"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = TaskScheduler(max_workers=4)
    return _global_scheduler


def main():
    """命令行入口 - 运行调度器守护进程"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ZhiHealth 定时任务调度器')
    subparsers = parser.add_subparsers(dest='command')
    
    # 运行命令
    run_parser = subparsers.add_parser('run', help='启动调度器守护进程')
    run_parser.add_argument('--workers', type=int, default=4, help='工作线程数')
    
    # 状态命令
    status_parser = subparsers.add_parser('status', help='查看调度状态')
    
    # 触发命令
    trigger_parser = subparsers.add_parser('trigger', help='手动触发任务')
    trigger_parser.add_argument('--task-id', required=True, help='任务ID')
    
    # 列表命令
    list_parser = subparsers.add_parser('list', help='列出所有注册任务')
    
    args = parser.parse_args()
    
    scheduler = get_scheduler()
    
    if args.command == 'run':
        print("\n" + "="*70)
        print("  ZhiHealth 定时任务调度器")
        print("="*70)
        print(f"\n  工作线程: {args.workers}")
        print("  按 Ctrl+C 停止\n")
        
        signal.signal(signal.SIGINT, lambda s, f: scheduler.stop())
        signal.signal(signal.SIGTERM, lambda s, f: scheduler.stop())
        
        scheduler.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            
    elif args.command == 'status':
        status = scheduler.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False, default=str))
        
    elif args.command == 'trigger':
        success = scheduler.trigger_task_now(args.task_id)
        if success:
            print(f"[OK] 任务 {args.task_id} 已触发")
        else:
            print(f"[FAIL] 无法触发任务 {args.task_id}")
            
    elif args.command == 'list':
        tasks = scheduler.tasks
        print(f"\n{'='*70}")
        print(f"  已注册任务列表 ({len(tasks)} 个)")
        print(f"{'='*70}\n")
        
        for task in sorted(tasks.values(), key=lambda x: x.name):
            status_icon = "✅" if task.enabled else "⭕"
            type_icon = {
                'once': '①', 'interval': '🔄', 'daily': '📅',
                'weekly': '📆', 'monthly': '🗓️', 'cron': '⏰'
            }.get(task.task_type.value, '❓')
            
            print(f"{status_icon} {type_icon} [{task.task_id:25s}] {task.name}")
            print(f"    类型: {task.task_type.value:12s} | "
                  f"下次: {task.next_run.strftime('%Y-%m-%d %H:%M') if task.next_run else 'N/A':20s} | "
                  f"运行: {task.total_runs}次 | 成功率: {(task.success_count/max(task.total_runs,1)*100):.1f}%")
            print()
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()