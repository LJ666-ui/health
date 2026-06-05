"""
ZhiHealth 实时健康数据模拟生成器
用于测试Spark/Flink流处理管道
支持多用户、多设备、多种数据类型的模拟
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from kafka import KafkaProducer
from loguru import logger
import threading
import sys


class HealthDataSimulator:
    """健康数据模拟器"""
    
    def __init__(self, 
                 num_users: int = 10,
                 num_devices: int = 20,
                 data_types: List[str] = None,
                 anomaly_rate: float = 0.05):
        self.num_users = num_users
        self.num_devices = num_devices
        self.data_types = data_types or ['heart_rate', 'body_temp', 'blood_pressure', 'steps', 'sleep']
        self.anomaly_rate = anomaly_rate
        
        # 用户基础信息（用于生成更真实的数据）
        self.user_profiles = self._generate_user_profiles()
        
        # 记录ID计数器
        self.record_id_counter = 0
        
    def _generate_user_profiles(self) -> Dict:
        """生成用户画像（影响数据分布）"""
        profiles = {}
        for user_id in range(1, self.num_users + 1):
            age = random.randint(18, 75)
            gender = random.choice(['M', 'F'])
            
            profiles[user_id] = {
                'age': age,
                'gender': gender,
                'base_heart_rate': random.randint(65, 85),
                'base_bp_sys': random.randint(110, 140) if age > 50 else random.randint(105, 125),
                'base_bp_dia': random.randint(70, 90),
                'activity_level': random.choice(['low', 'moderate', 'high', 'very_high']),
                'sleep_pattern': random.choice(['normal', 'light_sleeper', 'heavy_sleeper', 'irregular']),
                'health_status': random.choices(
                    ['healthy', 'mild_conditions', 'chronic_issues'],
                    weights=[0.6, 0.3, 0.1]
                )[0]
            }
            
        return profiles
    
    def generate_single_record(self, user_id: int = None, 
                              device_id: int = None,
                              data_type: str = None,
                              timestamp: int = None) -> Dict:
        """生成单条健康记录"""
        user_id = user_id or random.randint(1, self.num_users)
        device_id = device_id or random.randint(101, 100 + self.num_devices)
        data_type = data_type or random.choice(self.data_types)
        timestamp = timestamp or int(datetime.now().timestamp() * 1000)
        
        profile = self.user_profiles.get(user_id, {})
        
        record = {
            'record_id': self.record_id_counter,
            'user_id': user_id,
            'device_id': device_id,
            'data_type': data_type,
            'timestamp': timestamp
        }
        
        self.record_id_counter += 1
        
        # 根据数据类型和用户画像生成数值
        if data_type == 'heart_rate':
            base_hr = profile.get('base_heart_rate', 72)
            hr = self._generate_with_variation(base_hr, std=8)
            
            if random.random() < self.anomaly_rate:
                hr = random.choice([
                    random.randint(40, 50),   # 心动过缓
                    random.randint(130, 160), # 心动过速
                ])
                
            record['heart_rate'] = round(hr, 2)
            
        elif data_type == 'body_temp':
            base_temp = 36.5
            temp = self._generate_with_variation(base_temp, std=0.3)
            
            if random.random() < self.anomaly_rate * 0.5:  # 体温异常较少
                temp = random.choice([34.8, 35.2, 39.2, 40.1])
                
            record['body_temp'] = round(temp, 2)
            
        elif data_type == 'blood_pressure':
            base_sys = profile.get('base_bp_sys', 120)
            base_dia = profile.get('base_bp_dia', 80)
            
            sys_val = int(self._generate_with_variation(base_sys, std=12))
            dia_val = int(self._generate_with_variation(base_dia, std=8))
            
            # 确保收缩压 > 舒张压
            dia_val = min(dia_val, sys_val - 20)
            
            if random.random() < self.anomaly_rate:
                severity = random.random()
                if severity > 0.7:  # 高血压危象
                    sys_val = random.randint(185, 220)
                    dia_val = random.randint(120, 145)
                elif severity > 0.4:  # 高血压
                    sys_val = random.randint(150, 179)
                    dia_val = random.randint(95, 115)
                    
            record['blood_pressure_systolic'] = sys_val
            record['blood_pressure_diastolic'] = dia_val
            
        elif data_type == 'steps':
            activity_map = {
                'low': (2000, 5000),
                'moderate': (5000, 10000),
                'high': (10000, 18000),
                'very_high': (18000, 30000)
            }
            
            activity = profile.get('activity_level', 'moderate')
            steps_range = activity_map.get(activity, (5000, 10000))
            steps = random.randint(*steps_range)
            
            record['steps'] = steps
            
        elif data_type == 'sleep':
            sleep_map = {
                'normal': (6.5, 8.5),
                'light_sleeper': (5.5, 7.0),
                'heavy_sleeper': (8.0, 10.0),
                'irregular': (4.5, 9.5)
            }
            
            pattern = profile.get('sleep_pattern', 'normal')
            sleep_range = sleep_map.get(pattern, (6.5, 8.5))
            sleep_hours = round(random.uniform(*sleep_range), 2)
            
            record['sleep_hours'] = sleep_hours
            
        return record
    
    def _generate_with_variation(self, base_value: float, std: float) -> float:
        """基于基准值生成带随机波动的数据（高斯分布）"""
        return base_value + random.gauss(0, std)
    
    def generate_batch(self, batch_size: int = 100) -> List[Dict]:
        """批量生成数据"""
        records = []
        for _ in range(batch_size):
            records.append(self.generate_single_record())
        return records


class KafkaDataPublisher:
    """Kafka数据发布器"""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092",
                 topic: str = "health_data_raw"):
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: str(k).encode('utf-8'),
            acks='all',
            retries=3,
            batch_size=16384,
            linger_ms=10,
            buffer_memory=33554432
        )
        logger.info(f"Kafka producer connected to {bootstrap_servers}, topic: {topic}")
        
    def publish_records(self, records: List[Dict], interval_ms: float = 100) -> int:
        """发布记录到Kafka"""
        success_count = 0
        
        for record in records:
            try:
                future = self.producer.send(
                    topic=self.topic,
                    key=record.get('user_id'),
                    value=record
                )
                
                result = future.get(timeout=10)
                success_count += 1
                
                time.sleep(interval_ms / 1000.0)  # 模拟实时数据间隔
                
            except Exception as e:
                logger.error(f"Failed to publish record {record.get('record_id')}: {e}")
                
        logger.info(f"Published {success_count}/{len(records)} records to Kafka")
        return success_count
    
    def publish_continuous_stream(self, simulator: HealthDataSimulator,
                                  records_per_second: int = 10,
                                  duration_seconds: int = 60) -> None:
        """持续发布数据流"""
        interval = 1.0 / records_per_second
        end_time = time.time() + duration_seconds
        published_count = 0
        
        logger.info(f"Starting continuous stream: {records_per_second} rec/s for {duration_seconds}s")
        
        try:
            while time.time() < end_time:
                record = simulator.generate_single_record()
                
                try:
                    self.producer.send(
                        topic=self.topic,
                        key=record['user_id'],
                        value=record
                    )
                    published_count += 1
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    logger.warning(f"Publish error: {e}")
                    time.sleep(0.1)
                    
        finally:
            self.producer.flush()
            logger.info(f"Stream completed. Total published: {published_count} records")
            
    def close(self):
        """关闭生产者"""
        self.producer.flush()
        self.producer.close()
        logger.info("Kafka producer closed")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ZhiHealth Real-time Data Simulator')
    parser.add_argument('--users', type=int, default=10, help='Number of users to simulate')
    parser.add_argument('--devices', type=int, default=20, help='Number of devices')
    parser.add_argument('--anomaly-rate', type=float, default=0.05, help='Anomaly rate (0-1)')
    parser.add_argument('--kafka-servers', default='localhost:9092', help='Kafka bootstrap servers')
    parser.add_argument('--topic', default='health_data_raw', help='Kafka topic')
    parser.add_argument('--mode', choices=['batch', 'continuous'], default='batch', help='Publishing mode')
    parser.add_argument('--batch-size', type=int, default=500, help='Batch size (for batch mode)')
    parser.add_argument('--rate', type=int, default=10, help='Records per second (for continuous mode)')
    parser.add_argument('--duration', type=int, default=60, help='Duration in seconds (for continuous mode)')
    parser.add_argument('--output-file', help='Output to JSON file instead of Kafka')
    
    args = parser.parse_args()
    
    logger.info("="*70)
    logger.info("  ZhiHealth 实时健康数据模拟器")
    logger.info(f"  用户数: {args.users} | 设备数: {args.devices} | 异常率: {args.anomaly_rate*100}%")
    logger.info("="*70)
    
    simulator = HealthDataSimulator(
        num_users=args.users,
        num_devices=args.devices,
        anomaly_rate=args.anomaly_rate
    )
    
    if args.output_file:
        # 输出到文件模式
        records = simulator.generate_batch(args.batch_size * 10)
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        logger.info(f"Generated {len(records)} records to {args.output_file}")
        
    elif args.mode == 'batch':
        # 批量模式
        publisher = KafkaDataPublisher(
            bootstrap_servers=args.kafka_servers,
            topic=args.topic
        )
        
        try:
            records = simulator.generate_batch(args.batch_size)
            publisher.publish_records(records, interval_ms=50)
        finally:
            publisher.close()
            
    elif args.mode == 'continuous':
        # 连续流模式
        publisher = KafkaDataPublisher(
            bootstrap_servers=args.kafka_servers,
            topic=args.topic
        )
        
        try:
            publisher.publish_continuous_stream(
                simulator=simulator,
                records_per_second=args.rate,
                duration_seconds=args.duration
            )
        finally:
            publisher.close()


if __name__ == "__main__":
    main()