USE zhihealth_user;

-- 修复sys_menu表：添加缺失的update_time和deleted字段
ALTER TABLE sys_menu ADD COLUMN update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间' AFTER create_time;
ALTER TABLE sys_menu ADD COLUMN deleted TINYINT DEFAULT 0 COMMENT '逻辑删除' AFTER update_time;

-- 验证
DESCRIBE sys_menu;
SELECT 'Table structure fixed!' as result;
