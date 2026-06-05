-- ============================================================
--  智康云枢 数据库初始化脚本
--  版本: v1.0
--  数据库: zhihealth (MySQL 8.0)
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ==================== 用户权限模块 ====================

-- 系统用户表
CREATE TABLE IF NOT EXISTS `sys_user` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `username`    VARCHAR(50)  NOT NULL COMMENT '用户名',
    `password`    VARCHAR(200) NOT NULL COMMENT '密码(BCrypt)',
    `real_name`   VARCHAR(50)  DEFAULT '' COMMENT '真实姓名',
    `phone`       VARCHAR(20)  DEFAULT '' COMMENT '手机号',
    `email`       VARCHAR(100) DEFAULT '' COMMENT '邮箱',
    `avatar`      VARCHAR(255) DEFAULT '' COMMENT '头像URL',
    `gender`      TINYINT      DEFAULT 0 COMMENT '性别:0未知 1男 2女',
    `birthday`    DATE         DEFAULT NULL COMMENT '出生日期',
    `status`      TINYINT      DEFAULT 1 COMMENT '状态:0禁用 1正常',
    `role_id`     BIGINT       DEFAULT NULL COMMENT '角色ID',
    `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    KEY `idx_phone` (`phone`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';

-- 角色表
CREATE TABLE IF NOT EXISTS `sys_role` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT,
    `role_name`   VARCHAR(50)  NOT NULL COMMENT '角色名称',
    `role_code`   VARCHAR(50)  NOT NULL COMMENT '角色编码',
    `description` VARCHAR(255) DEFAULT '' COMMENT '描述',
    `status`      TINYINT      DEFAULT 1 COMMENT '状态',
    `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- 权限/菜单表
CREATE TABLE IF NOT EXISTS `sys_menu` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT,
    `parent_id`   BIGINT       DEFAULT 0 COMMENT '父菜单ID',
    `menu_name`   VARCHAR(50)  NOT NULL COMMENT '菜单名称',
    `menu_type`   CHAR(1)      DEFAULT 'M' COMMENT '类型:M目录 C菜单 F按钮',
    `path`        VARCHAR(200) DEFAULT '' COMMENT '路由路径',
    `component`   VARCHAR(255) DEFAULT '' COMMENT '组件路径',
    `perms`       VARCHAR(100) DEFAULT '' COMMENT '权限标识',
    `icon`        VARCHAR(100) DEFAULT '' COMMENT '图标',
    `sort_order`  INT          DEFAULT 0 COMMENT '排序',
    `status`      TINYINT      DEFAULT 1,
    `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_parent` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='菜单权限表';

-- 角色菜单关联表
CREATE TABLE IF NOT EXISTS `sys_role_menu` (
    `id`      BIGINT NOT NULL AUTO_INCREMENT,
    `role_id` BIGINT NOT NULL,
    `menu_id` BIGINT NOT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_role_id` (`role_id`),
    KEY `idx_menu_id` (`menu_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色菜单关联';

-- 初始化默认数据：超级管理员 + 角色 + 菜单
INSERT INTO `sys_user` (`username`, `password`, `real_name`, `phone`, `status`, `role_id`) VALUES
('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '超级管理员', '13800000000', 1, 1);

INSERT INTO `sys_role` (`role_name`, `role_code`, `description`) VALUES
('超级管理员', 'SUPER_ADMIN', '拥有所有权限'),
('普通管理员', 'ADMIN', '常规管理权限'),
('普通用户', 'USER', '基础使用权限');

INSERT INTO `sys_menu` (`parent_id`, `menu_name`, `menu_type`, `path`, `component`, `icon`, `sort_order`) VALUES
(0, '系统管理', 'M', '/system', '', 'Setting', 1),
(1, '用户管理', 'C', '/system/user', 'views/user/UserView', 'User', 1),
(1, '角色管理', 'C', '/system/role', '', 'UserFilled', 2),
(1, '菜单管理', 'C', '/system/menu', '', 'Menu', 3),
(0, '设备中心', 'M', '/device', '', 'Monitor', 2),
(6, '设备列表', 'C', '/device/list', 'views/device/DeviceView', 'Cpu', 1),
(0, '数据中心', 'M', '/data', '', 'DataAnalysis', 3),
(9, '健康档案', 'C', '/data/archive', 'views/archive/ArchiveView', 'Document', 1),
(9, '数据查询', 'C', '/data/query', 'views/data/DataView', 'LineChart', 2),
(0, 'AI分析', 'M', '/ai', '', 'MagicStick', 4),
(12, '智能分析', 'C', '/ai/analysis', 'views/ai/AiView', 'TrendCharts', 1),
(12, 'AI助手', 'C', '/ai/chat', 'views/ai/AiChatView', 'ChatDotRound', 2),
(0, '预警中心', 'M', '/alert', '', 'Bell', 5),
(15, '预警记录', 'C', '/alert/list', 'views/alert/AlertView', 'Warning', 1),
(0, '报告中心', 'M', '/report', '', 'Document', 6),
(17, '报告列表', 'C', '/report/list', 'views/report/ReportView', 'Files', 1);

-- ==================== 设备模块 ====================

CREATE TABLE IF NOT EXISTS `device_info` (
    `id`              BIGINT       NOT NULL AUTO_INCREMENT,
    `device_code`     VARCHAR(64)  NOT NULL COMMENT '设备唯一编码',
    `device_name`     VARCHAR(100) NOT NULL COMMENT '设备名称',
    `device_type`     VARCHAR(30)  NOT NULL COMMENT '设备类型:BLOOD_PRESSURE/BLOOD_SUGAR/HEART_RATE/SLEEP/WEIGHT/THERMOMETER/OXYGEN/ECG',
    `brand`           VARCHAR(50)  DEFAULT '' COMMENT '品牌',
    `model`           VARCHAR(50)  DEFAULT '' COMMENT '型号',
    `firmware_ver`    VARCHAR(30)  DEFAULT '' COMMENT '固件版本',
    `user_id`         BIGINT       DEFAULT NULL COMMENT '绑定用户ID',
    `status`          TINYINT      DEFAULT 1 COMMENT '状态:0离线 1在线 2故障',
    `battery_level`   INT          DEFAULT 0 COMMENT '电量百分比',
    `last_online_time` DATETIME    DEFAULT NULL COMMENT '最后上线时间',
    `remark`          VARCHAR(500) DEFAULT '',
    `create_time`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `update_time`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_device_code` (`device_code`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_device_type` (`device_type`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备信息表';

-- ==================== 健康数据模块 ====================

CREATE TABLE IF NOT EXISTS `health_data` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT,
    `user_id`       BIGINT       NOT NULL COMMENT '用户ID',
    `device_code`   VARCHAR(64)  DEFAULT '' COMMENT '采集设备编码',
    `data_type`     VARCHAR(30)  NOT NULL COMMENT '数据类型:HEART_RATE/BLOOD_PRESSURE/BLOOD_SUGAR/SLEEP/WEIGHT/OXYGEN/STEPS/TEMPERATURE/ECG',
    `data_value`    JSON         NOT NULL COMMENT '测量值(JSON格式,支持多字段)',
    `unit`          VARCHAR(20)  DEFAULT '' COMMENT '单位',
    `measure_time`  DATETIME     NOT NULL COMMENT '测量时间',
    `source`        VARCHAR(20)  DEFAULT 'DEVICE' COMMENT '来源:DEVICE/MANUAL/AI_PREDICT',
    `is_abnormal`   TINYINT      DEFAULT 0 COMMENT '是否异常:0正常 1异常',
    `abnormal_desc` VARCHAR(255) DEFAULT '' COMMENT '异常描述',
    `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_measure` (`user_id`, `measure_time`),
    KEY `idx_data_type` (`data_type`),
    KEY `idx_measure_time` (`measure_time`),
    KEY `idx_is_abnormal` (`is_abnormal`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='健康数据主表';

-- ==================== 预警模块 ====================

CREATE TABLE IF NOT EXISTS `alert_record` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT,
    `alert_no`      VARCHAR(64)  NOT NULL COMMENT '预警编号',
    `user_id`       BIGINT       NOT NULL COMMENT '用户ID',
    `alert_type`    VARCHAR(30)  NOT NULL COMMENT '预警类型:THRESHOLD/TREND/AI_PREDICTION/MANUAL',
    `alert_level`   VARCHAR(10)  NOT NULL COMMENT '级别:INFO/WARNING/DANGER/CRITICAL',
    `alert_title`   VARCHAR(200) NOT NULL COMMENT '预警标题',
    `alert_content` TEXT         NOT NULL COMMENT '预警详情',
    `related_data`  JSON         DEFAULT NULL COMMENT '关联数据快照',
    `status`        VARCHAR(20)  DEFAULT 'PENDING' COMMENT '状态:PENDING/PROCESSING/RESOLVED/DISMISSED',
    `handle_user`   BIGINT       DEFAULT NULL COMMENT '处理人ID',
    `handle_time`   DATETIME     DEFAULT NULL COMMENT '处理时间',
    `handle_remark` VARCHAR(500) DEFAULT '' COMMENT '处理备注',
    `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `update_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_alert_no` (`alert_no`),
    KEY `idx_user_alert` (`user_id`, `create_time`),
    KEY `idx_alert_level` (`alert_level`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预警记录表';

-- 预警规则配置表
CREATE TABLE IF NOT EXISTS `alert_rule` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT,
    `rule_name`     VARCHAR(100) NOT NULL COMMENT '规则名称',
    `data_type`     VARCHAR(30)  NOT NULL COMMENT '适用数据类型',
    `condition_type` VARCHAR(20) NOT NULL COMMENT '条件类型:GT/LT/GTE/LTE/RANGE/CHANGE_RATE',
    `threshold_min`  DECIMAL(10,2) DEFAULT NULL COMMENT '阈值下限',
    `threshold_max`  DECIMAL(10,2) DEFAULT NULL COMMENT '阈值上限',
    `alert_level`   VARCHAR(10)  NOT NULL DEFAULT 'WARNING' COMMENT '触发等级',
    `notify_channels` VARCHAR(100) DEFAULT 'SYSTEM' COMMENT '通知渠道:SYSTEM/SMS/EMAIL/PUSH/WECHAT',
    `enabled`       TINYINT      DEFAULT 1 COMMENT '是否启用',
    `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预警规则配置表';

-- 插入默认预警规则
INSERT INTO `alert_rule` (`rule_name`, `data_type`, `condition_type`, `threshold_min`, `threshold_max`, `alert_level`) VALUES
('心率过高', 'HEART_RATE', 'GT', 120, NULL, 'DANGER'),
('心率过低', 'HEART_RATE', 'LT', 45, NULL, 'WARNING'),
('收缩压偏高', 'BLOOD_PRESSURE', 'RANGE', 140, 180, 'WARNING'),
('收缩压危险', 'BLOOD_PRESSURE', 'GT', 180, NULL, 'DANGER'),
('舒张压偏高', 'BLOOD_PRESSURE', 'RANGE', 90, 110, 'WARNING'),
('空腹血糖偏高', 'BLOOD_SUGAR', 'GT', 7.0, NULL, 'WARNING'),
('血氧饱和度过低', 'OXYGEN', 'LT', 92, NULL, 'DANGER'),
('体温异常', 'TEMPERATURE', 'RANGE', 38.0, 40.0, 'WARNING');

-- ==================== 报告模块 ====================

CREATE TABLE IF NOT EXISTS `report_record` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT,
    `report_no`     VARCHAR(64)  NOT NULL COMMENT '报告编号',
    `user_id`       BIGINT       NOT NULL COMMENT '用户ID',
    `report_type`   VARCHAR(30)  NOT NULL COMMENT '报告类型:DAILY/WEEKLY/MONTHLY/CUSTOM/AI_ANALYSIS',
    `report_title`  VARCHAR(200) NOT NULL COMMENT '报告标题',
    `report_file_url` VARCHAR(500) DEFAULT '' COMMENT 'PDF文件路径',
    `summary`       TEXT         DEFAULT NULL COMMENT '摘要',
    `period_start`  DATE         DEFAULT NULL COMMENT '统计周期开始',
    `period_end`    DATE         DEFAULT NULL COMMENT '统计周期结束',
    `status`        VARCHAR(20)  DEFAULT 'GENERATING' COMMENT '状态:GENERATING/COMPLETED/FAILED',
    `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `update_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_report_no` (`report_no`),
    KEY `idx_user_report` (`user_id`, `create_time`),
    KEY `idx_report_type` (`report_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报告记录表';

-- ==================== 日志审计模块 ====================

CREATE TABLE IF NOT EXISTS `operation_log` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT,
    `user_id`       BIGINT       DEFAULT NULL COMMENT '操作人ID',
    `username`      VARCHAR(50)  DEFAULT '' COMMENT '操作人名',
    `module`        VARCHAR(50)  NOT NULL COMMENT '操作模块',
    `operation`     VARCHAR(50)  NOT NULL COMMENT '操作类型:LOGIN/LOGOUT/CREATE/UPDATE/DELETE/EXPORT/IMPORT',
    `method`        VARCHAR(200) DEFAULT '' COMMENT '请求方法',
    `url`           VARCHAR(500) DEFAULT '' COMMENT '请求URL',
    `ip`            VARCHAR(50)  DEFAULT '' COMMENT 'IP地址',
    `request_param` TEXT         DEFAULT NULL COMMENT '请求参数',
    `response_data` TEXT         DEFAULT NULL COMMENT '响应数据',
    `duration_ms`   INT          DEFAULT 0 COMMENT '耗时(ms)',
    `status`        TINYINT      DEFAULT 1 COMMENT '结果:0失败 1成功',
    `error_msg`     TEXT         DEFAULT NULL COMMENT '错误信息',
    `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_log` (`user_id`, `create_time`),
    KEY `idx_module` (`module`),
    KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';

-- ==================== AI分析模块 ====================

CREATE TABLE IF NOT EXISTS `ai_analysis_record` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT,
    `user_id`       BIGINT       NOT NULL COMMENT '用户ID',
    `analysis_type` VARCHAR(30)  NOT NULL COMMENT '分析类型:TREND/RISK/PREDICTION/NLP_QA/REPORT',
    `input_data`    JSON         DEFAULT NULL COMMENT '输入数据',
    `model_used`    VARCHAR(50)  DEFAULT '' COMMENT '使用的模型',
    `result`        MEDIUMTEXT   NOT NULL COMMENT '分析结果(JSON/文本)',
    `confidence`    DECIMAL(5,4) DEFAULT NULL COMMENT '置信度',
    `cost_tokens`   INT          DEFAULT 0 COMMENT 'Token消耗',
    `cost_time_ms`  INT          DEFAULT 0 COMMENT '耗时(ms)',
    `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_analysis` (`user_id`, `create_time`),
    KEY `idx_analysis_type` (`analysis_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI分析记录表';

-- ==================== Nacos配置数据库（集群模式）====================

CREATE DATABASE IF NOT EXISTS `nacos_config` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `nacos_config`;

/* Nacos配置表结构（简化版，完整版由Nacos自动初始化）*/
CREATE TABLE IF NOT EXISTS `config_info` (
    `id`            BIGINT(20)   NOT NULL AUTO_INCREMENT,
    `data_id`       VARCHAR(255) NOT NULL COMMENT 'data_id',
    `group_id`      VARCHAR(128) DEFAULT '' COMMENT 'group_id',
    `content`       LONGTEXT     NOT NULL COMMENT 'content',
    `tenant_id`     VARCHAR(128) DEFAULT '' COMMENT 'tenant_id',
    `app_name`      VARCHAR(128) DEFAULT '',
    `src_ip`        VARCHAR(50)  DEFAULT '',
    `src_user`      VARCHAR(50)  DEFAULT '',
    `gmt_create`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `gmt_modified`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_configinfo_datagrouptenant` (`data_id`,`group_id`,`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Nacos配置信息表';

-- 插入Nacos公共配置（微服务共享）
INSERT INTO `config_info` (`data_id`, `group_id`, `content`, `tenant_id`) VALUES
('common-config.yaml', 'DEFAULT_GROUP', '# 公共配置\nspring:\n  application:\n    name: zhihealth-common\n  jackson:\n    date-format: yyyy-MM-dd HH:mm:ss\n    time-zone: Asia/Shanghai\n    default-property-inclusion: non_null\nmybatis-plus:\n  configuration:\n    map-underscore-to-camel-case: true\n    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl\nlogging:\n  level:\n    com.zhihealth: debug', ''),
('redis-config.yaml', 'DEFAULT_GROUP', 'spring:\n  redis:\n    host: ${REDIS_HOST:localhost}\n    port: ${REDIS_PORT:6379}\n    password: ${REDIS_PASSWORD:}\n    database: 0\n    lettuce:\n      pool:\n        max-active: 16\n        max-idle: 8\n        min-idle: 2', '');

USE `zhihealth`;
SET FOREIGN_KEY_CHECKS = 1;

-- 输出完成提示
SELECT '智康云枢数据库初始化完成!' AS message;
SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'zhihealth';
