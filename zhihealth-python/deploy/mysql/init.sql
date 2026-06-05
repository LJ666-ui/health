-- ZhiHealth MySQL 初始化脚本
-- 自动创建数据库、表结构和初始数据

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

USE zhihealth;

-- ============== 用户表 ==============
CREATE TABLE IF NOT EXISTS `user` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    `username` VARCHAR(50) NOT NULL COMMENT '用户名',
    `password` VARCHAR(255) NOT NULL COMMENT '密码(加密)',
    `real_name` VARCHAR(50) DEFAULT NULL COMMENT '真实姓名',
    `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    `avatar` VARCHAR(500) DEFAULT NULL COMMENT '头像URL',
    `gender` TINYINT DEFAULT 0 COMMENT '性别 0未知 1男 2女',
    `birthday` DATE DEFAULT NULL COMMENT '生日',
    `status` TINYINT DEFAULT 1 COMMENT '状态 0禁用 1正常',
    `role_id` INT DEFAULT 2 COMMENT '角色ID 1管理员 2普通用户',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    KEY `idx_phone` (`phone`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============== 设备表 ==============
CREATE TABLE IF NOT EXISTS `device` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '设备ID',
    `device_code` VARCHAR(64) NOT NULL COMMENT '设备编码',
    `device_name` VARCHAR(100) DEFAULT NULL COMMENT '设备名称',
    `device_type` VARCHAR(50) DEFAULT NULL COMMENT '设备类型 (smartwatch/phone/scale)',
    `user_id` BIGINT DEFAULT NULL COMMENT '所属用户ID',
    `status` TINYINT DEFAULT 1 COMMENT '状态 0离线 1在线 2故障',
    `last_online_time` DATETIME DEFAULT NULL COMMENT '最后在线时间',
    `firmware_version` VARCHAR(50) DEFAULT NULL COMMENT '固件版本',
    `battery_level` INT DEFAULT 0 COMMENT '电量百分比',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_device_code` (`device_code`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备表';

-- ============== 健康数据记录表（核心表） ==============
CREATE TABLE IF NOT EXISTS `health_record` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    `record_id` VARCHAR(64) DEFAULT NULL COMMENT '外部记录ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `device_id` BIGINT DEFAULT NULL COMMENT '设备ID',
    `data_type` VARCHAR(30) NOT NULL COMMENT '数据类型 (heart_rate/blood_pressure/body_temp/steps/sleep)',
    `heart_rate` DECIMAL(5,1) DEFAULT NULL COMMENT '心率(bpm)',
    `blood_pressure_systolic` INT DEFAULT NULL COMMENT '收缩压(mmHg)',
    `blood_pressure_diastolic` INT DEFAULT NULL COMMENT '舒张压(mmHg)',
    `body_temp` DECIMAL(4,1) DEFAULT NULL COMMENT '体温(°C)',
    `blood_oxygen` DECIMAL(4,1) DEFAULT NULL COMMENT '血氧(%)',
    `steps` INT DEFAULT NULL COMMENT '步数',
    `calories` DECIMAL(8,2) DEFAULT NULL COMMENT '消耗卡路里(kcal)',
    `distance` DECIMAL(8,2) DEFAULT NULL COMMENT '运动距离(km)',
    `sleep_hours` DECIMAL(4,1) DEFAULT NULL COMMENT '睡眠时长(h)',
    `sleep_quality` TINYINT DEFAULT NULL COMMENT '睡眠质量评分(1-5)',
    `weight` DECIMAL(5,1) DEFAULT NULL COMMENT '体重(kg)',
    `height` DECIMAL(5,1) DEFAULT NULL COMMENT '身高(cm)',
    `bmi` DECIMAL(4,1) DEFAULT NULL COMMENT 'BMI指数',
    `extra_data` JSON DEFAULT NULL COMMENT '扩展数据(JSON格式)',
    `collect_time` DATETIME NOT NULL COMMENT '采集时间',
    `processed_time` DATETIME DEFAULT NULL COMMENT '处理时间',
    `data_source` VARCHAR(20) DEFAULT 'manual' COMMENT '数据来源 manual/device/api/import',
    `quality_score` INT DEFAULT 100 COMMENT '数据质量分数(0-100)',
    `is_abnormal` TINYINT DEFAULT 0 COMMENT '是否异常 0正常 1异常',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_record_id` (`record_id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_device_id` (`device_id`),
    KEY `idx_data_type` (`data_type`),
    KEY `idx_collect_time` (`collect_time`),
    KEY `idx_user_collect` (`user_id`, `collect_time`),
    KEY `idx_data_type_collect` (`data_type`, `collect_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='健康数据记录表';

-- ============== 告警规则表 ==============
CREATE TABLE IF NOT EXISTS `alert_rule` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `rule_name` VARCHAR(100) NOT NULL COMMENT '规则名称',
    `rule_code` VARCHAR(64) NOT NULL COMMENT '规则编码',
    `metric` VARCHAR(50) NOT NULL COMMENT '监控指标',
    `condition_operator` VARCHAR(10) NOT NULL COMMENT '条件操作符 (> < >= <= == !=)',
    `condition_value` DECIMAL(10,2) NOT NULL COMMENT '阈值',
    `severity` TINYINT DEFAULT 2 COMMENT '严重级别 1info 2warning 3critical 4emergency',
    `cooldown_seconds` INT DEFAULT 300 COMMENT '冷却时间(秒)',
    `enabled` TINYINT DEFAULT 1 COMMENT '是否启用',
    `notify_channels` VARCHAR(200) DEFAULT 'in_app' COMMENT '通知渠道(逗号分隔)',
    `description` TEXT DEFAULT NULL COMMENT '规则描述',
    `creator_id` BIGINT DEFAULT NULL COMMENT '创建人',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_rule_code` (`rule_code`),
    KEY `idx_metric` (`metric`),
    KEY `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警规则表';

-- ============== 告警记录表 ==============
CREATE TABLE IF NOT EXISTS `alert_record` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `alert_id` VARCHAR(64) NOT NULL COMMENT '告警唯一ID',
    `rule_id` BIGINT NOT NULL COMMENT '规则ID',
    `user_id` BIGINT NOT NULL COMMENT '关联用户ID',
    `severity` TINYINT DEFAULT 2 COMMENT '严重级别',
    `title` VARCHAR(200) NOT NULL COMMENT '告警标题',
    `message` TEXT DEFAULT NULL COMMENT '告警内容',
    `trigger_value` DECIMAL(10,2) DEFAULT NULL COMMENT '触发值',
    `status` TINYINT DEFAULT 0 COMMENT '状态 0pending 1sent 2delivered 3failed 4acknowledged',
    `sent_channels` VARCHAR(500) DEFAULT NULL COMMENT '已发送渠道',
    `acknowledged_by` BIGINT DEFAULT NULL COMMENT '确认人',
    `acknowledged_at` DATETIME DEFAULT NULL COMMENT '确认时间',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_alert_id` (`alert_id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_rule_id` (`rule_id`),
    KEY `idx_severity` (`severity`),
    KEY `idx_status` (`status`),
    KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警记录表';

-- ============== AI分析报告表 ==============
CREATE TABLE IF NOT EXISTS `ai_analysis_report` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `report_id` VARCHAR(64) NOT NULL COMMENT '报告ID',
    `user_id` BIGINT DEFAULT NULL COMMENT '用户ID',
    `analysis_type` VARCHAR(50) NOT NULL COMMENT '分析类型 (comprehensive/predict/trend/segment)',
    `model_version` VARCHAR(20) DEFAULT NULL COMMENT '模型版本',
    `input_records_count` INT DEFAULT 0 COMMENT '输入记录数',
    `result_summary` JSON DEFAULT NULL COMMENT '结果摘要',
    `risk_assessment` JSON DEFAULT NULL COMMENT '风险评估',
    `recommendations` JSON DEFAULT NULL COMMENT '建议列表',
    `report_file_path` VARCHAR(500) DEFAULT NULL COMMENT '报告文件路径',
    `processing_time_ms` INT DEFAULT 0 COMMENT '处理耗时(ms)',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_report_id` (`report_id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_analysis_type` (`analysis_type`),
    KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI分析报告表';

-- ============== 系统配置表 ==============
CREATE TABLE IF NOT EXISTS `sys_config` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `config_key` VARCHAR(100) NOT NULL COMMENT '配置键',
    `config_value` TEXT DEFAULT NULL COMMENT '配置值',
    `config_type` VARCHAR(20) DEFAULT 'string' COMMENT '值类型 string/int/bool/json',
    `description` VARCHAR(500) DEFAULT NULL COMMENT '描述',
    `is_system` TINYINT DEFAULT 0 COMMENT '是否系统内置 0否 1是',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- ============== 操作日志表 ==============
CREATE TABLE IF NOT EXISTS `operation_log` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `operator_id` BIGINT DEFAULT NULL COMMENT '操作人ID',
    `operation_type` VARCHAR(50) NOT NULL COMMENT '操作类型',
    `module` VARCHAR(50) DEFAULT NULL COMMENT '模块',
    `target_id` VARCHAR(64) DEFAULT NULL COMMENT '目标对象ID',
    `content` TEXT DEFAULT NULL COMMENT '操作内容',
    `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
    `user_agent` VARCHAR(500) DEFAULT NULL COMMENT '浏览器UA',
    `request_url` VARCHAR(500) DEFAULT NULL COMMENT '请求URL',
    `request_method` VARCHAR(10) DEFAULT NULL COMMENT '请求方法',
    `request_params` TEXT DEFAULT NULL COMMENT '请求参数',
    `response_time_ms` INT DEFAULT 0 COMMENT '响应耗时(ms)',
    `status` TINYINT DEFAULT 1 COMMENT '执行状态 0失败 1成功',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_operator_id` (`operator_id`),
    KEY `idx_operation_type` (`operation_type`),
    KEY `idx_module` (`module`),
    KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';

-- ============== 插入初始数据 ==============

INSERT IGNORE INTO `user` (`id`, `username`, `password`, `real_name`, `phone`, `email`, `gender`, `status`, `role_id`) VALUES
(1, 'admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EH', '系统管理员', '13800000001', 'admin@zhihealth.com', 1, 1, 1),
(2, 'test_user', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EH', '测试用户', '13800000002', 'test@zhihealth.com', 1, 1, 2);

INSERT IGNORE INTO `sys_config` (`config_key`, `config_value`, `config_type`, `description`, `is_system`) VALUES
('system.name', 'ZhiHealth 智慧健康大数据平台', 'string', '系统名称', 1),
('system.version', '2.0.0', 'string', '系统版本', 1),
('etl.batch_size', '1000', 'int', 'ETL批处理大小', 1),
('ai.model_path', '/app/ai/models', 'string', 'AI模型存储路径', 1),
('alert.cooldown_default', '300', 'int', '默认告警冷却时间(秒)', 1),
('visualization.refresh_interval', '3', 'int', '大屏刷新间隔(秒)', 1),
('api.rate_limit', '1000', 'int', 'API每分钟请求限制', 1);

INSERT IGNORE INTO `alert_rule` (`rule_name`, `rule_code`, `metric`, `condition_operator`, `condition_value`, `severity`, `cooldown_seconds`, `enabled`, `notify_channels`, `description`) VALUES
('心率过高', 'hr_high', 'heart_rate', '>', 120.00, 2, 300, 1, 'email,in_app,webhook', '检测到心率超过120 bpm，可能存在心动过速风险'),
('心率过低', 'hr_low', 'heart_rate', '<', 50.00, 2, 300, 1, 'email,in_app', '检测到心率低于50 bpm，可能存在心动过缓风险'),
('高血压危象', 'bp_crisis', 'blood_pressure_systolic', '>', 180.00, 3, 600, 1, 'email,sms,in_app,webhook', '收缩压超过180mmHg或舒张压超过120mmHg，需立即就医'),
('体温异常升高', 'temp_high', 'body_temp', '>', 39.50, 3, 3600, 1, 'email,sms,in_app', '体温超过39.5°C，可能存在发热症状'),
('严重睡眠不足', 'sleep_deficit', 'sleep_hours', '<', 5.00, 1, 86400, 1, 'in_app,email', '连续多日睡眠不足5小时'),
('活动量骤降', 'activity_low', 'steps', '<', 1500.00, 1, 172800, 1, 'in_app,email', '活动量较平均值下降超过70%');

SET FOREIGN_KEY_CHECKS = 1;

SELECT '✅ ZhiHealth 数据库初始化完成！' AS message;
SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'zhihealth';