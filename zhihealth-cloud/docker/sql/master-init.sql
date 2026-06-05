-- MySQL主库初始化：创建复制账号
-- 此脚本在master容器首次启动时自动执行

CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED WITH mysql_native_password BY 'repl_2024_secure';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'repl_user'@'%';
FLUSH PRIVILEGES;

-- 确认GTID已开启
SELECT @@server_id, @@gtid_mode, @@log_bin;
