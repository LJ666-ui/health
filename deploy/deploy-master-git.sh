#!/bin/bash
# ============================================================
#  智康云枢 - 主节点(Master)一键部署脚本 (Git版)
#  用途: 自动克隆代码 + 构建镜像 + 启动所有服务
#  适用: CentOS 7.9 / 2核4G服务器
# ============================================================

set -e

# ==================== 配置区 ====================
GIT_REPO="${1:-https://gitee.com/yourusername/zhihealth.git}"  # 替换为你的仓库地址
BRANCH="${2:-main}"
MYSQL_PASSWORD="root_2024_zhihealth"
REDIS_PASSWORD="zhihealth_redis_2024"
SLAVE_IP="39.105.57.155"

echo "╔══════════════════════════════════════════════════╗"
echo "║     智康云枢 主节点 一键部署向导 (Git版)        ║"
echo "║     Server: $(hostname) ($(hostname -I | awk '{print $1}'))    ║"
echo "║     Time: $(date '+%Y-%m-%d %H:%M:%S')              ║"
echo "╚══════════════════════════════════════════════════╝"

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 root 用户执行: sudo bash $0"
    exit 1
fi

# ==================== 第1步：环境准备 ====================
prepare_env() {
    echo ""
    echo ">>> [1/6] 环境检查与优化..."
    
    # 安装基础工具
    yum update -y -q 2>/dev/null || true
    yum install -y git wget curl unzip java-17-openjdk-devel maven -q
    
    # 系统优化
    systemctl disable firewalld 2>/dev/null || true
    systemctl stop firewalld 2>/dev/null || true
    
    # 文件描述符限制
    echo "* soft nofile 65535" >> /etc/security/limits.conf 2>/dev/null || true
    echo "* hard nofile 65535" >> /etc/security/limits.conf 2>/dev/null || true
    
    # 创建目录
    mkdir -p /opt/zhihealth/{logs,data,backups}
    
    echo "✅ 环境准备完成"
}

# ==================== 第2步：克隆代码 ====================
clone_code() {
    echo ""
    echo ">>> [2/6] 克隆项目代码..."
    cd /opt/zhihealth
    
    if [ -d ".git" ]; then
        echo "检测到已有代码，执行更新..."
        git pull origin $BRANCH
    else
        if command -v git &> /dev/null; then
            echo "正在克隆: $GIT_REPO"
            git clone --depth 1 -b $BRANCH $GIT_REPO .
        else
            echo "❌ Git未安装"
            exit 1
        fi
    fi
    
    echo "✅ 代码就绪"
}

# ==================== 第3步：构建JAR包 ====================
build_jars() {
    echo ""
    echo ">>> [3/6] 构建后端JAR包 (预计5-10分钟)..."
    
    cd /opt/zhihealth/zhihealth-cloud
    
    if [ -f "pom.xml" ]; then
        echo "Maven构建中..."
        mvn clean package -DskipTests -q
        
        # 验证构建结果
        JAR_COUNT=$(find . -name "*.jar" -path "*/target/*" ! -name "*sources.jar" | wc -l)
        echo "✅ 构建完成，生成 $JAR_COUNT 个JAR文件"
    else
        echo "⚠️  未找到pom.xml，跳过构建（可能使用预编译JAR）"
    fi
}

# ==================== 第4步：启动基础设施 ====================
start_infra() {
    echo ""
    echo ">>> [4/6] 启动基础设施服务..."
    
    # 启动MySQL（如果容器存在）
    if docker ps -a | grep -q "mysql\|zhihealth-mysql"; then
        echo "启动 MySQL..."
        docker start $(docker ps -a | grep mysql | awk '{print $1}') 2>/dev/null || true
        sleep 8
    else
        echo "创建 MySQL 容器..."
        docker run -d \
            --name zhihealth-mysql \
            --restart always \
            -p 3306:3306 \
            -e MYSQL_ROOT_PASSWORD=$MYSQL_PASSWORD \
            -v zhihealth_mysql_data:/var/lib/mysql \
            mysql:8.0 \
            --character-set-server=utf8mb4 \
            --collation-server=utf8mb4_unicode_ci \
            --max-connections=200 \
            --innodb-buffer-pool-size=512M
        sleep 10
    fi
    
    # 启动Redis
    if docker ps -a | grep -q "redis\|zhihealth-redis"; then
        echo "启动 Redis..."
        docker start $(docker ps -a | grep redis | awk '{print $1}') 2>/dev/null || true
    else
        echo "创建 Redis 容器..."
        docker run -d \
            --name zhihealth-redis \
            --restart always \
            -p 6379:6379 \
            redis:7-alpine \
            redis-server --requirepass $REDIS_PASSWORD --maxmemory 256mb --maxmemory-policy allkeys-lru
    fi
    
    # 启动Nacos
    if docker ps -a | grep -q "nacos\|zhihealth-nacos"; then
        echo "启动 Nacos..."
        docker start $(docker ps -a | grep nacos | awk '{print $1}') 2>/dev/null || true
        sleep 15
    else
        echo "创建 Nacos 容器..."
        docker run -d \
            --name zhihealth-nacos \
            --restart always \
            -p 8848:8848 -p 9848:9848 -p 9849:9849 \
            -e MODE=standalone \
            -e JVM_XMS=256m -e JVM_XMX=512m -e JVM_XMN=128m \
            nacos/nacos-server:v2.2.3
        sleep 15
    fi
    
    echo "✅ 基础设施启动完成"
}

# ==================== 第5步：构建并启动微服务 ====================
start_microservices() {
    echo ""
    echo ">>> [5/6] 构建并启动微服务集群..."
    
    cd /opt/zhihealth/deploy
    
    # 创建环境变量文件
    cat > .env << EOF
MYSQL_PASSWORD=$MYSQL_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
INFLUX_PASSWORD=admin123456
MONGO_PASSWORD=mongo123456
SLAVE_IP=$SLAVE_IP
EOF
    
    # 构建Docker镜像
    echo "构建Docker镜像..."
    for service in gateway user device collect storage cache alert report log ai; do
        if [ -f "Dockerfile.$service" ]; then
            echo "  构建 $service ..."
            docker build -f Dockerfile.$service -t zhihealth-$service:v1.0 . -q 2>/dev/null || true
        fi
    done
    
    # 启动所有服务
    echo "启动所有容器..."
    docker-compose -f docker-compose.master.yml up -d
    
    echo "等待服务初始化 (60秒)..."
    sleep 60
}

# ==================== 第6步：验证部署 ====================
verify() {
    echo ""
    echo ">>> [6/6] 部署验证..."
    
    echo ""
    echo "==========================================="
    echo "  服务状态总览:"
    echo "==========================================="
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20
    
    echo ""
    echo "健康检查:"
    
    # Gateway
    if curl -sf http://localhost:8080/actuator/health > /dev/null 2>&1; then
        echo "  ✅ Gateway (http://localhost:8080)"
    else
        echo "  ⏳ Gateway 启动中..."
    fi
    
    # User Service
    if curl -sf http://localhost:8081/user/role/list > /dev/null 2>&1; then
        echo "  ✅ User Service (http://localhost:8081)"
    else
        echo "  ⏳ User Service 启动中..."
    fi
    
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║  🎉 主节点部署完成！                            ║"
    echo "╠══════════════════════════════════════════════════╣"
    echo "║  访问地址:                                       ║"
    echo "║  • 前端界面: http://$(hostname -I | awk '{print $1}')          ║"
    echo "║  • API网关: http://$(hostname -I | awk '{print $1}'):8080       ║"
    echo "║  • Nacos:   http://$(hostname -I | awk '{print $1}'):8848/nacos ║"
    echo "╠══════════════════════════════════════════════════╣"
    echo "║  默认账号: testuser / Test123456               ║"
    echo "╠══════════════════════════════════════════════════╣"
    echo "║  常用命令:                                       ║"
    echo "║  • 查看日志: docker logs -f zhihealth-gateway   ║"
    echo "║  • 重启服务: cd /opt/zhihealth/deploy && docker-compose restart ║"
    echo "║  • 资源监控: docker stats --no-stream           ║"
    echo "╚══════════════════════════════════════════════════╝"
}

# ==================== 主流程 ====================
main() {
    prepare_env
    clone_code
    build_jars
    start_infra
    start_microservices
    verify
}

main "$@"
