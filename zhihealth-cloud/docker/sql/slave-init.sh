#!/bin/bash
# MySQL从库初始化：配置主从同步
# 在slave容器首次启动后手动执行，或通过entrypoint触发

set -e

MASTER_HOST="mysql-master"
MASTER_PORT=3306
MASTER_USER="repl_user"
MASTER_PASS="repl_2024_secure"

echo "[MySQL Slave] 等待主库就绪..."
until mysqladmin ping -h"$MASTER_HOST" -P"$MASTER_PORT" -uroot -p"${MYSQL_ROOT_PASSWORD:-123456}" --silent; do
  echo "[MySQL Slave] 等待主库... $(date)"
  sleep 3
done

echo "[MySQL Slave] 主库已连接，开始配置主从复制..."

# 获取主库当前binlog位置
MASTER_STATUS=$(mysql -h"$MASTER_HOST" -P"$MASTER_PORT" -u"$MASTER_USER" -p"$MASTER_PASS" -N -e "SHOW MASTER STATUS\G" 2>/dev/null | grep -E "File|Position")
echo "$MASTER_STATUS"

# 配置主从关系（使用GTID方式）
mysql -uroot -p"${MYSQL_ROOT_PASSWORD:-123456}" <<'EOSQL'
CHANGE REPLICATION SOURCE TO
  SOURCE_HOST='mysql-master',
  SOURCE_PORT=3306,
  SOURCE_USER='repl_user',
  SOURCE_PASSWORD='repl_2024_secure',
  GET_MASTER_PUBLIC_KEY=1;

START REPLICA;

SHOW REPLICA STATUS\G
EOSQL

echo "[MySQL Slave] 主从复制配置完成！"
