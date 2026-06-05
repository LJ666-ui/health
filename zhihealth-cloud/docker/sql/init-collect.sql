-- 逐个初始化剩余业务库（跳过Nacos配置冲突）
USE zhihealth_collect;
SOURCE /tmp/init.sql;
SELECT 'zhihealth_collect DONE' as status;
