#!/bin/bash
# ============================================================
#  智康云枢 - 从节点(Slave)一键部署脚本 (Git版)
#  用途: 克隆代码 + Maven构建 + 启动微服务集群 + 数据存储
#  适用: CentOS 7.9 / 2核8G服务器
#
#  部署内容：
#    - InfluxDB (时序数据库)
#    - MongoDB (文档数据库)
#    - 9个业务微服务 (User/Device/Collect/Storage/Cache/Alert/Report/Log/AI)
#    - 前端Nginx
#
#  依赖：主节点(182.92.1.136) 的 MySQL/Redis/Nacos/RabbitMQ/Gateway
# ============================================================

set -e

MASTER_IP="182.92.1.136"
GIT_REPO="https://github.com/LJ666-ui/health.git"
BRANCH="main"

echo "╔══════════════════════════════════════════════════════╗"
echo "║   智康云枢 从节点 一键部署向导 (2核8G版)           ║"
echo "║   Server: $(hostname) ($(hostname -I | awk '{print $1}'))              ║"
echo "║   Time: $(date '+%Y-%m-%d %H:%M:%S')                    ║"
echo "╚══════════════════════════════════════════════════════╝"

# 检查root权限
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 root 用户执行: sudo bash $0"
    exit 1
fi

# ==================== 第1步：环境准备 ====================
prepare_env() {
    echo ""
    echo ">>> [1/6] 环境检查与准备..."

    # 安装基础工具
    yum install -y git wget curl unzip docker docker-compose -q 2>/dev/null || true

    # 启动Docker
    systemctl enable docker 2>/dev/null || true
    systemctl start docker 2>/dev/null || true

    # 关闭防火墙（内网环境）
    systemctl disable firewalld 2>/dev/null || true
    systemctl stop firewalld 2>/dev/null || true

    # 文件描述符限制
    grep -q "65535" /etc/security/limits.conf 2>/dev/null || \
        echo "* soft nofile 65535" >> /etc/security/limits.conf
    grep -q "65535" /etc/security/limits.conf 2>/dev/null || \
        echo "* hard nofile 65535" >> /etc/security/limits.conf

    # 创建目录
    mkdir -p /opt/zhihealth/{data,logs,backups,config}

    # Docker镜像加速（国内）
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json << 'DOCEOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
}
DOCEOF
    systemctl restart docker 2>/dev/null || true

    echo "✅ 环境准备完成"
}

# ==================== 第2步：克隆代码 ====================
clone_code() {
    echo ""
    echo ">>> [2/6] 克隆项目代码..."

    cd /opt

    if [ -d "/opt/zhihealth/.git" ]; then
        echo "检测到已有代码，执行更新..."
        cd /opt/zhihealth && git pull origin $BRANCH
    else
        if command -v git &> /dev/null; then
            echo "正在克隆: $GIT_REPO"
            rm -rf /opt/zhihealth
            git clone --depth 1 -b $BRANCH $GIT_REPO /opt/zhihealth
        else
            echo "❌ Git未安装"
            exit 1
        fi
    fi

    # 验证关键文件
    if [ ! -f "/opt/zhihealth/deploy/docker-compose.slave.yml" ]; then
        echo "❌ 未找到 docker-compose.slave.yml"
        exit 1
    fi

    echo "✅ 代码就绪 ($(find /opt/zhihealth -type f | wc -l) 个文件)"
}

# ==================== 第3步：网络测试 ====================
test_network() {
    echo ""
    echo ">>> [3/6] 测试主节点连通性..."

    local MASTER_OK=false

    # Ping测试
    if ping -c 3 -W 2 $MASTER_IP > /dev/null 2>&1; then
        echo "  ✅ Ping通主节点 ($MASTER_IP)"
        MASTER_OK=true
    else
        echo "  ⚠️ Ping不通，尝试端口连通..."
    fi

    # 端口连通性测试
    for PORT in 3306 6379 5672 8848 8080; do
        if timeout 3 bash -c "echo >/dev/tcp/$MASTER_IP/$PORT" 2>/dev/null; then
            case $PORT in
                3306) echo "  ✅ MySQL     ($MASTER_IP:$PORT)" ;;
                6379) echo "  ✅ Redis     ($MASTER_IP:$PORT)" ;;
                5672) echo "  ✅ RabbitMQ  ($MASTER_IP:$PORT)" ;;
                8848) echo "  ✅ Nacos     ($MASTER_IP:$PORT)" ;;
                8080) echo "  ✅ Gateway   ($MASTER_IP:$PORT)" ;;
            esac
        else
            case $PORT in
                3306) echo "  ⏳ MySQL     ($MASTER_IP:$PORT) - 可能未启动" ;;
                6379) echo "  ⏳ Redis     ($MASTER_IP:$PORT) - 可能未启动" ;;
                5672) echo "  ⏳ RabbitMQ  ($MASTER_IP:$PORT) - 可能未启动" ;;
                8848) echo "  ⏳ Nacos     ($MASTER_IP:$PORT) - 可能未启动" ;;
                8080) echo "  ⏳ Gateway   ($MASTER_IP:$PORT) - 可能未启动" ;;
            esac
        fi
    done

    echo "✅ 网络测试完成"
}

# ==================== 第4步：Maven构建JAR包 ====================
build_jars() {
    echo ""
    echo ">>> [4/6] 构建后端JAR包 (Docker Maven构建)..."

    cd /opt/zhihealth

    if [ -f "zhihealth-cloud/pom.xml" ]; then
        # 使用Docker容器内Maven构建（和主节点一样的方案）
        echo "使用Docker Maven构建 (maven:3.9-eclipse-temurin-17)..."
        docker run --rm \
            -v "$(pwd)/zhihealth-cloud":/usr/src/maven \
            -w /usr/src/maven \
            maven:3.9-eclipse-temurin-17 \
            mvn clean package -DskipTests -q

        JAR_COUNT=$(find zhihealth-cloud -name "*.jar" -path "*/target/*" ! -name "*sources.jar" | wc -l)
        echo "✅ 构建完成，生成 $JAR_COUNT 个JAR文件"
    else
        echo "⚠️  未找到pom.xml，跳过构建（可能使用预编译JAR）"
    fi
}

# ==================== 第5步：创建配置文件 ====================
prepare_config() {
    echo ""
    echo ">>> [5/6] 准备部署配置..."

    cd /opt/zhihealth/deploy

    # 创建环境变量文件
    cat > .env << EOF
MASTER_IP=${MASTER_IP}
MYSQL_PASSWORD=root_2024_zhihealth
REDIS_PASSWORD=zhihealth_redis_2024
INFLUX_PASSWORD=admin123456
MONGO_PASSWORD=mongo123456
EOF

    # 创建MongoDB初始化脚本
    mkdir -p config
    cat > config/mongo-init.js << 'MONGOF'
db = db.getSiblingDB('zhihealth_storage');
db.createCollection('health_records');
db.createCollection('device_data');
db.createCollection('log_entries');
print('MongoDB初始化完成');
MONGOF

    # 创建Nginx配置（代理到主节点Gateway）
    mkdir -p config
    cat > config/nginx.slave.conf << 'NGINXEOF'
worker_processes auto;
events { worker_connections 1024; }
http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;

    server {
        listen       80;
        server_name  _;

        # 前端静态文件
        location / {
            root   /usr/share/nginx/html;
            index  index.html index.htm;
            try_files \$uri \$uri/ /index.html;
        }

        # API反向代理到主节点Gateway
        location /api/ {
            proxy_pass http://${MASTER_IP}:8080/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        }
    }
}
NGINXEOF

    # 替换nginx.conf中的变量
    sed -i "s/\${MASTER_IP}/${MASTER_IP}/g" config/nginx.slave.conf

    echo "✅ 配置文件已生成"
}

# ==================== 第6步：启动所有服务 ====================
start_services() {
    echo ""
    echo ">>> [6/6] 启动所有服务..."

    cd /opt/zhihealth/deploy

    # 先启动数据存储服务
    echo "[1/3] 启动 InfluxDB + MongoDB..."
    docker-compose -f docker-compose.slave.yml up -d influxdb mongodb
    sleep 15

    # 再启动微服务集群
    echo "[2/3] 启动 9个微服务 + Nginx..."
    docker-compose -f docker-compose.slave.yml up -d \
        user-service device-service collect-service storage-service \
        cache-service alert-service report-service log-service \
        ai-service nginx

    echo ""
    echo "等待服务初始化 (90秒)..."
    sleep 90
}

# ==================== 验证部署 ====================
verify() {
    echo ""
    echo ">>> 部署验证"
    echo ""

    echo "==========================================="
    echo "  容器状态:"
    echo "==========================================="
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20

    echo ""
    echo "==========================================="
    echo "  健康检查:"
    echo "==========================================="

    # 本地服务检查
    for SVC in "InfluxDB:8086" "MongoDB:27017"; do
        NAME=$(echo $SVC | cut -d: -f1)
        PORT=$(echo $SVC | cut -d: -f2)
        if timeout 3 bash -c "echo >/dev/tcp/localhost/$PORT" 2>/dev/null; then
            echo "  ✅ $NAME (localhost:$PORT)"
        else
            echo "  ⏳ $NAME 启动中... (localhost:$PORT)"
        fi
    done

    # 微服务检查
    for PORT in 8081 8082 8083 8084 8085 8087 8089 8090 8091; do
        if timeout 3 bash -c "echo >/dev/tcp/localhost/$PORT" 2>/dev/null; then
            case $PORT in
                8081) echo "  ✅ User Service    (:8081)" ;;
                8082) echo "  ✅ Device Service  (:8082)" ;;
                8083) echo "  ✅ Collect Service (:8083)" ;;
                8084) echo "  ✅ Storage Service (:8084)" ;;
                8085) echo "  ✅ Cache Service   (:8085)" ;;
                8087) echo "  ✅ AI Service      (:8087)" ;;
                8089) echo "  ✅ Log Service     (:8089)" ;;
                8090) echo "  ✅ Alert Service   (:8090)" ;;
                8091) echo "  ✅ Report Service  (:8091)" ;;
            esac
        else
            case $PORT in
                8081) echo "  ⏳ User Service    (:8081) 启动中..." ;;
                8082) echo "  ⏳ Device Service  (:8082) 启动中..." ;;
                8083) echo "  ⏳ Collect Service (:8083) 启动中..." ;;
                8084) echo "  ⏳ Storage Service (:8084) 启动中..." ;;
                8085) echo "  ⏳ Cache Service   (:8085) 启动中..." ;;
                8087) echo "  ⏳ AI Service      (:8087) 启动中..." ;;
                8089) echo "  ⏳ Log Service     (:8089) 启动中..." ;;
                8090) echo "  ⏳ Alert Service   (:8090) 启动中..." ;;
                8091) echo "  ⏳ Report Service  (:8091) 启动中..." ;;
            esac
        fi
    done

    # 前端
    if timeout 3 bash -c "echo >/dev/tcp/localhost/80" 2>/dev/null; then
        echo "  ✅ Frontend Nginx  (:80)"
    else
        echo "  ⏳ Frontend Nginx  (:80) 启动中..."
    fi

    SLAVE_IP=$(hostname -I | awk '{print $1}')

    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  🎉 从节点部署完成！                                ║"
    echo "╠══════════════════════════════════════════════════════╣"
    echo "║  本机地址:                                          ║"
    echo "║  • 前端界面: http://$SLAVE_IP                        ║"
    echo "║  • InfluxDB: http://$SLAVE_IP:8086                  ║"
    echo "║  • MongoDB:  $SLAVE_IP:27017                         ║"
    echo "╠══════════════════════════════════════════════════════╣"
    echo "║  主节点地址 (基础设施):                              ║"
    echo "║  • Gateway:  http://$MASTER_IP:8080                 ║"
    echo "║  • Nacos:    http://$MASTER_IP:8848/nacos           ║"
    echo "╠══════════════════════════════════════════════════════╣"
    echo "║  默认账号: testuser / Test123456                   ║"
    echo "╠══════════════════════════════════════════════════════╣"
    echo "║  常用命令:                                           ║"
    echo "║  • 查看日志: docker logs -f zhihealth-user         ║"
    echo "║  • 重启全部: cd /opt/zhihealth/deploy               ║"
    echo "║             && docker-compose -f docker-compose.slave.yml restart ║"
    echo "║  • 资源监控: docker stats --no-stream              ║"
    echo "║  • 停止服务: docker-compose -f docker-compose.slave.yml down ║"
    echo "╚══════════════════════════════════════════════════════╝"
}

# ==================== 主流程 ====================
main() {
    prepare_env
    clone_code
    test_network
    build_jars
    prepare_config
    start_services
    verify
}

main "$@"
