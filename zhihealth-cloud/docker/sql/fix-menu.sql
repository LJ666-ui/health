USE zhihealth_user;

-- 修复sys_menu表
ALTER TABLE sys_menu ADD COLUMN sort_order INT DEFAULT 0 COMMENT '排序' AFTER icon;
ALTER TABLE sys_menu ADD COLUMN deleted TINYINT DEFAULT 0 COMMENT '逻辑删除' AFTER update_time;

-- 显示结果
SELECT 'sys_menu fixed' as status;
DESCRIBE sys_menu;
SELECT COUNT(*) as role_count FROM sys_role;
