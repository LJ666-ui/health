# MongoDB初始化脚本（创建用户和集合）
db = db.getSiblingDB('zhihealth_storage');

// 创建存储用户
db.createUser({
  user: 'zhihealth_app',
  pwd: 'ZhiHealth_Mongo_2024',
  roles: [
    { role: 'readWrite', db: 'zhihealth_storage' }
  ]
});

// 创建健康数据集合
db.createCollection('health_records');
db.health_records.createIndex({ "userId": 1, "timestamp": -1 });
db.health_records.createIndex({ "deviceId": 1 });

// 创建设备数据集合
db.createCollection('device_data');
db.device_data.createIndex({ "deviceId": 1, "timestamp": -1 });

print('✅ MongoDB初始化完成');
