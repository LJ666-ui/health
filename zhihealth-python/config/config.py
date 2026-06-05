import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class MySQLConfig:
    host: str = "localhost"
    port: int = 3307
    user: str = "root"
    password: str = "root_2024_zhihealth"
    database: str = "zhihealth"
    charset: str = "utf8mb4"

@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0

@dataclass
class MongoDBConfig:
    host: str = "localhost"
    port: int = 27017
    database: str = "zhihealth_docs"
    username: Optional[str] = "admin"
    password: Optional[str] = "mongo_2024"

@dataclass
class InfluxDBConfig:
    url: str = "http://localhost:8086"
    token: str = "zhihealth-token"
    org: str = "zhihealth"
    bucket: str = "health_data"

@dataclass
class ETLConfig:
    batch_size: int = 1000
    max_retries: int = 3
    retry_delay: float = 1.0
    log_level: str = "INFO"

mysql = MySQLConfig()
redis = RedisConfig()
mongodb = MongoDBConfig()
influxdb = InfluxDBConfig()
etl = ETLConfig()

DATA_TYPES = ["heart_rate", "body_temp", "blood_pressure", "steps", "sleep"]
VALID_DATA_RANGES = {
    "heart_rate": (40, 200),
    "body_temp": (35.0, 42.0),
    "blood_pressure_systolic": (70, 250),
    "blood_pressure_diastolic": (40, 150),
    "steps": (0, 100000),
    "sleep_hours": (0, 24)
}