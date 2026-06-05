USE zhihealth_user;

-- 只添加deleted列（sort_order已存在）
ALTER TABLE sys_menu ADD COLUMN deleted TINYINT DEFAULT 0 COMMENT '逻辑删除' AFTER update_time;

-- 验证
DESCRIBE sys_menu;
