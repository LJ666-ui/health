USE zhihealth_user;

-- 修复sys_role表：添加sort_order字段
ALTER TABLE sys_role ADD COLUMN sort_order INT DEFAULT 0 COMMENT '排序' AFTER status;

-- 验证
DESCRIBE sys_role;
SELECT 'sys_role fixed!' as result;
