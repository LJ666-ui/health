"""
ZhiHealth Spark Streaming 实时健康数据处理引擎
支持实时数据采集、窗口聚合、异常检测、预警推送
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

class HealthDataStreamingProcessor:
    def __init__(self, app_name: str = "ZhiHealthRealtimeEngine", 
                 batch_interval: int = 10,
                 kafka_servers: str = "localhost:9092"):
        self.app_name = app_name
        self.batch_interval = batch_interval
        self.kafka_servers = kafka_servers
        self.spark = None
        self.ssc = None
        
    def create_spark_session(self) -> SparkSession:
        """创建Spark会话"""
        self.spark = SparkSession.builder \
            .appName(self.app_name) \
            .config("spark.sql.shuffle.partitions", "8") \
            .config("spark.streaming.kafka.maxRatePerPartition", "1000") \
            .config("spark.streaming.stopGracefullyOnShutdown", "true") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .getOrCreate()
            
        self.spark.sparkContext.setLogLevel("WARN")
        logger.info(f"Spark Session created: {app_name}")
        return self.spark
    
    def define_health_data_schema(self) -> StructType:
        """定义健康数据Schema"""
        return StructType([
            StructField("record_id", LongType(), nullable=False),
            StructField("user_id", LongType(), nullable=False),
            StructField("device_id", LongType(), nullable=False),
            StructField("data_type", StringType(), nullable=False),
            StructField("heart_rate", DoubleType(), nullable=True),
            StructField("body_temp", DoubleType(), nullable=True),
            StructField("blood_pressure_systolic", IntegerType(), nullable=True),
            StructField("blood_pressure_diastolic", IntegerType(), nullable=True),
            StructField("steps", IntegerType(), nullable=True),
            StructField("sleep_hours", DoubleType(), nullable=True),
            StructField("timestamp", LongType(), nullable=False)
        ])
    
    def process_kafka_stream(self, topic: str = "health_data_raw") -> None:
        """从Kafka消费并处理实时健康数据流"""
        if not self.spark:
            self.create_spark_session()
            
        df = self.spark \
          .readStream \
          .format("kafka") \
          .option("kafka.bootstrap.servers", self.kafka_servers) \
          .option("subscribe", topic) \
          .option("startingOffsets", "latest") \
          .option("maxOffsetsPerTrigger", "10000") \
          .load()
        
        value_df = df.select(
            from_json(col("value").cast("string"), 
                     self.define_health_data_schema()).alias("data")
        ).select("data.*")
        
        logger.info(f"Started streaming from Kafka topic: {topic}")
        
        # 实时数据清洗与转换
        cleaned_stream = self._clean_realtime_data(value_df)
        
        # 窗口聚合计算
        windowed_aggregates = self._compute_windowed_aggregates(cleaned_stream)
        
        # 异常检测
        anomaly_stream = self._detect_anomalies_realtime(cleaned_stream)
        
        # 写入多个输出目标
        query1 = cleaned_stream.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", "false") \
            .start()
            
        query2 = windowed_aggregates.writeStream \
            .outputMode("complete") \
            .format("memory") \
            .queryName("health_metrics_windowed") \
            .start()
            
        query3 = anomaly_stream.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", "false") \
            .start()
        
        logger.info("All streaming queries started successfully")
        
        self.spark.streams.awaitAnyTermination()
    
    def _clean_realtime_data(self, stream_df):
        """实时数据清洗"""
        cleaned = stream_df \
            .filter(col("user_id").isNotNull()) \
            .filter(col("device_id").isNotNull()) \
            .filter(col("timestamp").isNotNull()) \
            .withColumn("event_time", to_timestamp(col("timestamp") / 1000)) \
            .withColumn("processing_time", current_timestamp()) \
            .withColumn("data_quality_score",
                when(col("heart_rate").between(40, 200), 100)
                .when(col("heart_rate").isNotNull(), 50)
                .otherwise(lit(None))
            ) \
            .withColumn("is_valid",
                col("user_id").isNotNull() & 
                col("device_id").isNotNull() & 
                (col("data_quality_score") > 0)
            )
            
        return cleaned.filter(col("is_valid"))
    
    def _compute_windowed_aggregates(self, stream_df):
        """滑动窗口聚合计算（每10秒窗口，5秒滑动）"""
        windowed_agg = stream_df \
            .groupBy(
                window(col("event_time"), "10 seconds", "5 seconds"),
                col("user_id"),
                col("data_type")
            ) \
            .agg(
                count("*").alias("record_count"),
                avg("heart_rate").alias("avg_heart_rate"),
                max("heart_rate").alias("max_heart_rate"),
                min("heart_rate").alias("min_heart_rate"),
                avg("blood_pressure_systolic").alias("avg_sys"),
                avg("blood_pressure_diastolic").alias("avg_dia"),
                sum("steps").alias("total_steps"),
                avg("sleep_hours").alias("avg_sleep"),
                collect_list("device_id").alias("devices_used")
            ) \
            .select(
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("user_id"),
                col("data_type"),
                col("record_count"),
                round(col("avg_heart_rate"), 2).alias("avg_hr"),
                col("max_heart_rate"),
                col("min_heart_rate"),
                round(col("avg_sys"), 0).alias("avg_bp_sys"),
                round(col("avg_dia"), 0).alias("avg_bp_dia"),
                col("total_steps"),
                round(col("avg_sleep"), 2).alias("avg_slp_hrs"),
                size(col("devices_used")).alias("device_count")
            )
            
        return windowed_agg
    
    def _detect_anomalies_realtime(self, stream_df):
        """实时异常检测"""
        anomalies = stream_df \
            .filter(
                (col("heart_rate") < 50) | (col("heart_rate") > 120) |
                (col("blood_pressure_systolic") > 180) | (col("blood_pressure_diastolic") > 120) |
                (col("body_temp") < 35.0) | (col("body_temp") > 41.0)
            ) \
            .withColumn("anomaly_type",
                when(col("heart_rate") < 50, "bradycardia")
                .when(col("heart_rate") > 120, "tachycardia")
                .when(col("blood_pressure_systolic") > 180, "hypertensive_crisis")
                .when(col("blood_pressure_diastolic") > 120, "hypertensive_crisis")
                .when(col("body_temp") < 35.0, "hypothermia")
                .when(col("body_temp") > 41.0, "hyperthermia")
                .otherwise("unknown_anomaly")
            ) \
            .withColumn("severity",
                when(col("anomaly_type").isin(["hypertensive_crisis", "hyperthermia"]), "critical")
                .when(col("anomaly_type").isin(["tachycardia", "hypothermia"]), "high")
                .otherwise("medium")
            ) \
            .withColumn("alert_timestamp", current_timestamp()) \
            .select(
                col("user_id"),
                col("device_id"),
                col("data_type"),
                col("anomaly_type"),
                col("severity"),
                col("heart_rate"),
                col("blood_pressure_systolic").alias("bp_sys"),
                col("blood_pressure_diastolic").alias("bp_dia"),
                col("body_temp"),
                col("event_time"),
                col("alert_timestamp")
            )
            
        return anomalies


class SparkBatchAnalyzer:
    """Spark批量分析器（用于离线深度分析）"""
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        
    def analyze_user_health_patterns(self, data_path: str) -> DataFrame:
        """用户健康模式分析"""
        schema = HealthDataStreamingProcessor().define_health_data_schema()
        
        df = self.spark.read.schema(schema).parquet(data_path)
        
        analysis = df.groupBy("user_id") \
            .agg(
                count("*").alias("total_records"),
                countDistinct("device_id").alias("unique_devices"),
                avg("heart_rate").alias("avg_hr"),
                stddev("heart_rate").alias("hr_stddev"),
                avg("blood_pressure_systolic").alias("avg_bp_sys"),
                avg("blood_pressure_diastolic").alias("avg_bp_dia"),
                sum("steps").alias("total_steps"),
                avg("sleep_hours").alias("avg_sleep"),
                min("timestamp").alias("first_record"),
                max("timestamp").alias("last_record")
            ) \
            .withColumn("active_days", 
                datediff(to_timestamp(col("last_record") / 1000), 
                        to_timestamp(col("first_record") / 1000))
            ) \
            .withColumn("daily_avg_steps", 
                round(col("total_steps") / greatest(col("active_days"), lit(1)), 2)
            ) \
            .withColumn("hr_variability", 
                round(col("hr_stddev"), 2)
            )
            
        return analysis
    
    def detect_health_risk_groups(self, data_path: str) -> DataFrame:
        """高风险人群识别"""
        patterns = self.analyze_user_health_patterns(data_path)
        
        risk_groups = patterns.withColumn("risk_score",
            when(col("avg_bp_sys") > 140, 40)
            .when(col("avg_bp_sys") > 130, 25)
            .when(col("avg_bp_sys") > 120, 15)
            .otherwise(0) +
            when(col("hr_variability") > 30, 20)
            .when(col("hr_variability") > 20, 10)
            .otherwise(0) +
            when(col("daily_avg_steps") < 3000, 25)
            .when(col("daily_avg_steps") < 5000, 15)
            .when(col("daily_avg_steps") < 8000, 5)
            .otherwise(0) +
            when(col("avg_sleep") < 5.5, 15)
            .when(col("avg_sleep") < 6.5, 8)
            .otherwise(0)
        ) \
        .withColumn("risk_category",
            when(col("risk_score") >= 70, "critical")
            .when(col("risk_score") >= 50, "high")
            .when(col("risk_score") >= 30, "moderate")
            .when(col("risk_score") >= 15, "low")
            .otherwise("normal")
        )
        
        return risk_groups.filter(col("risk_category") != "normal")


def main():
    """启动Spark Streaming处理"""
    processor = HealthDataStreamingProcessor(
        app_name="ZhiHealthRealtimeAnalytics",
        batch_interval=10
    )
    
    try:
        logger.info("="*70)
        logger.info("  ZhiHealth Spark Streaming 实时处理引擎启动")
        logger.info("="*70)
        
        processor.process_kafka_stream(topic="health_data_raw")
        
    except KeyboardInterrupt:
        logger.info("Streaming stopped by user")
    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)

if __name__ == "__main__":
    main()