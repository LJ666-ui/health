# 智康云枢 - 云服务器生产部署完整指南（基于已有2C4G双服务器）

## 📋 部署环境概览

### 已有资源

| 服务器 | 角色 | IP地址 | 配置 | 状态 |
|--------|------|--------|------|------|
| **zhihealth-master** | 主节点（应用服务器） | 182.92.1.136 | 2核4G CentOS 7.9 | 💤 已停止 |
| **zhihealth-slave** | 从节点（数据服务器） | 39.105.129.207 | 2核4G CentOS 7.9 | 💤 已停止 |

### 主节点已部署组件
- ✅ Docker v26.1.4 + Compose v2.27.1
- ✅ MySQL 8.0 (端口3306, 密码123456)
- ✅ Nacos 2.3.0 (端口8848, 账号nacos/nacos)
- ✅ Redis 7 (端口6379, 无密码)
- ✅ RabbitMQ (端口5672/15672)

### 从节点已部署组件
- ✅ Docker v26.1.4 + Compose v2.27.1
- ✅ InfluxDB 2.7 (端口8086, admin/admin123456)
- ✅ MongoDB 6.0 (端口27017, admin/mongo123456)

---

## 🚀 快速部署流程（预计30分钟）

### 第1步：启动云服务器（5分钟）

#### 1.1 启动主节点
**方式A：阿里云控制台**
1. 登录 [阿里云ECS控制台](https://ecs.console.aliyun.com/)
2. 找到实例 `zhihealth-master` (i-2zeb06mtzq67qeOzwrk)
3. 点击 **"开机"** → **"确定"**
4. 等待状态变为 **"运行中"**

**方式B：命令行（需要安装aliyun-cli）**
```bash
aliyun ecs StartInstance --InstanceId i-2zeb06mtzq67qeOzwrk
```

#### 1.2 启动从节点
同样操作，启动 `zhihealth-slave` (i-2ze7jote79dwl74ykssz)

#### 1.3 验证启动成功
```bash
# 在本地电脑执行（确保能SSH连接）
ssh root@182.92.1.136 "hostname && uptime"
ssh root@39.105.129.207 "hostname && uptime"
```

**预期输出：**
```
zhihealth-master
 10:00:01 up 2 min,  1 user,  load average: 0.00, 0.02, 0.05

zhihealth-slave
 10:00:02 up 2 min,  1 user,  load average: 0.00, 0.03, 0.05
```

---

### 第2步：上传代码和部署包（10分钟）

#### 2.1 在本地电脑打包项目文件

**在 Windows 本地电脑执行（PowerShell）：**
```powershell
cd e:\Health

# 创建部署包（排除node_modules、target、.git等大文件夹）
tar -czvf zhihealth-deploy.tar.gz `
    --exclude="zhihealth-cloud/*/target" `
    --exclude="zhihealth-cloud/.git" `
    --exclude="zhihealth-frontend/node_modules" `
    --exclude="zhihealth-frontend/dist" `
    --exclude=".git" `
    deploy/
    zhihealth-cloud/
    zhihealth-frontend/

# 查看包大小（应该<100MB）
ls -lh zhihealth-deploy.tar.gz
```

#### 2.2 上传到两台服务器

**上传到主节点：**
```powershell
scp zhihealth-deploy.tar.gz root@182.92.1.136:/opt/
```

**上传到从节点：**
```powershell
scp zhihealth-deploy.tar.gz root@39.105.129.207:/opt/
```

**或者使用图形化工具（推荐新手）：**
- **WinSCP**: https://winscp.net/eng/download.php
- **FileZilla**: https://filezilla-project.org/download.php
- **Xftp**: 随宝塔面板提供

**操作步骤（以WinSCP为例）：**
1. 打开WinSCP
2. Hostname: `182.92.1.136`, User: `root`, Password: 你的密码
3. 登录后进入 `/opt/` 目录
4. 从左侧本地窗口拖拽 `zhihealth-deploy.tar.gz` 到右侧
5. 同样操作上传到从节点 `39.105.129.207`

---

### 第3步：配置安全组规则（重要！）

**阿里云控制台操作：**

#### 3.1 主节点安全组规则
登录 [安全组控制台](https://ecs.console.aliyun.com/#/securityGroupDetail/region/cn-beijing) → 找到主节点安全组 → **添加规则**

| 方向 | 端口范围 | 授权对象 | 协议 | 用途 |
|------|----------|----------|------|------|
| 入方向 | 80/80 | 0.0.0.0/0 | TCP | HTTP访问前端 |
| 入方向 | 8080/8080 | 0.0.0.0/0 | TCP | API网关 |
| 入方向 | 8081-8091 | 0.0.0.0/0 | TCP | 微服务直连（可选） |
| 入方向 | 3306/3306 | 39.105.129.207/32 | TCP | MySQL仅从节点访问 |
| 入方向 | 8848/8848 | 0.0.0.0/0 | TCP | Nacos控制台 |
| 入方向 | 6379/6379 | 172.16.0.0/16 | TCP | Redis仅内网 |

#### 3.2 从节点安全组规则

| 方向 | 端口范围 | 授权对象 | 协议 | 用途 |
|------|----------|----------|------|------|
| 入方向 | 27017/27017 | 182.92.1.136/32 | TCP | MongoDB仅主节点访问 |
| 入方向 | 8086/8086 | 0.0.0.0/0 | TCP | InfluxDB（可选） |

---

### 第4步：执行部署脚本（10分钟）

#### 4.1 SSH连接主节点并部署

**在本地电脑执行：**
```bash
ssh root@182.92.1.136
```

**进入服务器后执行：**
```bash
# 解压部署包
cd /opt
tar -xzvf zhihealth-deploy.tar.gz

# 进入deploy目录
cd deploy

# 设置执行权限
chmod +x *.sh

# 创建环境变量文件
cat > .env << 'EOF'
MYSQL_PASSWORD=root_2024_zhihealth
REDIS_PASSWORD=zhihealth_redis_2024
INFLUX_PASSWORD=admin123456
MONGO_PASSWORD=mongo123456
SLAVE_IP=39.105.129.207
EOF

# 执行主节点部署脚本
./deploy-master.sh
```

**脚本会自动完成：**
1. ✅ 系统优化（关闭防火墙、优化内核参数）
2. ✅ 启动已有中间件（MySQL、Redis、Nacos）
3. ✅ 构建Docker镜像（如果本地有Maven）
4. ✅ 启动所有微服务容器
5. ✅ 健康检查验证

#### 4.2 SSH连接从节点并部署

**新开一个终端窗口：**
```bash
ssh root@39.105.129.207
```

**进入服务器后执行：**
```bash
# 解压部署包
cd /opt
tar -xzvf zhihealth-deploy.tar.gz

# 进入deploy目录
cd deploy

# 设置执行权限
chmod +x *.sh

# 创建环境变量文件
cat > .env << 'EOF'
INFLUX_PASSWORD=admin123456
MONGO_PASSWORD=mongo123456
MASTER_IP=182.92.1.136
EOF

# 执行从节点部署脚本
./deploy-slave.sh
```

**脚本会自动完成：**
1. ✅ 系统优化
2. ✅ 启动InfluxDB和MongoDB
3. ✅ 配置网络互通（测试到主节点的连通性）
4. ✅ 健康检查验证

---

### 第5步：验证部署结果（5分钟）

#### 5.1 访问前端界面

打开浏览器访问：
- **前端界面**: http://182.92.1.136
- **API网关**: http://182.92.1.136:8080
- **Nacos控制台**: http://182.92.1.136:8848/nacos (nacos/nacos)

#### 5.2 测试API接口

**在本地电脑执行：**
```bash
# 测试Gateway健康检查
curl http://182.92.1.136:8080/actuator/health

# 测试User服务角色列表
curl http://182.92.1.136:8081/user/role/list

# 测试Device服务设备列表
curl http://182.92.1.136:8082/device/list

# 测试InfluxDB（从节点）
curl http://39.105.129.207:8086/health

# 测试MongoDB（从节点）
telnet 39.105.129.207 27017
```

#### 5.3 登录系统测试

1. 打开 http://182.92.1.136
2. 使用账号登录：
   - 用户名: `testuser`
   - 密码: `Test123456`
3. 测试功能：
   - 查看仪表盘
   - 进入用户管理
   - 查看设备列表
   - 测试数据采集

---

## 📊 资源分配方案（2C4G优化版）

### 主节点内存分配（总4GB）

| 服务 | 内存限制 | CPU限制 | 说明 |
|------|----------|---------|------|
| MySQL | 1GB | 1核 | 核心数据库 |
| Nacos | 800MB | 1.5核 | 注册中心+配置 |
| Redis | 300MB | 0.5核 | 缓存层 |
| Gateway | 350MB | 0.5核 | API网关 |
| User服务 | 350MB | 0.5核 | 用户认证 |
| Device服务 | 280MB | 0.3核 | 设备管理 |
| Collect服务 | 280MB | 0.3核 | 数据采集 |
| Storage服务 | 280MB | 0.3核 | 数据存储 |
| Cache服务 | 180MB | 0.2核 | 缓存调度 |
| Alert服务 | 280MB | 0.3核 | 告警预警 |
| Report服务 | 280MB | 0.3核 | 报告生成 |
| Log服务 | 180MB | 0.2核 | 操作日志 |
| AI服务 | 450MB | 0.8核 | AI分析（最重） |
| Nginx | 50MB | 0.1核 | 反向代理 |
| **总计** | **~5.7GB** | **~7.8核** | **实际使用~3.5GB** |

**说明：** 
- 总限制>物理内存是正常的（不是所有服务同时满载）
- 实际运行时内存使用约3.5GB（剩余500MB系统开销）
- CPU使用率通常<50%（大部分时间空闲）

### 从节点内存分配（总4GB）

| 服务 | 内存限制 | CPU限制 | 说明 |
|------|----------|---------|------|
| InfluxDB | 512MB | 1核 | 时序数据库 |
| MongoDB | 768MB | 1核 | 文档数据库 |
| **总计** | **~1.28GB** | **2核** | **剩余2.7GB可用** |

**优势：** 从节点资源充裕，后续可扩展Hive大数据栈

---

## 🔧 运维管理命令速查

### 日常监控

```bash
# 查看所有容器状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 实时查看日志
docker logs -f zhihealth-gateway          # 网关日志
docker logs -f zhihealth-user             # 用户服务日志
docker logs -f zhihealth-mysql           # MySQL日志

# 查看资源使用情况
docker stats --no-stream                 # 一次性快照
docker stats                             # 实时监控（类似top）

# 查看磁盘使用
df -h                                    # 系统磁盘
docker system df                         # Docker磁盘
```

### 服务管理

```bash
# 重启单个服务
docker restart zhihealth-gateway

# 重启所有微服务（不重启MySQL/Redis/Nacos）
cd /opt/zhihealth/docker
docker-compose restart gateway user device collect storage cache alert report log ai nginx

# 停止所有服务
docker-compose down

# 停止并删除数据卷（⚠️ 会丢失数据）
docker-compose down -v
```

### 数据备份

```bash
# 备份MySQL数据库
mkdir -p /opt/zhihealth/backups/$(date +%Y%m%d)
docker exec zhihealth-mysql mysqldump -u root -p'root_2024_zhihealth' \
  --all-databases --single-transaction > /opt/zhihealth/backups/$(date +%Y%m%d)/mysql-full-backup.sql

# 备份Redis
docker exec zhihealth-redis redis-cli BGSAVE
cp /var/lib/docker/volumes/deploy_redis_data/_data/dump.rdb /opt/zhihealth/backups/$(date +%Y%m%d)/redis-backup.rdb

# 备份MongoDB
docker exec zhihealth-mongodb mongodump --username admin --password mongo123456 \
  --authenticationDatabase admin --out /tmp/mongobackup
docker cp zhihealth-mongodb:/tmp/mongobackup /opt/zhihealth/backups/$(date +%Y%m%d)/mongodb-backup
```

### 故障排查

```bash
# 容器无法启动？查看详细错误
docker logs <容器名>

# 内存不足？
free -h
docker system prune -a  # 清理无用镜像和容器

# 端口被占用？
lsof -i :8080
kill -9 <PID>

# 无法连接其他服务器？
ping 39.105.129.207
telnet 39.105.129.207 27017

# Docker服务异常？
systemctl status docker
journalctl -u docker -f
```

---

## ⚡ 性能优化建议（针对2C4G限制）

### 1. 减少不必要的微服务
如果CPU/内存仍然紧张，可以暂时禁用非核心服务：

```bash
# 停止AI服务（最耗资源）
docker stop zhihealth-ai

# 停止报告服务（按需启动）
docker stop zhihealth-report

# 停止日志服务（可后期开启）
docker stop zhihealth-log
```

### 2. 启用Swap分区（增加虚拟内存）
```bash
# 创建2GB Swap文件
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 设置开机自动挂载
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 验证
free -h
```

### 3. 优化JVM参数
编辑各服务的`JAVA_OPTS`环境变量：
```yaml
environment:
  JAVA_OPTS: "-Xms128m -Xmx256m -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
```

### 4. 启用Docker日志轮转
防止日志文件占满磁盘：
```bash
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

systemctl restart docker
```

---

## 🔒 安全加固建议

### 1. 修改默认密码
```bash
# MySQL密码
docker exec -it zhihealth-mysql mysql -u root -p'旧密码' -e "ALTER USER 'root'@'%' IDENTIFIED BY '新强密码';"

# Redis密码（修改docker-compose.yml后重启）
# Nacos密码（修改docker-compose.yml后重启）
```

### 2. 配置防火墙（替代完全关闭）
```bash
# 安装iptables-services
yum install iptables-services -y

# 允许必要端口
iptables -I INPUT -p tcp --dport 22 -j ACCEPT      # SSH
iptables -I INPUT -p tcp --dport 80 -j ACCEPT       # HTTP
iptables -I INPUT -p tcp --dport 8080 -j ACCEPT     # API网关
iptables -I INPUT -p tcp --dport 8848 -j ACCEPT     # Nacos
iptables -I INPUT -s 39.105.129.207 -p tcp --dport 3306 -j ACCEPT  # MySQL仅从节点
iptables -I INPUT -s 182.92.1.136 -p tcp --dport 27017 -j ACCEPT  # MongoDB仅主节点

# 其他全部拒绝
iptables -P INPUT DROP

# 保存规则
service iptables save
```

### 3. 配置SSL证书（HTTPS）
参考 `config/nginx.ssl.conf.example` 文件（需购买或申请免费证书）

---

## 📞 常见问题FAQ

### Q1: 部署后无法访问前端页面？
**排查步骤：**
1. 检查Nginx是否运行：`docker ps | grep nginx`
2. 检查80端口是否开放：`netstat -tlnp | grep :80`
3. 检查阿里云安全组是否放行80端口
4. 查看Nginx日志：`docker logs zhihealth-nginx`

### Q2: 微服务启动失败？
**常见原因及解决：**
- **内存不足**：`docker stats` 查看，调整JVM `-Xmx` 参数
- **MySQL连接失败**：检查密码是否正确（`.env`文件中的`MYSQL_PASSWORD`）
- **Nacos未就绪**：等待Nacos健康检查通过后再启动微服务
- **端口冲突**：`lsof -i :端口号` 查看占用进程

### Q3: 主从节点网络不通？
**解决方法：**
1. 检查双方防火墙：`systemctl status firewalld`
2. 检查安全组规则：确保放行了内网通信端口
3. Ping测试：`ping 对方IP`
4. Telnet测试：`telnet 对方IP 端口号`

### Q4: 如何更新版本？
```bash
# 1. 上传新代码到/opt/zhihealth
# 2. 重新构建镜像
cd /opt/zhihealth/docker
docker-compose build gateway user device ...

# 3. 重启对应服务
docker-compose up -d gateway user device ...
```

### Q5: 如何扩容升级？
当2C4G不够用时：
1. **阿里云控制台** → **实例** → **更多** → **升配**
2. 选择更高规格（如4C8G或8C16G）
3. 支付差价后立即生效（需重启一次）
4. 所有数据和配置保留不变

---

## 📈 监控告警（可选增强）

### 安装Prometheus + Grafana（轻量版）
```bash
# 在从节点部署监控（不影响主节点性能）
# 参考: docker-compose.monitoring.yml（待创建）
```

### 基础监控脚本
```bash
#!/bin/bash
# health-check.sh - 定期检查服务健康状态

while true; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # 检查Gateway
    if curl -sf http://localhost:8080/actuator/health > /dev/null; then
        echo "$timestamp | Gateway | OK"
    else
        echo "$timestamp | Gateway | FAIL" | tee -a /opt/zhihealth/logs/alert.log
    fi
    
    # 检查MySQL
    if docker exec zhihealth-mysql mysqladmin ping > /dev/null; then
        echo "$timestamp | MySQL | OK"
    else
        echo "$timestamp | MySQL | FAIL" | tee -a /opt/zhihealth/logs/alert.log
    fi
    
    sleep 60  # 每60秒检查一次
done
```

---

## ✅ 部署完成确认清单

部署完成后，请逐项确认：

- [ ] 两台服务器均已启动且状态为"运行中"
- [ ] 安全组规则已正确配置（80/8080/8848等端口）
- [ ] 代码已上传到 `/opt/zhihealth/` 目录
- [ ] `.env` 环境变量文件已配置
- [ ] 主节点所有容器运行正常（`docker ps` 显示15个容器Up）
- [ ] 从节点InfluxDB和MongoDB运行正常
- [ ] 可以通过浏览器访问 http://182.92.1.136
- [ ] 可以登录系统（testuser/Test123456）
- [ ] API接口正常返回数据（/user/role/list等）
- [ ] 主从节点网络互通正常
- [ ] 数据备份计划已制定
- [ ] 监控告警已配置（可选）

---

**🎉 祝你部署顺利！如有问题请查看日志或联系技术支持。**

**最后更新:** 2026-06-05  
**适用版本:** v1.0 (针对2C4G双服务器优化)
