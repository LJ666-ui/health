#!/bin/bash

# ZhiHealth 一键部署脚本
# 用法: ./deploy.sh [start|stop|restart|status|logs|init]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker 未安装${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}错误: Docker Compose 未安装${NC}"
        exit 1
    fi
}

create_env_file() {
    if [ ! -f ".env" ]; then
        cat > .env << 'EOF'
# ZhiHealth 环境配置
COMPOSE_PROJECT_NAME=zhihealth

# MySQL
MYSQL_ROOT_PASSWORD=ZhiHealth@2026
MYSQL_DATABASE=zhihealth
MYSQL_USER=zhihealth
MYSQL_PASSWORD=ZhiHealth123

# Redis
REDIS_PASSWORD=

# MongoDB
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=ZhiHealthMongo2026

# InfluxDB
INFLUXDB_ADMIN_USER=admin
INFLUXDB_ADMIN_PASSWORD=ZhiHealthInflux2026
INFLUXDB_ORG=zhihealth
INFLUXDB_BUCKET=health_data

# Nacos
NACOS_MODE=standalone

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=ZhiHealthGrafana2026

# Python API
PYTHON_ENV=production
LOG_LEVEL=INFO
EOF
        echo -e "${GREEN}✓ 已创建 .env 配置文件${NC}"
    fi
}

cmd_start() {
    print_header "启动 ZhiHealth 平台"
    
    check_docker
    create_env_file
    
    echo -e "${YELLOW}[1/4] 拉取/构建镜像...${NC}"
    docker compose pull --ignore-buildable 2>/dev/null || true
    docker compose build python-api
    
    echo -e "\n${YELLOW}[2/4] 启动基础设施服务...${NC}"
    docker compose up -d mysql redis mongodb influxdb zookeeper kafka nacos
    
    echo -e "\n${YELLOW}[3/4] 等待服务就绪...${NC}"
    sleep 15
    
    echo -e "\n${YELLOW}[4/4] 启动应用服务...${NC}"
    docker compose up -d python-api grafana
    
    print_header "✅ 部署完成！"
    
    echo -e "${GREEN}服务访问地址:${NC}"
    echo -e "  🌐 Python API:       http://localhost:5000"
    echo -e "  📊 可视化大屏:      http://localhost:5000/"
    echo -e "  📈 Grafana面板:     http://localhost:3000 (admin/ZhiHealthGrafana2026)"
    echo -e "  ⚙️  Nacos控制台:    http://localhost:8848/nacos (nacos/nacos)"
    echo -e "  💾 MySQL:           localhost:3306 (root/ZhiHealth@2026)"
    echo -e "  🔴 Redis:           localhost:6379"
    echo -e "  🟢 MongoDB:         localhost:27017"
    echo -e "  ⏱️  InfluxDB:        localhost:8086"
    echo -e "  📨 Kafka:           localhost:9092"
}

cmd_stop() {
    print_header "停止 ZhiHealth 平台"
    docker compose down
    echo -e "${GREEN}✓ 所有服务已停止${NC}"
}

cmd_restart() {
    cmd_stop
    cmd_start
}

cmd_status() {
    print_header "ZhiHealth 服务状态"
    docker compose ps
}

cmd_logs() {
    local service=${1:-}
    if [ -z "$service" ]; then
        docker compose logs -f --tail=100
    else
        docker compose logs -f --tail=100 "$service"
    fi
}

cmd_init() {
    print_header "初始化测试数据"
    
    check_docker
    
    # 生成测试数据
    docker compose exec python-api python main.py generate --count 1000 --output data/test_data.csv
    
    # 运行ETL
    docker compose exec python-api python main.py etl --mode full --input data/test_data.csv
    
    # 运行AI分析
    docker compose exec python-api python main.py ai --mode analyze --input data/test_data.csv
    
    echo -e "${GREEN}✅ 测试数据初始化完成！${NC}"
}

case "${1:-start}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "$2"
        ;;
    init)
        cmd_init
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs|init}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动所有服务（默认）"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看日志 [服务名]"
        echo "  init    - 初始化测试数据"
        exit 1
        ;;
esac