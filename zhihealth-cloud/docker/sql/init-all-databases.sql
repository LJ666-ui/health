-- 批量初始化所有业务数据库表结构
-- 在每个业务库中执行init.sql

-- 1. 设备服务库
USE zhihealth_device;
SOURCE /tmp/init.sql;
SELECT 'zhihealth_device initialized' as status;

-- 2. 数据采集库
USE zhihealth_collect;
SOURCE /tmp/init.sql;
SELECT 'zhihealth_collect initialized' as status;

-- 3. 预警服务库
USE zhihealth_alert;
SOURCE /tmp/init.sql;
SELECT 'zhihealth_alert initialized' as status;

-- 4. 存储服务库
USE zhihealth_storage;
SOURCE /tmp/init.sql;
SELECT 'zhihealth_storage initialized' as status;

-- 5. 日志服务库
USE zhihealth_log;
SOURCE /tmp/init.sql;
SELECT 'zhihealth_log initialized' as status;

-- 6. 报告服务库
USE zhihealth_report;
SOURCE /tmp/init.sql;
SELECT 'zhihealth_report initialized' as status;
