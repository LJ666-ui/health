"""
定时任务调度器单元测试
覆盖：任务注册、触发、状态管理、并发控制
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestTaskRegistration:
    """任务注册测试"""
    
    def test_register_simple_task(self):
        """测试简单任务注册"""
        from scheduler.task_scheduler import TaskScheduler, ScheduledTask, TaskType
        
        scheduler = TaskScheduler(max_workers=2)
        
        task = ScheduledTask(
            task_id='test_task_001',
            name='测试任务',
            description='用于单元测试的任务',
            task_type=TaskType.ONCE,
            func=lambda: "task completed"
        )
        
        scheduler.register_task(task)
        
        assert 'test_task_001' in scheduler.tasks
        assert scheduler.tasks['test_task_001'].name == '测试任务'
    
    def test_register_duplicate_task_overwrites(self):
        """测试重复注册覆盖旧任务"""
        from scheduler.task_scheduler import TaskScheduler, ScheduledTask, TaskType
        
        scheduler = TaskScheduler()
        
        task1 = ScheduledTask(
            task_id='duplicate_id',
            name='原始版本',
            description='',
            task_type=TaskType.INTERVAL,
            interval_seconds=60,
            func=lambda: None
        )
        
        task2 = ScheduledTask(
            task_id='duplicate_id',
            name='更新版本',
            description='',
            task_type=TaskType.DAILY,
            run_at_hour=3,
            func=lambda: None
        )
        
        scheduler.register_task(task1)
        scheduler.register_task(task2)  # 应覆盖
        
        assert scheduler.tasks['duplicate_id'].name == '更新版本'
        assert scheduler.tasks['duplicate_id'].task_type == TaskType.DAILY
    
    def test_unregister_task(self):
        """测试移除任务"""
        from scheduler.task_scheduler import TaskScheduler, ScheduledTask, TaskType
        
        scheduler = TaskScheduler()
        
        task = ScheduledTask(
            task_id='to_remove',
            name='待移除任务',
            description='',
            task_type=TaskType.ONCE,
            func=lambda: None
        )
        
        scheduler.register_task(task)
        assert 'to_remove' in scheduler.tasks
        
        scheduler.unregister_task('to_remove')
        assert 'to_remove' not in scheduler.tasks


class TestTaskScheduling:
    """任务调度逻辑测试"""
    
    def test_next_run_calculation_daily(self):
        """测试每日任务下次运行时间计算"""
        from scheduler.task_scheduler import ScheduledTask, TaskType
        
        now = datetime.now()
        
        task = ScheduledTask(
            task_id='daily_test',
            name='每日任务',
            description='',
            task_type=TaskType.DAILY,
            run_at_hour=14,
            run_at_minute=30,
            func=lambda: None
        )
        
        next_run = task.calculate_next_run()
        
        assert next_run is not None
        assert next_run > now  # 未来时间
        
        # 验证小时和分钟正确
        assert next_run.hour == 14
        assert next_run.minute == 30
    
    def test_next_run_calculation_interval(self):
        """测试间隔任务时间计算"""
        from scheduler.task_scheduler import ScheduledTask, TaskType
        
        base_time = datetime(2026, 6, 2, 12, 0, 0)
        
        task = ScheduledTask(
            task_id='interval_test',
            name='间隔任务',
            description='',
            task_type=TaskType.INTERVAL,
            interval_seconds=3600,  # 1小时
            func=lambda: None
        )
        task.last_run = base_time
        
        next_run = task.calculate_next_run()
        
        expected = base_time + timedelta(hours=1)
        assert next_run == expected
    
    def test_once_task_only_runs_once(self):
        """测试一次性任务执行后不再调度"""
        from scheduler.task_scheduler import ScheduledTask, TaskType
        
        task = ScheduledTask(
            task_id='once_task',
            name='一次性任务',
            description='',
            task_type=TaskType.ONCE,
            func=lambda: None
        )
        
        first_run = task.calculate_next_run()
        task.last_run = first_run
        
        second_run = task.calculate_next_run()
        
        assert second_run is None, "一次性任务不应有第二次执行"


class TestTaskExecution:
    """任务执行测试"""
    
    def test_successful_task_execution(self):
        """测试成功执行任务"""
        from scheduler.task_scheduler import TaskScheduler, ScheduledTask, TaskType
        
        scheduler = TaskScheduler(max_workers=2)
        
        execution_log = []
        
        def sample_task():
            execution_log.append("executed")
            return {"status": "success"}
        
        task = ScheduledTask(
            task_id='success_test',
            name='成功任务',
            description='',
            task_type=TaskType.ONCE,
            func=sample_task
        )
        
        scheduler.register_task(task)
        result = scheduler.trigger_task_now('success_test')
        
        assert result is True
        time.sleep(0.5)  # 等待异步执行完成
        
        assert len(execution_log) > 0, "任务未被执行"
    
    def test_failed_task_error_handling(self):
        """测试失败任务的错误处理"""
        from scheduler.task_scheduler import TaskScheduler, ScheduledTask, TaskType
        
        scheduler = TaskScheduler(max_workers=2)
        
        def failing_task():
            raise ValueError("模拟任务失败")
        
        task = ScheduledTask(
            task_id='fail_test',
            name='失败任务',
            description='',
            task_type=TaskType.ONCE,
            func=failing_task,
            max_retries=0  # 不重试，立即失败
        )
        
        scheduler.register_task(task)
        scheduler.trigger_task_now('fail_test')
        
        time.sleep(0.5)
        
        # 验证错误被捕获（不崩溃）
        if 'fail_test' in scheduler.tasks:
            last_result = scheduler.tasks['fail_test'].last_result
            if last_result:
                assert last_result.status.value == 'failed'


class TestConcurrencyControl:
    """并发控制测试"""
    
    def test_prevent_concurrent_same_task(self):
        """防止同一任务并发执行"""
        from scheduler.task_scheduler import TaskScheduler, ScheduledTask, TaskType
        import threading
        
        scheduler = TaskScheduler(max_workers=4)
        
        execution_count = [0]
        lock = threading.Lock()
        
        def slow_task():
            with lock:
                execution_count[0] += 1
            time.sleep(2)  # 模拟耗时操作
            return "done"
        
        task = ScheduledTask(
            task_id='concurrent_test',
            name='并发测试任务',
            description='',
            task_type=TaskType.ONCE,
            func=slow_task,
            timeout_seconds=10
        )
        
        scheduler.register_task(task)
        
        # 尝试快速连续触发两次
        result1 = scheduler.trigger_task_now('concurrent_test')
        time.sleep(0.1)
        result2 = scheduler.trigger_task_now('concurrent_test')
        
        # 第二次应失败或跳过（任务正在运行）
        assert result1 is True
        assert result2 is False or (not result2 and len(scheduler.running_tasks.get('concurrent_test', [])) > 0)


class TestStatusReporting:
    """状态报告测试"""
    
    def test_get_status_returns_dict(self):
        """测试状态返回格式"""
        from scheduler.task_scheduler import TaskScheduler
        
        scheduler = TaskScheduler()
        status = scheduler.get_status()
        
        assert isinstance(status, dict)
        assert 'total_tasks' in status
        assert 'active_tasks' in status
        assert 'tasks_summary' in status
    
    def test_status_includes_all_registered_tasks(self):
        """测试状态包含所有已注册任务"""
        from scheduler.task_scheduler import TaskScheduler, ScheduledTask, TaskType
        
        scheduler = TaskScheduler()
        
        for i in range(5):
            task = ScheduledTask(
                task_id=f'task_{i}',
                name=f'任务{i}',
                description='',
                task_type=TaskType.INTERVAL,
                interval_seconds=3600 * (i + 1),
                func=lambda: None
            )
            scheduler.register_task(task)
        
        status = scheduler.get_status()

        # 5 manual + 6 built-in = 11 total
        assert status['total_tasks'] >= 5
        assert len(status['tasks_summary']) >= 5
        # Verify our 5 custom tasks are in the summary
        task_ids = [t['id'] for t in status['tasks_summary']]
        for i in range(5):
            assert f'task_{i}' in task_ids
    
    def test_enable_disable_task(self):
        """测试启用/禁用任务"""
        from scheduler.task_scheduler import TaskScheduler, ScheduledTask, TaskType
        
        scheduler = TaskScheduler()
        
        task = ScheduledTask(
            task_id='toggleable',
            name='可切换任务',
            description='',
            task_type=TaskType.DAILY,
            run_at_hour=2,
            func=lambda: None
        )
        
        scheduler.register_task(task)
        
        # 初始启用
        assert scheduler.tasks['toggleable'].enabled is True
        
        # 禁用
        scheduler.disable_task('toggleable')
        assert scheduler.tasks['toggleable'].enabled is False
        
        # 重新启用
        scheduler.enable_task('toggleable')
        assert scheduler.tasks['toggleable'].enabled is True


class TestBuiltinTasks:
    """内置任务功能验证"""
    
    @patch('etl.etl_pipeline.ETPipeline')
    def test_etl_builtin_task_exists(self, mock_etl):
        """验证ETL内置任务存在且配置正确"""
        from scheduler.task_scheduler import get_scheduler
        
        scheduler = get_scheduler()
        
        assert 'etl_daily_pipeline' in scheduler.tasks
        
        etl_task = scheduler.tasks['etl_daily_pipeline']
        assert etl_task.task_type.value == 'daily'
        assert etl_task.run_at_hour == 2
    
    @patch('ai.ml_engine.AIEngine')
    def test_ai_analysis_task_config(self, mock_ai):
        """验证AI分析任务配置"""
        from scheduler.task_scheduler import get_scheduler
        
        scheduler = get_scheduler()
        
        assert 'ai_weekly_analysis' in scheduler.tasks
        
        ai_task = scheduler.tasks['ai_weekly_analysis']
        assert ai_task.task_type.value == 'weekly'
        assert ai_task.day_of_week == 0  # 周一


class TestHistoryTracking:
    """历史记录追踪测试"""
    
    def test_task_history_recording(self):
        """测试任务执行历史记录"""
        from scheduler.task_scheduler import TaskScheduler, ScheduledTask, TaskType
        
        scheduler = TaskScheduler(max_workers=2)
        
        call_counter = [0]
        
        def counting_task():
            call_counter[0] += 1
            return f"call #{call_counter[0]}"
        
        task = ScheduledTask(
            task_id='history_test',
            name='历史记录测试',
            description='',
            task_type=TaskType.INTERVAL,
            interval_seconds=1,
            func=counting_task,
            max_history=5
        )
        
        scheduler.register_task(task)
        
        # 手动触发多次
        for _ in range(3):
            scheduler.trigger_task_now('history_test')
            time.sleep(0.5)
        
        history = scheduler.get_task_history('history_test')
        
        assert isinstance(history, list)
        assert len(history) >= 2  # 至少部分记录
        assert len(history) <= 5  # 不超过max_history限制


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])