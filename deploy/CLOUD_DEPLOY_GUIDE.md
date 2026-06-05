# 智康云枢 - 云服务器部署完整指南

## 📋 目录
1. [云服务器配置推荐](#1-云服务器配置推荐)
2. [快速部署（一键脚本）](#2-快速部署一键脚本)
3. [手动部署详细步骤](#3-手动部署详细步骤)
4. [本地迁移到云端](#4-本地迁移到云端)
5. [常见问题解决](#5-常见问题解决)
6. [运维管理命令](#6-运维管理命令)

---

## 1️⃣ 云服务器配置推荐

### 方案A：单服务器部署（推荐初期）
```
┌─────────────────────────────────────┐
│         云服务器 (8核16G)           │
│                                     │
│  ┌───────────┐  ┌──────────────┐   │
│  │  Nginx:80  │  │ Gateway:8080 │   │
│  └───────────┘  └──────────────┘   │
│  ┌─────────────────────────────┐   │
│  │    MySQL + Redis + Nacos     │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ 10个微服务 (User/Device...)  │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ MongoDB + InfluxDB          │   │
│  └─────────────────────────────┘   │
│                                     │
│  费用: ~300-500元/月              │
└─────────────────────────────────────┘
```

**推荐配置：**
- **CPU**: 8核
- **内存**: 16GB
- **硬盘**: 100GB SSD + 200GB数据盘
- **带宽**: 5Mbps（可按需升级）
- **操作系统**: CentOS 7.9 或 Ubuntu 20.04 LTS
- **服务商**: 阿里云ECS / 腾讯云CVM / 华为云ECS

### 方案B：双服务器部署（生产环境）
```
┌──────────────────┐     ┌──────────────────────┐
│   主应用服务器     │     │    大数据服务器        │
│   (4核8G)         │     │    (8核16G)          │
│                  │     │                      │
│ • Nginx          │────▶│• Hadoop HDFS         │
│ • Gateway        │     │• Hive                │
│ • MySQL          │     │• MongoDB             │
│ • Redis          │     │• InfluxDB            │
│ • Nacos          │     │                      │
│ • 10个微服务      │     │                      │
│                  │     │                      │
│ 费用: ~200元/月  │     │ 费用: ~400元/月      │
└──────────────────┘     └──────────────────────┘
```

**适用场景**: 数据量大、需要Hive分析、用户量>1000

---

## 2️⃣ 快速部署（一键脚本）

### 步骤1：购买并连接云服务器
```bash
# 在本地电脑执行（使用SSH连接）
ssh root@你的服务器IP

# 首次登录修改密码
passwd
```

### 步骤2：上传部署包
```bash
# 在本地电脑执行（将deploy文件夹打包上传）
cd e:\Health
tar -czvf deploy.tar.gz deploy/
scp deploy.tar.gz root@你的服务器IP:/opt/

# 或使用工具：WinSCP / FileZilla / Xftp
```

### 步骤3：执行一键部署
```bash
# 在云服务器上执行
cd /opt
tar -xzvf deploy.tar.gz
cd deploy

# 赋予执行权限
chmod +x deploy-cloud.sh

# 执行部署（交互式）
./deploy-cloud.sh

# 或非交互式执行
./deploy-cloud.sh 你的IP地址
```

### 步骤4：验证部署结果
```bash
# 查看所有容器状态
docker ps --format "table {{.Names}}\t{{.Status}}"

# 测试API
curl http://localhost:8080/actuator/health
curl http://localhost:8081/user/role/list

# 访问前端
浏览器打开: http://你的服务器IP
```

---

## 3️⃣ 手动部署详细步骤

### 3.1 安装基础环境
```bash
# 更新系统
yum update -y  # CentOS
# apt update && apt upgrade -y  # Ubuntu

# 安装Docker
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker

# 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 安装Git和Maven
yum install -y git maven java-17-openjdk-devel  # CentOS
# apt install -y git maven openjdk-17-jdk  # Ubuntu

# 验证安装
docker --version
docker-compose --version
java -version
mvn -version
```

### 3.2 克隆代码
```bash
mkdir -p /opt/zhihealth && cd /opt/zhihealth

# 方式A：从GitHub克隆
git clone https://github.com/yourusername/zhihealth.git .

# 方式B：上传本地代码（使用scp或FTP）
# 将本地 e:\Health 整个目录上传到此位置
```

### 3.3 构建后端项目
```bash
cd zhihealth-cloud

# Maven构建（跳过测试，约10分钟）
mvn clean package -DskipTests

# 查看生成的JAR包
ls -lh */target/*.jar
```

### 3.4 构建Docker镜像
```bash
cd docker

# 构建基础设施镜像
docker-compose -f docker-compose.infra.yml build

# 构建微服务镜像
docker-compose -f docker-compose.services.yml build

# 查看构建完成的镜像
docker images | grep zhihealth
```

### 3.5 配置环境变量
```bash
cat > .env << 'EOF'
MYSQL_PASSWORD=ZhiHealth_2024_Production
REDIS_PASSWORD=zhihealth_redis_2024
INFLUX_PASSWORD=ZhiHealth_Influx_2024
NACOS_PASSWORD=nacos
EOF

# 设置权限
chmod 600 .env
```

### 3.6 启动所有服务
```bash
# 使用生产环境配置启动
docker-compose -f docker-compose.infra.yml \
              -f docker-compose.services.yml \
              -f docker-compose.prod.yml \
              up -d

# 查看启动日志
docker-compose logs -f

# 等待所有服务健康（约60-90秒）
watch -n 5 'docker ps --format "table {{.Names}}\t{{.Status}}"'
```

### 3.7 初始化数据库
```bash
# 如果MySQL自动初始化失败，手动执行
docker exec -i zhihealth-mysql mysql -u root -p'ZhiHealth_2024_Production' < ../sql/init.sql

# 创建测试用户（通过API注册）
curl -X POST http://localhost:8081/user/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123456","nickname":"管理员"}'
```

---

## 4️⃣ 本地迁移到云端

### 方法A：导出/导入镜像（推荐用于离线环境）

**在本地电脑执行：**
```bash
# 1. 导出所有zhihealth镜像
docker save $(docker images --format '{{.Repository}}:{{.Tag}}' | grep zhihealth) | gzip > zhihealth-images.tar.gz

# 2. 导出数据卷（可选，如果本地有重要数据）
docker run --rm -v zhihealth-mysql-data:/data alpine tar czf /backup/mysql-data.tar.gz -C /data .
docker run --rm -v zhihealth-redis-data:/data alpine tar czf /backup/redis-data.tar.gz -C /data .

# 3. 上传到云服务器
scp zhihealth-images.tar.gz root@服务器IP:/opt/
scp mysql-data.tar.gz redis-data.tar.gz root@服务器IP:/opt/  # 可选
```

**在云服务器上执行：**
```bash
# 1. 导入镜像
gunzip -c zhihealth-images.tar.gz | docker load

# 2. 恢复数据卷（可选）
docker run --rm -v zhihealth-mysql-data:/data -v /opt:/backup alpine tar xzf /backup/mysql-data.tar.gz -C /data

# 3. 启动服务
cd /opt/zhihealth/docker
docker-compose up -d
```

### 方法B：在云服务器重新构建（推荐用于在线环境）

直接按照第3节的步骤在云服务器上重新构建即可。

---

## 5️⃣ 常见问题解决

### Q1: Docker容器启动失败？
```bash
# 查看容器日志
docker logs 容器名

# 常见原因及解决方案：
# - 端口被占用: lsof -i :端口号 && kill -9 PID
# - 内存不足: free -h && docker system prune -a
# - 权限问题: sudo usermod -aG docker $USER （需重新登录）
```

### Q2: 微服务连接不上MySQL/Redis？
```bash
# 检查网络
docker network ls
docker network inspect zhihealth_zhihealth-network

# 测试连通性
docker exec zhihealth-user ping zhihealth-mysql
docker exec zhihealth-user ping zhihealth-redis
```

### Q3: CPU/内存占用过高？
```bash
# 查看资源占用
docker stats --no-stream

# 限制容器资源（编辑docker-compose.prod.yml中的deploy.resources.limits）
docker-compose up -d --force-recreate

# 清理无用资源
docker system prune -a  # ⚠️ 会删除未使用的镜像
```

### Q4: 如何更新版本？
```bash
# 1. 拉取新代码
cd /opt/zhihealth
git pull origin main

# 2. 重新构建
cd zhihealth-cloud
mvn clean package -DskipTests

# 3. 重启相关服务
cd ../docker
docker-compose build 服务名
docker-compose up -d 服务名

# 示例：只更新user服务
docker-compose build user-service
docker-compose up -d user-service
```

### Q5: 数据备份与恢复？
```bash
# 备份MySQL
docker exec zhihealth-mysql mysqldump -u root -p'密码' --all-databases > backup_$(date +%Y%m%d).sql

# 备份Redis
docker exec zhihealth-redis redis-cli BGSAVE
cp /var/lib/docker/volumes/zhihealth_redis_data/_data/dump.rdb ./redis-backup.rdb

# 恢复
docker exec -i zhihealth-mysql mysql -u root -p'密码' < backup_20260605.sql
```

---

## 6️⃣ 运维管理命令速查

### 日常监控
```bash
# 查看所有服务状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 实时查看日志
docker logs -f --tail 100 zhihealth-gateway

# 查看资源使用
docker stats --no-stream

# 进入容器调试
docker exec -it zhihealth-user bash
```

### 服务管理
```bash
# 重启单个服务
docker restart zhihealth-user

# 重启所有服务
cd /opt/zhihealth/docker && docker-compose restart

# 停止所有服务
docker-compose down

# 停止并删除数据（⚠️ 危险操作）
docker-compose down -v
```

### 性能优化
```bash
# 查看慢查询
docker exec zhihealth-mysql mysql -e "SHOW PROCESSLIST;"

# Redis内存分析
docker exec zhihealth-redis redis-cli INFO memory

# JVM堆信息（Java服务）
docker exec zhihealth-gateway curl localhost:8080/actuator/info
```

### 安全加固
```bash
# 修改默认端口（编辑docker-compose.prod.yml）
# 启用HTTPS（准备SSL证书）
# 配置防火墙
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload
```

---

## 📞 技术支持

遇到问题时的排查顺序：
1. **查看日志**: `docker logs 服务名`
2. **检查网络**: `docker network inspect`
3. **检查资源**: `docker stats` 和 `free -h`
4. **重启服务**: `docker restart`
5. **查看文档**: 本项目的 README.md

**祝部署顺利！** 🚀
