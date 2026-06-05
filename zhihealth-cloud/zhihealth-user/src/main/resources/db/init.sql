CREATE DATABASE IF NOT EXISTS `zhihealth_user` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE `zhihealth_user`;

-- 用户表
CREATE TABLE IF NOT EXISTS `sys_user` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password` varchar(200) NOT NULL,
  `nickname` varchar(100) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `avatar` varchar(500) DEFAULT NULL,
  `status` tinyint(1) NOT NULL DEFAULT '1',
  `remark` varchar(500) DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 角色表
CREATE TABLE IF NOT EXISTS `sys_role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `role_name` varchar(50) NOT NULL COMMENT '角色名称',
  `role_code` varchar(50) NOT NULL COMMENT '角色编码',
  `description` varchar(200) DEFAULT NULL COMMENT '角色描述',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态:1启用 0禁用',
  `sort_order` int(11) NOT NULL DEFAULT '0' COMMENT '排序',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 权限表
CREATE TABLE IF NOT EXISTS `sys_permission` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `permission_name` varchar(100) NOT NULL COMMENT '权限名称',
  `permission_code` varchar(100) NOT NULL COMMENT '权限编码',
  `resource_type` varchar(20) NOT NULL COMMENT '资源类型:menu/button/api',
  `resource_code` varchar(50) NOT NULL COMMENT '资源编码(user/device/data等)',
  `action` varchar(30) NOT NULL COMMENT '操作:view/create/update/delete/export/import等',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '状态:1启用 0禁用',
  `parent_id` bigint(20) DEFAULT '0' COMMENT '父权限ID',
  `sort_order` int(11) NOT NULL DEFAULT '0' COMMENT '排序',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_permission_code` (`permission_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 用户-角色关联表
CREATE TABLE IF NOT EXISTS `sys_user_role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `role_id` bigint(20) NOT NULL COMMENT '角色ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`, `role_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_role_id` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 角色-权限关联表
CREATE TABLE IF NOT EXISTS `sys_role_permission` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `role_id` bigint(20) NOT NULL COMMENT '角色ID',
  `permission_id` bigint(20) NOT NULL COMMENT '权限ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_permission` (`role_id`, `permission_id`),
  KEY `idx_role_id` (`role_id`),
  KEY `idx_permission_id` (`permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ==================== 初始化默认角色 ====================
INSERT INTO `sys_role` (`role_name`, `role_code`, `description`, `status`, `sort_order`) VALUES
('超级管理员', 'super_admin', '拥有系统全部权限，可执行任何操作', 1, 0),
('系统管理员', 'admin', '负责系统日常运维和管理工作', 1, 1),
('医生/健康顾问', 'doctor', '负责查看和分析用户健康数据，提供专业建议', 1, 2),
('普通用户', 'user', '普通注册用户，可查看自己的健康数据', 1, 3);

-- ==================== 初始化默认权限 ====================

-- 用户管理权限 (user)
INSERT INTO `sys_permission` (`permission_name`, `permission_code`, `resource_type`, `resource_code`, `action`, `parent_id`, `sort_order`) VALUES
('用户管理', 'user:manage', 'menu', 'user', 'view', 0, 1),
('用户查看', 'user:view', 'button', 'user', 'view', 1, 1),
('用户新增', 'user:create', 'button', 'user', 'create', 1, 2),
('用户编辑', 'user:update', 'button', 'user', 'update', 1, 3),
('用户删除', 'user:delete', 'button', 'user', 'delete', 1, 4);

-- 设备管理权限 (device)
INSERT INTO `sys_permission` (`permission_name`, `permission_code`, `resource_type`, `resource_code`, `action`, `parent_id`, `sort_order`) VALUES
('设备管理', 'device:manage', 'menu', 'device', 'view', 0, 2),
('设备查看', 'device:view', 'button', 'device', 'view', 6, 1),
('设备新增', 'device:create', 'button', 'device', 'create', 6, 2),
('设备编辑', 'device:update', 'button', 'device', 'update', 6, 3),
('设备删除', 'device:delete', 'button', 'device', 'delete', 6, 4);

-- 数据管理权限 (data)
INSERT INTO `sys_permission` (`permission_name`, `permission_code`, `resource_type`, `resource_code`, `action`, `parent_id`, `sort_order`) VALUES
('数据查询', 'data:view', 'menu', 'data', 'view', 0, 3),
('数据导入', 'data:import', 'button', 'data', 'import', 11, 1),
('数据导出', 'data:export', 'button', 'data', 'export', 11, 2);

-- 告警中心权限 (alert)
INSERT INTO `sys_permission` (`permission_name`, `permission_code`, `resource_type`, `resource_code`, `action`, `parent_id`, `sort_order`) VALUES
('告警中心', 'alert:manage', 'menu', 'alert', 'view', 0, 4),
('告警查看', 'alert:view', 'button', 'alert', 'view', 14, 1),
('告警处理', 'alert:handle', 'button', 'alert', 'handle', 14, 2),
('告警规则配置', 'alert:config', 'button', 'alert', 'config', 14, 3);

-- AI分析权限 (ai)
INSERT INTO `sys_permission` (`permission_name`, `permission_code`, `resource_type`, `resource_code`, `action`, `parent_id`, `sort_order`) VALUES
('AI智能分析', 'ai:manage', 'menu', 'ai', 'analyze', 0, 5),
('AI分析', 'ai:analyze', 'button', 'ai', 'analyze', 18, 1),
('AI模型管理', 'ai:model_manage', 'button', 'ai', 'model_manage', 18, 2);

-- 报告中心权限 (report)
INSERT INTO `sys_permission` (`permission_name`, `permission_code`, `resource_type`, `resource_code`, `action`, `parent_id`, `sort_order`) VALUES
('报告中心', 'report:manage', 'menu', 'report', 'view', 0, 6),
('报告查看', 'report:view', 'button', 'report', 'view', 21, 1),
('报告生成', 'report:generate', 'button', 'report', 'generate', 21, 2),
('报告下载', 'report:download', 'button', 'report', 'download', 21, 3);

-- 系统管理权限 (settings/log)
INSERT INTO `sys_permission` (`permission_name`, `permission_code`, `resource_type`, `resource_code`, `action`, `parent_id`, `sort_order`) VALUES
('系统设置', 'settings:view', 'menu', 'settings', 'view', 0, 7),
('日志查看', 'log:view', 'menu', 'log', 'view', 0, 8),
('日志清理', 'log:clean', 'button', 'log', 'clean', 26, 1),
('日志导出', 'log:export', 'button', 'log', 'export', 26, 2);

-- 缓存管理权限 (cache)
INSERT INTO `sys_permission` (`permission_name`, `permission_code`, `resource_type`, `resource_code`, `action`, `parent_id`, `sort_order`) VALUES
('缓存管理', 'cache:manage', 'menu', 'cache', 'view', 0, 9);

-- ==================== 超级管理员分配全部权限 ====================
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`)
SELECT 1, id FROM `sys_permission` WHERE `deleted` = 0 AND `status` = 1;

-- 系统管理员权限（不含用户删除和AI模型管理）
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`)
SELECT 2, id FROM `sys_permission`
WHERE `deleted` = 0 AND `status` = 1
AND `permission_code` NOT IN ('user:delete', 'ai:model_manage');

-- 医生角色权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`)
SELECT 3, id FROM `sys_permission`
WHERE `deleted` = 0 AND `status` = 1
AND `permission_code` IN (
    'user:view', 'device:view', 'data:view', 'data:export',
    'alert:view', 'alert:handle', 'ai:analyze',
    'report:view', 'report:generate', 'report:download'
);

-- 普通用户权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`)
SELECT 4, id FROM `sys_permission`
WHERE `deleted` = 0 AND `status` = 1
AND `permission_code` IN ('data:view', 'report:view', 'report:download', 'alert:view');

-- ==================== 默认管理员账号 ====================
-- 密码为 admin123 (BCrypt加密)
INSERT INTO `sys_user` (`username`, `password`, `nickname`, `status`, `remark`) VALUES
('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '系统管理员', 1, '系统默认管理员账号');

-- 为admin分配超级管理员角色
INSERT INTO `sys_user_role` (`user_id`, `role_id`) VALUES (1, 1);
