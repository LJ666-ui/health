-- 修复所有表结构问题
USE zhihealth_user;

-- 1. 确保sys_menu有sort_order和deleted字段
ALTER TABLE sys_menu ADD COLUMN IF NOT EXISTS sort_order INT DEFAULT 0 COMMENT '排序' AFTER icon;
ALTER TABLE sys_menu ADD COLUMN IF NOT EXISTS deleted TINYINT DEFAULT 0 COMMENT '逻辑删除' AFTER update_time;

-- 2. 检查并显示所有表结构
SHOW TABLES;
DESCRIBE sys_role;
DESCRIBE sys_menu;
DESCRIBE sys_user;
SELECT COUNT(*) as role_count FROM sys_role;
