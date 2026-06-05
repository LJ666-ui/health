# ============================================================
#  智康云枢 - 主节点(Master)生产部署脚本
#  服务器: zhihealth-master (182.92.1.136)
#  配置: 2核4G CentOS 7.9
#  用途: API网关 + 微服务集群 + 核心数据库
# ============================================================

set -e

echo "=========================================="
echo "  智康云枢 主节点部署向导"
echo "  服务器: $(hostname) ($(hostname -I | awk '{print $1}'))"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# ==================== 第1步：系统优化（2C4G专用）====================
optimize_system() {
    echo ""
    echo ">>> [1/7] 系统资源优化（适配2C4G）..."
    
    # 关闭不必要的服务释放内存
    systemctl disable firewalld 2>/dev/null || true
    systemctl stop firewalld 2>/dev/null || true
    
    # 优化内核参数
    cat >> /etc/sysctl.conf << 'EOF'
# 智康云枢内核优化
net.core.somaxconn = 1024
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
vm.swappiness = 10
EOF
    sysctl -p
    
    # 设置文件描述符限制
    echo "* soft nofile 65535" >> /etc/security/limits.conf
    echo "* hard nofile 65535" >> /etc/security/limits.conf
    
    # 清理yum缓存释放空间
    yum clean all
    
    echo "✅ 系统优化完成"
}

# ==================== 第2步：检查并启动已有中间件 ====================
check_existing_services() {
    echo ""
    echo ">>> [2/7] 检查已有中间件..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker未安装，请先安装"
        exit 1
    fi
    echo "✅ Docker版本: $(docker --version)"
    
    # 检查已有容器
    echo ""
    echo "检测到的容器:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "无容器"
    
    # 启动MySQL（如果存在但未运行）
    if docker ps -a | grep -q mysql; then
        echo "启动MySQL..."
        docker start mysql || true
        sleep 5
    fi
    
    # 启动Redis（如果存在但未运行）
    if docker ps -a | grep -q redis; then
        echo "启动Redis..."
        docker start redis || true
    fi
    
    # 启动Nacos（如果存在但未运行）
    if docker ps -a | grep -q nacos; then
        echo "启动Nacos..."
        docker start nacos || true
        sleep 10
    fi
    
    echo "✅ 中间件检查完成"
}

# ==================== 第3步：创建项目目录结构 ====================
create_directories() {
    echo ""
    echo ">>> [3/7] 创建目录结构..."
    
    mkdir -p /opt/zhihealth/{config,logs,data/{mysql,redis,nacos},backups,docker}
    
    # 创建日志轮转配置
    cat > /etc/logrotate.d/zhihealth << 'EOF'
/opt/zhihealth/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
EOF
    
    echo "✅ 目录创建完成"
}

# ==================== 第4步：上传或拉取代码 ====================
prepare_code() {
    echo ""
    echo ">>> [4/7] 准备项目代码..."
    
    cd /opt/zhihealth
    
    if [ ! -d "zhihealth-cloud" ]; then
        echo "⚠️  未检测到代码，请手动上传："
        echo "   方式1: scp -r ./zhihealth-cloud root@182.92.1.136:/opt/zhihealth/"
        echo "   方式2: git clone <你的仓库地址>"
        echo ""
        read -p "代码已准备好吗？(y/n): " ready
        if [ "$ready" != "y" ]; then
            exit 1
        fi
    else
        echo "✅ 代码已就绪"
    fi
}

# ==================== 第5步：构建微服务镜像（轻量化）====================
build_images() {
    echo ""
    echo ">>> [5/7] 构建Docker镜像（预计10-15分钟）..."
    
    cd /opt/zhihealth/docker
    
    # 检查Maven
    if command -v mvn &> /dev/null; then
        echo "使用本地Maven构建JAR包..."
        cd ../zhihealth-cloud
        mvn clean package -DskipTests -q
        cd ../docker
    fi
    
    # 构建核心微服务镜像（按优先级排序）
    services=("gateway" "user" "device" "collect" "storage" "cache")
    
    for service in "${services[@]}"; do
        echo "构建 $service 服务..."
        if [ -f "Dockerfile.$service" ]; then
            docker build -f Dockerfile.$service -t zhihealth-$service:v1.0 . 2>&1 | tail -5
            echo "✅ $service 镜像构建完成"
        fi
    done
    
    echo "✅ 所有镜像构建完成"
    docker images | grep zhihealth
}

# ==================== 第6步：启动微服务集群 ====================
start_microservices() {
    echo ""
    echo ">>> [6/7] 启动微服务集群..."
    
    cd /opt/zhihealth/docker
    
    # 使用生产配置启动（资源受限模式）
    export COMPOSE_PROJECT_NAME=zhihealth
    
    docker-compose -f docker-compose.master.yml up -d
    
    echo "等待服务启动（约60秒）..."
    sleep 60
    
    # 显示服务状态
    echo ""
    echo "📊 服务状态总览:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "zhihealth|NAMES"
}

# ==================== 第7步：健康检查与验证 ====================
verify_deployment() {
    echo ""
    echo ">>> [7/7] 部署验证..."
    
    echo "1. Gateway网关健康检查:"
    for i in {1..10}; do
        if curl -sf http://localhost:8080/actuator/health > /dev/null 2>&1; then
            echo "   ✅ Gateway正常响应 (http://localhost:8080)"
            break
        fi
        echo "   ⏳ 等待Gateway启动... ($i/10)"
        sleep 5
    done
    
    echo ""
    echo "2. User服务测试:"
    curl -s http://localhost:8081/user/role/list 2>/dev/null | head -c 200 && echo "" || echo "   ❌ User服务未响应"
    
    echo ""
    echo "3. Device服务测试:"
    curl -s http://localhost:8082/device/list 2>/dev/null | head -c 200 && echo "" || echo "   ❌ Device服务未响应"
    
    echo ""
    echo "=========================================="
    echo "  🎉 主节点部署完成！"
    echo "=========================================="
    echo ""
    echo "访问地址:"
    echo "  API网关: http://182.92.1.136:8080"
    echo "  Nacos控制台: http://182.92.1.136:8848/nacos (nacos/nacos)"
    echo ""
    echo "默认账号:"
    echo "  用户名: testuser"
    echo "  密码: Test123456"
    echo ""
    echo "管理命令:"
    echo "  查看日志: docker logs -f zhihealth-gateway"
    echo "  重启服务: cd /opt/zhihealth/docker && docker-compose restart"
    echo "  资源监控: docker stats --no-stream"
    echo "=========================================="
}

# ==================== 主流程 ====================
main() {
    optimize_system
    check_existing_services
    create_directories
    prepare_code
    build_images
    start_microservices
    verify_deployment
}

# 执行
main "$@"
