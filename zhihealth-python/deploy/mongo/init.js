// ZhiHealth MongoDB 初始化脚本
db = db.getSiblingDB('zhihealth');

// 创建集合和索引

db.createCollection('health_data_raw');
db.health_data_raw.createIndex({ "user_id": 1, "timestamp": -1 });
db.health_data_raw.createIndex({ "data_type": 1, "timestamp": -1 });
db.health_data_raw.createIndex({ "device_id": 1 });

db.createCollection('user_profiles');
db.user_profiles.createIndex({ "user_id": 1 }, { unique: true });

db.createCollection('device_metadata');
db.device_metadata.createIndex({ "device_code": 1 }, { unique: true });
db.device_metadata.createIndex({ "user_id": 1 });

db.createCollection('ai_model_results');
db.ai_model_results.createIndex({ "report_id": 1 }, { unique: true });
db.ai_model_results.createIndex({ "user_id": 1, "create_time": -1 });

db.createCollection('alert_events');
db.alert_events.createIndex({ "alert_id": 1 }, { unique: true });
db.alert_events.createIndex({ "user_id": 1, "severity": -1 });
db.alert_events.createIndex({ "status": 1, "create_time": -1 });

// 插入示例用户画像数据
db.user_profiles.insertMany([
    {
        user_id: 1001,
        age: 35,
        gender: "M",
        health_status: "healthy",
        risk_factors: [],
        created_at: new Date()
    },
    {
        user_id: 1002,
        age: 58,
        gender: "F",
        health_status: "mild_conditions",
        risk_factors: ["hypertension", "high_cholesterol"],
        created_at: new Date()
    }
]);

print("✅ MongoDB 初始化完成！");
print("已创建集合:", db.getCollectionNames());