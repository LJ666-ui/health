# ============================================================
#  智康云枢 - 从节点(Slave)生产部署脚本
#  服务器: zhihealth-slave (39.105.129.207)
#  配置: 2核4G CentOS 7.9
#  用途: 大数据存储 + NoSQL数据库 + 时序数据
# ============================================================

set -e

echo "=========================================="
echo "  智康云枢 从节点部署向导"
echo "  服务器: $(hostname) ($(hostname -I | awk '{print $1}'))"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# ==================== 第1步：系统优化 ====================
optimize_system() {
    echo ""
    echo ">>> [1/6] 系统资源优化..."
    
    # 关闭防火墙（内网环境）
    systemctl disable firewalld 2>/dev/null || true
    systemctl stop firewalld 2>/dev/null || true
    
    # 优化文件描述符
    echo "* soft nofile 65535" >> /etc/security/limits.conf
    echo "* hard nofile 65535" >> /etc/security/limits.conf
    
    # 禁用SELinux
    setenforce 0 2>/dev/null || true
    sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config 2>/dev/null || true
    
    echo "✅ 系统优化完成"
}

# ==================== 第2步：检查已有服务 =====================
check_existing_services() {
    echo ""
    echo ">>> [2/6] 检查已有中间件..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker未安装"
        exit 1
    fi
    
    echo "✅ Docker版本: $(docker --version)"
    echo ""
    echo "检测到的容器:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | head -10
    
    # 启动InfluxDB和MongoDB
    if docker ps -a | grep -q influxdb; then
        echo "启动InfluxDB..."
        docker start influxdb || docker start zhihealth-influxdb || true
        sleep 5
    fi
    
    if docker ps -a | grep -q mongodb; then
        echo "启动MongoDB..."
        docker start mongodb || docker start zhihealth-mongodb || true
        sleep 5
    fi
    
    echo "✅ 中间件检查完成"
}

# ==================== 第3步：创建目录 =====================
create_directories() {
    echo ""
    echo ">>> [3/6) 创建目录结构..."
    
    mkdir -p /opt/zhihealth/{data/{influxdb,mongodb,hadoop,hive},logs,backups}
    
    # 设置数据目录权限
    chmod -R 755 /opt/zhihealth/data
    
    echo "✅ 目录创建完成"
}

# ==================== 第4步：配置网络互通 =====================
configure_network() {
    echo ""
    echo ">>> [4/6] 配置主从节点网络..."
    
    MASTER_IP="182.92.1.136"
    
    # 测试到主节点的连通性
    echo "测试到主节点($MASTER_IP)的连接:"
    
    if ping -c 3 $MASTER_IP > /dev/null 2>&1; then
        echo "   ✅ Ping通 延迟正常"
    else
        echo "   ❌ 无法Ping通主节点，请检查安全组规则"
        exit 1
    fi
    
    # 测试端口连通性
    ports=("3306" "8848" "6379")
    services=("MySQL" "Nacos" "Redis")
    
    for i in "${!ports[@]}"; do
        port=${ports[$i]}
        service=${services[$i]}
        
        if timeout 5 bash -c "echo >/dev/tcp/$MASTER_IP/$port" 2>/dev/null; then
            echo "   ✅ $service ($port) 端口可达"
        else
            echo "   ⚠️  $service ($port) 端口不可达（可能未启动）"
        fi
    done
    
    echo "✅ 网络配置完成"
}

# ==================== 第5步：启动大数据存储服务 =====================
start_storage_services() {
    echo ""
    echo ">>> [5/6] 启动存储服务..."
    
    cd /opt/zhihealth/docker
    
    # 使用从节点配置启动
    export COMPOSE_PROJECT_NAME=zhihealth
    
    docker-compose -f docker-compose.slave.yml up -d
    
    echo "等待服务启动（约30秒）..."
    sleep 30
    
    echo ""
    echo "📊 存储服务状态:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "zhihealth|NAMES"
}

# ==================== 第6步：验证部署 =====================
verify_deployment() {
    echo ""
    echo ">>> [6/6] 部署验证..."
    
    echo "1. InfluxDB健康检查:"
    if curl -sf http://localhost:8086/health > /dev/null 2>&1; then
        echo "   ✅ InfluxDB正常运行 (http://localhost:8086)"
    else
        echo "   ⚠️  InfluxDB可能还在启动中"
    fi
    
    echo ""
    echo "2. MongoDB连接测试:"
    if docker exec zhihealth-mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        echo "   ✅ MongoDB正常运行 (localhost:27017)"
    else
        echo "   ⚠️  MongoDB可能还在启动中"
    fi
    
    echo ""
    echo "=========================================="
    echo "  🎉 从节点部署完成！"
    echo "=========================================="
    echo ""
    echo "访问地址:"
    echo "  InfluxDB: http://39.105.129.207:8086 (admin/admin123456)"
    echo "  MongoDB: 39.105.129.207:27017 (admin/mongo123456)"
    echo ""
    echo "管理命令:"
    echo "  查看日志: docker logs -f zhihealth-influxdb"
    echo "  重启服务: cd /opt/zhihealth/docker && docker-compose -f docker-compose.slave.yml restart"
    echo "=========================================="
}

# ==================== 主流程 =====================
main() {
    optimize_system
    check_existing_services
    create_directories
    configure_network
    start_storage_services
    verify_deployment
}

main "$@"
