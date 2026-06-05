import pandas as pd
import pymysql
from pymongo import MongoClient
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import redis
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime
import json
import time

from config.config import mysql, redis as redis_config, mongodb, influxdb, etl as etl_config
from etl.data_cleaner import DataCleaner

class ETPipeline:
    def __init__(self):
        self.cleaner = DataCleaner()
        self.mysql_conn = None
        self.redis_client = None
        self.mongo_client = None
        self.influx_client = None
        
    def _connect_mysql(self):
        try:
            self.mysql_conn = pymysql.connect(
                host=mysql.host,
                port=mysql.port,
                user=mysql.user,
                password=mysql.password,
                database=mysql.database,
                charset=mysql.charset,
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("MySQL连接成功")
            return True
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            return False

    def _connect_redis(self):
        try:
            self.redis_client = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                password=redis_config.password,
                db=redis_config.db,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis连接成功")
            return True
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return False

    def _connect_mongodb(self):
        try:
            if mongodb.username and mongodb.password:
                uri = f"mongodb://{mongodb.username}:{mongodb.password}@{mongodb.host}:{mongodb.port}/"
            else:
                uri = f"mongodb://{mongodb.host}:{mongodb.port}/"
                
            self.mongo_client = MongoClient(uri)
            self.mongo_client.admin.command('ping')
            logger.info("MongoDB连接成功")
            return True
        except Exception as e:
            logger.error(f"MongoDB连接失败: {e}")
            return False

    def _connect_influxdb(self):
        try:
            self.influx_client = InfluxDBClient(
                url=influxdb.url,
                token=influxdb.token,
                org=influxdb.org
            )
            health = self.influx_client.health()
            logger.info(f"InfluxDB连接成功: {health.status}")
            return True
        except Exception as e:
            logger.error(f"InfluxDB连接失败: {e}")
            return False

    def connect_all(self) -> bool:
        success = True
        success &= self._connect_mysql()
        success &= self._connect_redis()
        success &= self._connect_mongodb()
        success &= self._connect_influxdb()
        return success

    def extract_from_mysql(self, table_name: str = "health_record", 
                          batch_size: int = None) -> pd.DataFrame:
        if not self.mysql_conn:
            if not self._connect_mysql():
                return pd.DataFrame()

        batch_size = batch_size or etl_config.batch_size
        query = f"SELECT * FROM {table_name} ORDER BY id LIMIT {batch_size}"
        
        try:
            with self.mysql_conn.cursor() as cursor:
                cursor.execute(query)
                data = cursor.fetchall()
                
            df = pd.DataFrame(data)
            if not df.empty:
                logger.info(f"从MySQL提取数据: {len(df)} 条记录 (表: {table_name})")
            
            return df
            
        except Exception as e:
            logger.error(f"MySQL数据提取失败: {e}")
            return pd.DataFrame()

    def transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
            
        logger.info(f"开始数据转换，输入: {len(df)} 条记录")
        
        cleaned_df = self.cleaner.clean_health_data(df)
        
        cleaned_df['processed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cleaned_df['data_source'] = 'mysql_etl'
        
        logger.info(f"数据转换完成，输出: {len(cleaned_df)} 条记录")
        return cleaned_df

    def load_to_mysql(self, df: pd.DataFrame, table_name: str = "health_record_cleaned") -> bool:
        if df.empty or not self.mysql_conn:
            return False
            
        try:
            with self.mysql_conn.cursor() as cursor:
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    device_id BIGINT NOT NULL,
                    data_type VARCHAR(50),
                    heart_rate DECIMAL(6,2),
                    body_temp DECIMAL(4,2),
                    blood_pressure_systolic INT,
                    blood_pressure_diastolic INT,
                    steps INT,
                    sleep_hours DECIMAL(4,2),
                    timestamp BIGINT,
                    processed_time DATETIME,
                    data_source VARCHAR(50),
                    INDEX idx_user_id (user_id),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_data_type (data_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
                cursor.execute(create_table_sql)
                
                for _, row in df.iterrows():
                    insert_sql = f"""
                    INSERT INTO {table_name} 
                    (user_id, device_id, data_type, heart_rate, body_temp, 
                     blood_pressure_systolic, blood_pressure_diastolic, steps, 
                     sleep_hours, timestamp, processed_time, data_source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_sql, (
                        row.get('user_id'), row.get('device_id'),
                        row.get('data_type'), row.get('heart_rate'),
                        row.get('body_temp'), row.get('blood_pressure_systolic'),
                        row.get('blood_pressure_diastolic'), row.get('steps'),
                        row.get('sleep_hours'), row.get('timestamp'),
                        row.get('processed_time'), row.get('data_source')
                    ))
                    
            self.mysql_conn.commit()
            logger.info(f"成功写入MySQL表 {table_name}: {len(df)} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"MySQL数据加载失败: {e}")
            self.mysql_conn.rollback()
            return False

    def load_to_redis(self, df: pd.DataFrame, prefix: str = "health") -> bool:
        if df.empty or not self.redis_client:
            return False
            
        try:
            pipe = self.redis_client.pipeline(transaction=False)
            
            for _, row in df.iterrows():
                user_id = row.get('user_id')
                data_type = row.get('data_type', 'unknown')
                key = f"{prefix}:{user_id}:{data_type}"
                
                data_dict = {
                    'device_id': str(row.get('device_id', '')),
                    'heart_rate': str(row.get('heart_rate', '')),
                    'body_temp': str(row.get('body_temp', '')),
                    'blood_pressure_systolic': str(row.get('blood_pressure_systolic', '')),
                    'blood_pressure_diastolic': str(row.get('blood_pressure_diastolic', '')),
                    'steps': str(row.get('steps', '')),
                    'sleep_hours': str(row.get('sleep_hours', '')),
                    'timestamp': str(row.get('timestamp', '')),
                    'processed_time': str(row.get('processed_time', ''))
                }
                
                pipe.hset(key, mapping=data_dict)
                pipe.expire(key, 86400)
                
            pipe.execute()
            logger.info(f"成功写入Redis: {len(df)} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"Redis数据加载失败: {e}")
            return False

    def load_to_mongodb(self, df: pd.DataFrame, collection_name: str = "health_records") -> bool:
        if df.empty or not self.mongo_client:
            return False
            
        try:
            db = self.mongo_client[mongodb.database]
            collection = db[collection_name]
            
            records = df.to_dict("records")
            
            for record in records:
                record['_id'] = f"{record.get('user_id')}_{record.get('timestamp')}_{record.get('data_type')}"
                
            collection.insert_many(records, ordered=False)
            logger.info(f"成功写入MongoDB集合 {collection_name}: {len(records)} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB数据加载失败: {e}")
            return False

    def load_to_influxdb(self, df: pd.DataFrame) -> bool:
        if df.empty or not self.influx_client:
            return False
            
        try:
            write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            
            points = []
            for _, row in df.iterrows():
                point = Point("health_metrics") \
                    .tag("user_id", str(row.get('user_id', 0))) \
                    .tag("device_id", str(row.get('device_id', 0))) \
                    .tag("data_type", str(row.get('data_type', 'unknown'))) \
                    .field("heart_rate", float(row.get('heart_rate', 0) or 0)) \
                    .field("body_temp", float(row.get('body_temp', 0) or 0)) \
                    .field("blood_pressure_systolic", int(row.get('blood_pressure_systolic', 0) or 0)) \
                    .field("blood_pressure_diastolic", int(row.get('blood_pressure_diastolic', 0) or 0)) \
                    .field("steps", int(row.get('steps', 0) or 0)) \
                    .field("sleep_hours", float(row.get('sleep_hours', 0) or 0)) \
                    .time(int(row.get('timestamp', 0) or 0), WritePrecision.MS)
                    
                points.append(point)
                
            write_api.write(bucket=influxdb.bucket, record=points)
            logger.info(f"成功写入InfluxDB: {len(points)} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"InfluxDB数据加载失败: {e}")
            return False

    def run_full_pipeline(self, source_table: str = "health_record") -> Dict:
        start_time = time.time()
        pipeline_stats = {
            "status": "failed",
            "extract_count": 0,
            "transform_count": 0,
            "load_success": {},
            "duration_seconds": 0,
            "cleaning_report": {}
        }
        
        logger.info("="*60)
        logger.info("开始执行完整ETL流程")
        logger.info("="*60)
        
        if not self.connect_all():
            logger.error("数据库连接失败，终止流程")
            return pipeline_stats
        
        raw_data = self.extract_from_mysql(source_table)
        pipeline_stats["extract_count"] = len(raw_data)
        
        if raw_data.empty:
            logger.warning("未提取到原始数据")
            pipeline_stats["status"] = "completed_empty"
            return pipeline_stats
        
        transformed_data = self.transform_data(raw_data)
        pipeline_stats["transform_count"] = len(transformed_data)
        pipeline_stats["cleaning_report"] = self.cleaner.get_cleaning_report()
        
        load_targets = {
            "mysql": lambda: self.load_to_mysql(transformed_data),
            "redis": lambda: self.load_to_redis(transformed_data),
            "mongodb": lambda: self.load_to_mongodb(transformed_data),
            "influxdb": lambda: self.load_to_influxdb(transformed_data)
        }
        
        for target, loader in load_targets.items():
            try:
                success = loader()
                pipeline_stats["load_success"][target] = success
            except Exception as e:
                logger.error(f"{target} 加载异常: {e}")
                pipeline_stats["load_success"][target] = False
        
        end_time = time.time()
        pipeline_stats["duration_seconds"] = round(end_time - start_time, 2)
        pipeline_stats["status"] = "success"
        
        logger.info("="*60)
        logger.info(f"ETL流程完成! 耗时: {pipeline_stats['duration_seconds']}秒")
        logger.info(f"统计: 提取={pipeline_stats['extract_count']}, 转换={pipeline_stats['transform_count']}")
        logger.info(f"加载结果: {pipeline_stats['load_success']}")
        logger.info("="*60)
        
        return pipeline_stats

    def close_connections(self):
        if self.mysql_conn:
            self.mysql_conn.close()
            logger.info("MySQL连接已关闭")
            
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis连接已关闭")
            
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB连接已关闭")
            
        if self.influx_client:
            self.influx_client.close()
            logger.info("InfluxDB连接已关闭")