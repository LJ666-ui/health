# ============================================================
#  智康云枢 - 云服务器一键部署脚本
#  版本: v1.0
#  适用: CentOS 7.9+ / Ubuntu 20.04+
#  用法: bash deploy-cloud.sh [主服务器IP] [大数据服务器IP]
# ============================================================

set -e

# ==================== 配置区 ====================
MAIN_SERVER_IP="${1:-your-main-server-ip}"
BIGDATA_SERVER_IP="${2:-your-bigdata-server-ip}"

MYSQL_PASSWORD="ZhiHealth_2024_Production"
REDIS_PASSWORD=""
NACOS_PASSWORD="nacos"

echo "=========================================="
echo "  智康云枢 云服务器部署向导"
echo "  主服务器: $MAIN_SERVER_IP"
echo "  大数据服务器: ${BIGDATA_SERVER_IP:-未配置}"
echo "=========================================="

# ==================== 第1步：环境准备 ====================
prepare_environment() {
    echo ""
    echo ">>> [1/6] 安装基础环境..."
    
    # 更新系统
    sudo yum update -y || sudo apt update && sudo apt upgrade -y
    
    # 安装Docker
    if ! command -v docker &> /dev/null; then
        echo "安装Docker..."
        curl -fsSL https://get.docker.com | sh
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        echo "✅ Docker安装完成: $(docker --version)"
    else
        echo "✅ Docker已存在: $(docker --version)"
    fi
    
    # 安装Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "安装Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        echo "✅ Docker Compose安装完成"
    fi
    
    # 创建项目目录
    sudo mkdir -p /opt/zhihealth/{config,logs,data/{mysql,redis,mongodb,influxdb,hadoop,hive},backups}
    cd /opt/zhihealth
    
    echo "✅ 环境准备完成"
}

# ==================== 第2步：传输代码 ====================
transfer_code() {
    echo ""
    echo ">>> [2/6] 传输项目代码..."
    
    # 方式A：从GitHub克隆（推荐）
    read -p "请输入Git仓库地址（留空跳过）: " GIT_REPO
    if [ -n "$GIT_REPO" ]; then
        git clone $GIT_REPO .
        echo "✅ 代码克隆完成"
    else
        echo "⚠️  请手动上传代码到 /opt/zhihealth/"
        echo "   需要的文件："
        echo "   - zhihealth-cloud/ (后端代码)"
        echo "   - zhihealth-frontend/ (前端代码)"
        echo "   - docker/ (Docker配置)"
        exit 1
    fi
}

# ==================== 第3步：构建镜像 ====================
build_images() {
    echo ""
    echo ">>> [3/6] 构建Docker镜像（预计15-20分钟）..."
    
    # 检查Maven
    if ! command -v mvn &> /dev/null; then
        echo "安装Maven..."
        sudo yum install -y maven || sudo apt install -y maven
    fi
    
    # 构建后端JAR包
    cd zhihealth-cloud
    mvn clean package -DskipTests -q
    echo "✅ Maven构建完成"
    
    # 构建所有微服务镜像
    cd docker
    docker-compose -f docker-compose.infra.yml build
    docker-compose -f docker-compose.services.yml build
    echo "✅ 所有镜像构建完成"
    
    docker images | grep zhihealth
}

# ==================== 第4步：初始化数据库 ====================
init_database() {
    echo ""
    echo ">>> [4/6] 初始化数据库..."
    
    # 启动MySQL容器
    docker run -d \
        --name zhihealth-mysql \
        -p 3306:3306 \
        -e MYSQL_ROOT_PASSWORD=$MYSQL_PASSWORD \
        -v /opt/zhihealth/data/mysql:/var/lib/mysql \
        mysql:8.0 \
        --character-set-server=utf8mb4 \
        --collation-server=utf8mb4_unicode_ci
    
    sleep 10
    
    # 初始化数据库表结构
    docker exec -i zhihealth-mysql mysql -u root -p$MYSQL_PASSWORD < ../sql/init.sql
    echo "✅ 数据库初始化完成"
    
    # 显示创建的数据库
    docker exec zhihealth-mysql mysql -u root -p$MYSQL_PASSWORD -e "SHOW DATABASES LIKE 'zhihealth%';"
}

# ==================== 第5步：启动所有服务 ====================
start_services() {
    echo ""
    echo ">>> [5/6] 启动所有微服务..."
    
    # 使用生产环境配置启动
    docker-compose -f docker-compose.infra.yml \
                  -f docker-compose.services.yml \
                  -f docker-compose.prod.yml \
                  up -d
    
    echo "等待服务启动（约60秒）..."
    sleep 60
    
    # 检查服务状态
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep zhihealth
}

# ==================== 第6步：验证部署 ====================
verify_deployment() {
    echo ""
    echo ">>> [6/6] 验证部署结果..."
    
    echo "1. 检查Gateway健康状态:"
    curl -s http://localhost:8080/actuator/health | python3 -m json.tool || echo "❌ Gateway未响应"
    
    echo ""
    echo "2. 检查User服务:"
    curl -s http://localhost:8081/user/role/list | python3 -m json.tool || echo "❌ User服务未响应"
    
    echo ""
    echo "3. 检查Device服务:"
    curl -s http://localhost:8082/device/list | python3 -m json.tool || echo "❌ Device服务未响应"
    
    echo ""
    echo "=========================================="
    echo "  🎉 部署完成！"
    echo "=========================================="
    echo ""
    echo "访问地址:"
    echo "  前端界面: http://$MAIN_SERVER_IP:80 (或配置Nginx后80端口)"
    echo "  API网关: http://$MAIN_SERVER_IP:8080"
    echo "  Nacos控制台: http://$MAIN_SERVER_IP:8848/nacos (nacos/nacos)"
    echo ""
    echo "默认账号:"
    echo "  用户名: testuser"
    echo "  密码: Test123456"
    echo ""
    echo "管理命令:"
    echo "  查看日志: docker logs -f zhihealth-gateway"
    echo "  重启服务: cd /opt/zhihealth/docker && docker-compose restart"
    echo "  停止服务: cd /opt/zhihealth/docker && docker-compose down"
    echo "=========================================="
}

# ==================== 主流程 ====================
main() {
    prepare_environment
    transfer_code
    build_images
    init_database
    start_services
    verify_deployment
}

# 执行
main "$@"
