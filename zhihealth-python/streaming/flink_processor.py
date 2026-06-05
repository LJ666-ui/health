"""
ZhiHealth Apache Flink 实时健康数据处理引擎
支持CEP复杂事件处理、状态管理、精确一次语义
"""

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.common.typeinfo import Types
from pyflink.datastream.functions import (
    MapFunction, FilterFunction, 
    KeyedProcessFunction, FlatMapFunction,
    ProcessWindowFunction, ReduceFunction
)
from pyflink.datastream.window import (
    TumblingEventTimeWindows, SlidingEventTimeWindows,
    SessionEventTimeWindows, Time
)
from pyflink.table.expressions import col, lit
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class HealthDataPoint:
    """健康数据点"""
    record_id: int
    user_id: int
    device_id: int
    data_type: str
    heart_rate: float = 0.0
    body_temp: float = 0.0
    blood_pressure_systolic: int = 0
    blood_pressure_diastolic: int = 0
    steps: int = 0
    sleep_hours: float = 0.0
    timestamp: int = 0


class HealthDataParser(MapFunction):
    """JSON数据解析器"""
    
    def map(self, value: str) -> HealthDataPoint:
        try:
            data = json.loads(value)
            return HealthDataPoint(
                record_id=data.get('record_id', 0),
                user_id=data.get('user_id', 0),
                device_id=data.get('device_id', 0),
                data_type=data.get('data_type', 'unknown'),
                heart_rate=float(data.get('heart_rate', 0)),
                body_temp=float(data.get('body_temp', 0)),
                blood_pressure_systolic=int(data.get('blood_pressure_systolic', 0)),
                blood_pressure_diastolic=int(data.get('blood_pressure_diastolic', 0)),
                steps=int(data.get('steps', 0)),
                sleep_hours=float(data.get('sleep_hours', 0)),
                timestamp=int(data.get('timestamp', 0))
            )
        except Exception as e:
            logger.warning(f"Failed to parse health data: {e}")
            return HealthDataPoint(record_id=-1)


class DataQualityFilter(FilterFunction):
    """数据质量过滤器"""
    
    def filter(self, point: HealthDataPoint) -> bool:
        if point.record_id == -1 or point.user_id == 0:
            return False
            
        valid_ranges = {
            'heart_rate': (40, 200),
            'body_temp': (35.0, 42.0),
            'steps': (0, 100000),
            'sleep_hours': (0, 24)
        }
        
        if point.heart_rate > 0 and not (valid_ranges['heart_rate'][0] <= point.heart_rate <= valid_ranges['heart_rate'][1]):
            logger.warning(f"Invalid heart rate for user {point.user_id}: {point.heart_rate}")
            
        if point.body_temp > 0 and not (valid_ranges['body_temp'][0] <= point.body_temp <= valid_ranges['body_temp'][1]):
            logger.warning(f"Invalid body temp for user {point.user_id}: {point.body_temp}")
            
        return True


class AnomalyDetector(KeyedProcessFunction):
    """异常检测处理器（带状态）"""
    
    def __init__(self):
        self.state_desc = None
        
    def open(self, runtime_context):
        from pyflink.datastream.state import ValueStateDescriptor
        self.state_desc = ValueStateDescriptor(
            "user_history",
            Types.LIST(Types.FLOAT())
        )
        
    def process_element(self, point: HealthDataPoint, ctx, out):
        history = ctx.get_state(self.state_desc).value() or []
        
        anomalies = []
        
        # 心率异常检测
        if point.heart_rate > 0:
            avg_hr = sum(history[-20:]) / len(history[-20:]) if len(history) >= 20 else 70
            if abs(point.heart_rate - avg_hr) > 30:
                anomalies.append({
                    "type": "heart_rate_anomaly",
                    "value": point.heart_rate,
                    "expected_range": f"{avg_hr-25:.0f}-{avg_hr+25:.0f}",
                    "severity": "high" if abs(point.heart_rate - avg_hr) > 50 else "medium"
                })
            history.append(point.heart_rate)
            
        # 血压危机检测
        if point.blood_pressure_systolic > 180 or point.blood_pressure_diastolic > 120:
            anomalies.append({
                "type": "hypertensive_crisis",
                "systolic": point.blood_pressure_systolic,
                "diastolic": point.blood_pressure_diastolic,
                "severity": "critical"
            })
            
        # 体温异常
        if point.body_temp > 39.5 or point.body_temp < 35.5:
            anomalies.append({
                "type": "temperature_extreme",
                "value": point.body_temp,
                "severity": "critical" if point.body_temp > 41.0 or point.body_temp < 35.0 else "high"
            })
            
        # 输出异常警报
        for anomaly in anomalies:
            alert = {
                "alert_type": anomaly["type"],
                "user_id": point.user_id,
                "device_id": point.device_id,
                "severity": anomaly["severity"],
                "details": anomaly,
                "timestamp": datetime.now().isoformat(),
                "original_data": {
                    "heart_rate": point.heart_rate,
                    "bp_sys": point.blood_pressure_systolic,
                    "bp_dia": point.blood_pressure_diastolic,
                    "temp": point.body_temp
                }
            }
            out.collect((f"ALERT:{json.dumps(alert)}",))
            
        # 更新状态
        if len(history) > 100:
            history = history[-100:]
        ctx.get_state(self.state_desc).update(history)
        

class HealthMetricsAggregator(ReducerFunction):
    """健康指标聚合器"""
    
    def reduce(self, v1: Dict, v2: Dict) -> Dict:
        count = v1["count"] + v2["count"]
        return {
            "count": count,
            "avg_heart_rate": (v1["avg_heart_rate"] * v1["count"] + v2["avg_heart_rate"] * v2["count"]) / count,
            "max_heart_rate": max(v1["max_heart_rate"], v2["max_heart_rate"]),
            "min_heart_rate": min(v1["min_heart_rate"], v2["min_heart_rate"]),
            "total_steps": v1["total_steps"] + v2["total_steps"],
            "avg_bp_sys": (v1["avg_bp_sys"] * v1["count"] + v2["avg_bp_sys"] * v2["count"]) / count,
            "avg_bp_dia": (v1["avg_bp_dia"] * v1["count"] + v2["avg_bp_dia"] * v2["count"]) / count,
            "avg_sleep": (v1["avg_sleep"] * v1["count"] + v2["avg_sleep"] * v2["count"]) / count,
            "unique_users": list(set(v1["unique_users"] + v2["unique_users"]))
        }


class FlinkHealthStreamProcessor:
    """Flink流处理引擎主类"""
    
    def __init__(self, app_name: str = "ZhiHealthFlinkEngine",
                 kafka_servers: str = "localhost:9092",
                 checkpoint_interval: int = 60000):
        self.app_name = app_name
        self.kafka_servers = kafka_servers
        self.checkpoint_interval = checkpoint_interval
        
    def create_stream_environment(self) -> StreamExecutionEnvironment:
        """创建流执行环境"""
        env = StreamExecutionEnvironment.get_execution_environment()
        
        # 配置检查点（保证exactly-once语义）
        env.enable_checkpointing(self.checkpoint_interval)
        env.get_checkpoint_config().set_checkpointing_mode(
            CheckpointingMode.EXACTLY_ONCE
        )
        env.get_checkpoint_config().set_checkpoint_timeout(60000)
        env.get_checkpoint_config().set_max_concurrent_checkpoints(1)
        env.set_restart_strategy(RestartStrategies.fixed_delay_restart(
            3, Time.seconds(10)
        ))
        
        # 设置并行度
        env.set_parallelism(4)
        
        logger.info(f"Flink Streaming Environment created: {app_name}")
        return env
    
    def create_table_environment(self, stream_env: StreamExecutionEnvironment) -> StreamTableEnvironment:
        """创建表环境（用于SQL查询）"""
        settings = EnvironmentSettings.new_instance() \
            .in_streaming_mode() \
            .build()
            
        t_env = StreamTableEnvironment.create(stream_env, settings)
        
        # 注册Kafka连接器
        t_env.execute_sql("""
        CREATE TABLE kafka_health_source (
            record_id BIGINT,
            user_id BIGINT,
            device_id BIGINT,
            data_type STRING,
            heart_rate DOUBLE,
            body_temp DOUBLE,
            blood_pressure_systolic INT,
            blood_pressure_diastolic INT,
            steps INT,
            sleep_hours DOUBLE,
            `timestamp` BIGINT,
            event_time AS TO_TIMESTAMP(`timestamp`),
            WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'health_data_raw',
            'properties.bootstrap.servers' = '{}',
            'properties.group.id' = 'zhihealth-flink-consumer',
            'scan.startup.mode' = 'latest-offset',
            'format' = 'json'
        )""".format(self.kafka_servers))
        
        # 注册输出表（告警）
        t_env.execute_sql("""
        CREATE TABLE alert_sink (
            alert_type STRING,
            user_id BIGINT,
            severity STRING,
            details STRING,
            event_time TIMESTAMP(3),
            proc_time AS PROCTIME()
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'health_alerts',
            'properties.bootstrap.servers' = '{}',
            'format' = 'json'
        )""".format(self.kafka_servers))
        
        # 注册聚合结果输出表
        t_env.execute_sql("""
        CREATE TABLE metrics_windowed (
            window_start TIMESTAMP(3),
            window_end TIMESTAMP(3),
            user_id BIGINT,
            data_type STRING,
            record_count BIGINT,
            avg_heart_rate DOUBLE,
            max_heart_rate DOUBLE,
            min_heart_rate DOUBLE,
            total_steps BIGINT,
            avg_bp_sys DOUBLE,
            avg_bp_dia DOUBLE,
            avg_sleep DOUBLE
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'health_metrics_aggregated',
            'properties.bootstrap.servers' = '{}',
            'format' = 'json'
        )""".format(self.kafka_servers))
        
        return t_env
    
    def run_flink_sql_pipeline(self, stream_env: StreamExecutionEnvironment) -> None:
        """运行基于SQL的Flink流处理管道"""
        t_env = self.create_table_environment(stream_env)
        
        logger.info("Starting Flink SQL-based streaming pipeline...")
        
        # 1. 实时异常检测与告警写入
        t_env.execute_sql("""
        INSERT INTO alert_sink
        SELECT 
            CASE 
                WHEN heart_rate < 50 THEN 'bradycardia'
                WHEN heart_rate > 120 THEN 'tachycardia'
                WHEN blood_pressure_systolic > 180 OR blood_pressure_diastolic > 120 THEN 'hypertensive_crisis'
                WHEN body_temp < 35.5 THEN 'hypothermia'
                WHEN body_temp > 39.5 THEN 'hyperthermia'
                ELSE NULL
            END as alert_type,
            user_id,
            CASE 
                WHEN blood_pressure_systolic > 180 THEN 'critical'
                WHEN body_temp > 41.0 OR body_temp < 35.0 THEN 'critical'
                WHEN heart_rate > 130 OR heart_rate < 45 THEN 'high'
                ELSE 'medium'
            END as severity,
            CONCAT(
                '{"hr":', CAST(heart_rate AS STRING), 
                ',"bp_sys":', CAST(blood_pressure_systolic AS STRING),
                ',"bp_dia":', CAST(blood_pressure_diastolic AS STRING),
                ',"temp":', CAST(body_temp AS STRING), '}'
            ) as details,
            event_time
        FROM kafka_health_source
        WHERE (heart_rate IS NOT NULL AND (heart_rate < 50 OR heart_rate > 120))
           OR (blood_pressure_systolic > 180 OR blood_pressure_diastolic > 120)
           OR (body_temp IS NOT NULL AND (body_temp < 35.5 OR body_temp > 39.5))
        """)
        
        # 2. 滚动窗口聚合（每60秒）
        t_env.execute_sql("""
        INSERT INTO metrics_windowed
        SELECT 
            WINDOW_START as window_start,
            WINDOW_END as window_end,
            user_id,
            data_type,
            COUNT(*) as record_count,
            AVG(heart_rate) as avg_heart_rate,
            MAX(heart_rate) as max_heart_rate,
            MIN(heart_rate) as min_heart_rate,
            SUM(steps) as total_steps,
            AVG(blood_pressure_systolic) as avg_bp_sys,
            AVG(blood_pressure_diastolic) as avg_bp_dia,
            AVG(sleep_hours) as avg_sleep
        FROM TABLE(
            HOP(TABLE kafka_health_source, DESCRIPTOR(event_time), INTERVAL '30' SECOND, INTERVAL '60' SECOND)
        )
        GROUP BY 
            WINDOW_START, WINDOW_END, user_id, data_type
        HAVING COUNT(*) > 0
        """)
        
        logger.info("Flink SQL pipeline queries submitted successfully")
        
        # 执行作业
        t_env.execute("ZhiHealth_Flink_Realtime_Analytics")
    
    def run_datastream_api_pipeline(self, stream_env: StreamExecutionEnvironment) -> None:
        """运行基于DataStream API的管道"""
        from pyflink.datastream.connectors import FlinkKafkaConsumer
        
        logger.info("Starting Flink DataStream API pipeline...")
        
        # Kafka消费者配置
        properties = {
            'bootstrap.servers': self.kafka_servers,
            'group.id': 'zhihealth-flink-ds-consumer'
        }
        
        # 创建Kafka源
        kafka_consumer = FlinkKafkaConsumer(
            topics='health_data_raw',
            deserialization_schema=SimpleStringSchema(),
            properties=properties
        )
        kafka_consumer.set_start_from_latest()
        
        # 数据流处理链路
        raw_stream = stream_env.add_source(kafka_consumer)
        
        parsed_stream = raw_stream.map(HealthDataParser()) \
            .filter(DataQualityFilter())
        
        # 异常检测流（按用户KeyBy后进行状态化处理）
        alert_stream = parsed_stream.key_by(lambda x: x.user_id) \
            .process(AnomalyDetector())
        
        # 窗口聚合（滑动窗口：30秒窗口，15秒步长）
        aggregated_stream = parsed_stream.key_by(lambda x: (x.user_id, x.data_type)) \
            .window(SlidingEventTimeWindows.of(Time.seconds(30), Time.seconds(15))) \
            .reduce(HealthMetricsAggregator())
        
        # 输出到控制台（生产环境可改为Kafka/Elasticsearch/DB）
        alert_stream.print()
        aggregated_stream.print()
        
        # 执行作业
        stream_env.execute("ZhiHealth_Flink_DataStream_Pipeline")


def main():
    """启动Flink处理引擎"""
    processor = FlinkHealthStreamProcessor(
        app_name="ZhiHealthRealtimeEngine",
        kafka_servers="localhost:9092"
    )
    
    try:
        logger.info("="*70)
        logger.info("  ZhiHealth Apache Flink 实时处理引擎启动")
        logger.info("="*70)
        
        stream_env = processor.create_stream_environment()
        
        # 可选择使用SQL或DataStream API
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--sql":
            processor.run_flink_sql_pipeline(stream_env)
        else:
            processor.run_datastream_api_pipeline(stream_env)
            
    except KeyboardInterrupt:
        logger.info("Flink job stopped by user")
    except Exception as e:
        logger.error(f"Flink execution error: {e}", exc_info=True)

if __name__ == "__main__":
    main()