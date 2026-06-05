// MongoDB 初始化脚本：创建集合和索引
db = db.getSiblingDB('zhihealth_docs');

// 健康档案集合
db.createCollection('health_archive');
db.health_archive.createIndex({ user_id: 1, created_at: -1 });
db.health_archive.createIndex({ report_type: 1 });

// AI分析报告集合
db.createCollection('ai_report');
db.ai_report.createIndex({ user_id: 1, analysis_type: 1 });
db.ai_report.createIndex({ created_at: -1 });

// 预警日志集合
db.createCollection('alert_log');
db.alert_log.createIndex({ user_id: 1, alert_time: -1 });
db.alert_log.createIndex({ level: 1, status: 1 });

print('MongoDB初始化完成: health_archive, ai_report, alert_log');
