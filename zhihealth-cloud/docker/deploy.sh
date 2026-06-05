#!/bin/bash
# ============================================================
#  智康云枢 一键部署脚本
#  用法:
#    ./deploy.sh start     # 启动全部服务
#    ./deploy.sh stop      # 停止全部服务
#    ./deploy.sh status    # 查看状态
#    ./deploy.sh logs [服务名]  # 查看日志
#    ./deploy.sh check     # 环境检测
#    ./deploy.sh init-db   # 初始化数据库
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.full.yml"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}   $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ==================== 环境检测 ====================
check_env() {
    log_info "===== 环境检测 ====="

    local pass=true

    # Docker
    if command -v docker &>/dev/null; then
        log_ok "Docker: $(docker --version | cut -d' ' -f3 | tr -d ',')"
    else
        log_err "Docker 未安装"; pass=false
    fi

    # Docker Compose
    if docker compose version &>/dev/null; then
        log_ok "Docker Compose: $(docker compose version --short)"
    else
        log_err "Docker Compose 未安装"; pass=false
    fi

    # 磁盘空间 (>5GB)
    local free_kb=$(df "$SCRIPT_DIR" | awk 'NR==2{print $4}')
    local free_gb=$((free_kb / 1024 / 1024))
    if [ $free_gb -gt 5 ]; then
        log_ok "磁盘空间: ${free_gb}GB 可用"
    else
        log_warn "磁盘空间不足: 仅剩 ${free_gb}GB"
    fi

    # 内存
    local total_mem=$(free -g 2>/dev/null | awk '/Mem:/{print $2}' || echo "?")
    log_info "系统内存: ${total_mem}G"

    # 端口占用检查
    local ports=(80 8080 8848 3306 6379 8086 11434)
    for p in "${ports[@]}"; do
        if ss -tlnp 2>/dev/null | grep -q ":$p "; then
            log_warn "端口 $p 已被占用"
        else
            log_ok "端口 $p 空闲"
        fi
    done

    # Ollama检测
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        local models=$(curl -sf http://localhost:11434/api/tags | python3 -c "import sys,json; print(','.join(m['name'] for m in json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "无")
        log_ok "Ollama 在线 (模型: ${models:-无})"
    else
        log_warn "Ollama 未运行或不可达 (AI功能将受限)"
    fi

    if $pass; then
        log_ok "环境检测通过!"
    else
        log_err "环境检测未通过，请先修复上述问题"
        return 1
    fi
}

# ==================== 启动服务 ====================
do_start() {
    log_info "===== 启动智康云枢 ====="

    # 检查compose文件
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_err "找不到编排文件: $COMPOSE_FILE"
        exit 1
    fi

    # 先启动基础设施
    log_info "第一步: 启动基础设施 (MySQL/Redis/Nacos/MongoDB/InfluxDB)..."
    docker compose -f "$COMPOSE_FILE" up -d mysql-master redis-master redis-slave redis-sentinel-1 influxdb mongodb nacos1 nacos2 rabbitmq

    log_info "等待Nacos就绪..."
    for i in $(seq 1 24); do
        if curl -sf http://localhost:8848/nacos/v1/console/health/liveness >/dev/null 2>&1; then
            log_ok "Nacos集群已就绪"
            break
        fi
        sleep 5
        echo -n "."
    done

    # 配置MySQL主从
    log_info "配置MySQL主从复制..."
    docker exec zhihealth-mysql-slave bash -c '
        mysql -uroot -p"${MYSQL_ROOT_PASSWORD:-123456}" -e "
            CHANGE REPLICATION SOURCE TO
                SOURCE_HOST=\"mysql-master\",
                SOURCE_PORT=3306,
                SOURCE_USER=\"repl_user\",
                SOURCE_PASSWORD=\"repl_2024_secure\",
                GET_MASTER_PUBLIC_KEY=1;
            START REPLICA;
        " 2>/dev/null && echo "[OK] 主从复制已启动"' || log_warn "主从配置可能需要手动执行"

    # 启动微服务
    log_info "第二步: 启动微服务..."
    docker compose -f "$COMPOSE_FILE" up -d gateway user-service device-service collect-service storage-service cache-service alert-service ai-service report-service log-service

    # 启动前端+Python
    log_info "第三步: 启动前端 + Python AI..."
    docker compose -f "$COMPOSE_FILE" up -d python-ai frontend

    log_ok "全部服务启动完成!"
    echo ""
    echo "========================================="
    echo "  访问地址:"
    echo "    前端:       http://localhost"
    echo "    Nacos控制台: http://localhost:8848/nacos (nacos/nacos)"
    echo "    RabbitMQ:   http://localhost:15672 (admin/rabbit_2024)"
    echo "========================================="
    do_status
}

# ==================== 停止服务 ====================
do_stop() {
    log_info "停止所有服务..."
    docker compose -f "$COMPOSE_FILE" down
    log_ok "已停止"
}

# ==================== 查看状态 ====================
do_status() {
    log_info "===== 服务状态 ====="
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    log_info "===== 资源使用 ====="
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# ==================== 查看日志 ====================
do_logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100 "$service"
    else
        docker compose -f "$COMPOSE_FILE" logs -f --tail=50
    fi
}

# ==================== 初始化数据库 ====================
do_init_db() {
    log_info "初始化数据库..."

    # 等待MySQL ready
    until docker exec zhihealth-mysql-master mysqladmin ping -proot_123456 --silent; do
        echo "等待MySQL..."; sleep 2
    done

    # 执行建表SQL
    if [ -f "$SCRIPT_DIR/sql/init.sql" ]; then
        docker exec -i zhihealth-mysql-master mysql -uroot -p"${MYSQL_ROOT_PASSWORD:-123456}" zhihealth < "$SCRIPT_DIR/sql/init.sql"
        log_ok "数据库表初始化完成"
    fi

    # 初始化MongoDB集合
    docker exec zhihealth-mongodb mongosh -u admin -p"${MONGO_PASSWORD:-mongo_2024}" --authenticationDatabase admin zhihealth_docs --file /docker-entrypoint-initdb.d/init.js 2>/dev/null || true
    log_ok "MongoDB集合初始化完成"

    log_ok "数据库初始化完成!"
}

# ==================== 主入口 ====================
case "${1:-help}" in
    start)   check_env && do_start ;;
    stop)    do_stop ;;
    status)  do_status ;;
    logs)    do_logs "$2" ;;
    check)   check_env ;;
    init-db) do_init_db ;;
    *)
        echo ""
        echo "智康云枢 部署工具"
        echo ""
        echo "用法: $0 <命令>"
        echo ""
        echo "命令:"
        echo "  start       启动全部服务 (自动检测环境)"
        echo "  stop        停止全部服务"
        echo "  status      查看服务状态与资源使用"
        echo "  logs [服务]  查看日志 (可指定服务名)"
        echo "  check       环境检测"
        echo "  init-db     初始化数据库"
        echo "  help        显示帮助"
        echo ""
        echo "示例:"
        echo "  $0 check         # 先检测环境"
        echo "  $0 init-db       # 初始化数据库"
        echo "  $0 start         # 一键启动"
        echo "  $0 logs gateway  # 查看网关日志"
        echo ""
        ;;
esac
