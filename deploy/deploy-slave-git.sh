#!/bin/bash
# ============================================================
#  智康云枢 - 从节点(Slave)一键部署脚本 (Git版)
#  用途: 克隆代码 + 启动大数据存储服务
#  适用: CentOS 7.9 / 2核4G服务器
# ============================================================

set -e

MASTER_IP="182.92.1.136"

echo "╔══════════════════════════════════════════════════╗"
echo "║     智康云枢 从节点 一键部署向导 (Git版)        ║"
echo "║     Server: $(hostname) ($(hostname -I | awk '{print $1}'))    ║"
echo "╚══════════════════════════════════════════════════╝"

# ==================== 第1步：环境准备 ====================
prepare_env() {
    echo ">>> [1/4] 环境准备..."
    
    yum install -y git wget unzip -q 2>/dev/null || true
    systemctl disable firewalld 2>/dev/null || true
    systemctl stop firewalld 2>/dev/null || true
    
    mkdir -p /opt/zhihealth/{data,logs,backups}
    
    echo "✅ 完成"
}

# ==================== 第2步：克隆代码 ====================
clone_code() {
    echo ">>> [2/4] 克隆代码..."
    cd /opt/zhihealth
    
    if [ ! -d ".git" ]; then
        # 如果没有Git仓库，从主节点复制deploy文件夹即可
        echo "从主节点获取部署配置..."
        scp -o StrictHostKeyChecking=no root@${MASTER_IP}:/opt/zhihealth/deploy ./deploy 2>/dev/null || {
            echo "请先在主节点执行部署，或手动上传deploy文件夹"
            exit 1
        }
    else
        git pull origin main
    fi
    
    echo "✅ 完成"
}

# ==================== 第3步：网络测试 ====================
test_network() {
    echo ">>> [3/4] 测试主节点连通性..."
    
    if ping -c 3 $MASTER_IP > /dev/null 2>&1; then
        echo "  ✅ Ping通 ($MASTER_IP)"
    else
        echo "  ❌ 无法Ping通主节点"
        exit 1
    fi
    
    echo "✅ 网络正常"
}

# ==================== 第4步：启动存储服务 ====================
start_storage() {
    echo ">>> [4/4] 启动存储服务..."
    
    cd /opt/zhihealth/deploy
    
    cat > .env << EOF
INFLUX_PASSWORD=admin123456
MONGO_PASSWORD=mongo123456
MASTER_IP=$MASTER_IP
EOF
    
    docker-compose -f docker-compose.slave.yml up -d
    
    sleep 30
    
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║  🎉 从节点部署完成！                            ║"
    echo "╠══════════════════════════════════════════════════╣"
    echo "║  InfluxDB: http://$(hostname -I | awk '{print $1}'):8086         ║"
    echo "║  MongoDB:  $(hostname -I | awk '{print $1}'):27017              ║"
    echo "╠══════════════════════════════════════════════════╣"
    echo "║  管理命令:                                       ║"
    echo "║  docker logs -f zhihealth-influxdb             ║"
    echo "║  docker logs -f zhihealth-mongodb             ║"
    echo "╚══════════════════════════════════════════════════╝"
}

main
prepare_env
clone_code
test_network
start_storage
