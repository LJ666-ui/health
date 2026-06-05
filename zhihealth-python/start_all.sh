#!/bin/bash
# ============================================================
# ZhiHealth 智慧健康大数据平台 - 一键启动脚本 (Linux/Mac)
# 
# 用法:
#   ./start_all.sh              # 启动全部服务
#   ./start_all.sh --api-only    # 仅启动API服务
#   ./start_all.sh --stop        # 停止所有服务
#   ./start_all.sh --status      # 查看服务状态
#
# 启动的服务:
#   1. REST API Server      :5000
#   2. WebSocket Server     :8088
#   3. Prometheus Monitor   :9090
#   4. Task Scheduler       :后台运行
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_NC='\033[0m'

PID_DIR=".pids"
mkdir -p "$PID_DIR"
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

print_banner() {
    echo -e "${COLOR_BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     🏥 ZhiHealth 智慧健康大数据平台 v2.0                   ║"
    echo "║     🚀 一键启动全部服务                                    ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${COLOR_NC}"
}

check_dependencies() {
    echo -e "${COLOR_YELLOW}[检查] 验证Python环境...${COLOR_NC}"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${COLOR_RED}[错误] Python3 未安装${COLOR_NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${COLOR_GREEN}[OK] Python 版本: $PYTHON_VERSION${COLOR_NC}"
    
    if [ ! -f "requirements.txt" ]; then
        echo -e "${COLOR_RED}[错误] requirements.txt 不存在${COLOR_NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}[提示] 如需安装依赖: pip install -r requirements.txt${NC}"
}

start_api_server() {
    echo -e "${COLOR_BLUE}[启动] REST API + WebSocket 服务...${COLOR_NC}"
    
    nohup python3 main.py api start \
        --host 0.0.0.0 \
        --port 5000 \
        --ws-port 8088 \
        --enable-ws \
        > "$LOG_DIR/api_server.log" 2>&1 &
    
    API_PID=$!
    echo $API_PID > "$PID_DIR/api_server.pid"
    
    sleep 2
    
    if ps -p $API_PID > /dev/null 2>&1; then
        echo -e "${COLOR_GREEN}[OK] API服务已启动 | PID: $API_PID | http://localhost:5000${COLOR_NC}"
        echo -e "${COLOR_GREEN}[OK] WebSocket已启动 | ws://localhost:8088${COLOR_NC}"
    else
        echo -e "${COLOR_RED}[失败] API服务启动失败，请查看日志: $LOG_DIR/api_server.log${COLOR_NC}"
        return 1
    fi
}

start_monitor() {
    echo -e "${COLOR_BLUE}[启动] Prometheus 监控端点...${COLOR_NC}"
    
    nohup python3 main.py monitor start \
        --host 0.0.0.0 \
        --port 9090 \
        > "$LOG_DIR/monitor.log" 2>&1 &
    
    MONITOR_PID=$!
    echo $MONITOR_PID > "$PID_DIR/monitor.pid"
    
    sleep 1
    
    if ps -p $MONITOR_PID > /dev/null 2>&1; then
        echo -e "${COLOR_GREEN}[OK] 监控端点已启动 | PID: $MONITOR_PID | http://localhost:9090/metrics${COLOR_NC}"
    else
        echo -e "${COLOR_YELLOW}[警告] 监控端点启动失败（非致命错误）${COLOR_NC}"
    fi
}

start_scheduler() {
    echo -e "${COLOR_BLUE}[启动] 定时任务调度器...${COLOR_NC}"
    
    nohup python3 main.py scheduler run --workers 4 \
        > "$LOG_DIR/scheduler.log" 2>&1 &
    
    SCHEDULER_PID=$!
    echo $SCHEDULER_PID > "$PID_DIR/scheduler.pid"
    
    sleep 1
    
    if ps -p $SCHEDULER_PID > /dev/null 2>&1; then
        echo -e "${COLOR_GREEN}[OK] 调度器已启动 | PID: $SCHEDULER_PID${COLOR_NC}"
    else
        echo -e "${COLOR_YELLOW}[警告] 调度器启动失败（非致命错误）${COLOR_NC}"
    fi
}

stop_all_services() {
    echo -e "${COLOR_YELLOW}[停止] 正在关闭所有服务...${COLOR_NC}"
    
    for pid_file in "$PID_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            PID=$(cat "$pid_file")
            SERVICE_NAME=$(basename "$pid_file" .pid)
            
            if ps -p $PID > /dev/null 2>&1; then
                kill $PID 2>/dev/null || true
                echo -e "${COLOR_GREEN}[已停止] $SERVICE_NAME (PID: $PID)${COLOR_NC}"
            fi
            
            rm -f "$pid_file"
        fi
    done
    
    echo -e "${COLOR_GREEN}[完成] 所有服务已停止${COLOR_NC}"
}

show_status() {
    echo -e "${COLOR_BLUE}══════════════════════════════════════════${COLOR_NC}"
    echo -e "${COLOR_BLUE}  ZhiHealth 服务状态${COLOR_NC}"
    echo -e "${COLOR_BLUE}══════════════════════════════════════════${COLOR_NC}\n"
    
    total=0
    running=0
    
    declare -A SERVICES=(
        ["api_server"]="REST API Server (:5000)"
        ["monitor"]="Prometheus Monitor (:9090)"
        ["scheduler"]="Task Scheduler"
    )
    
    for service in "${!SERVICES[@]}"; do
        pid_file="$PID_DIR/${service}.pid"
        total=$((total + 1))
        
        if [ -f "$pid_file" ]; then
            PID=$(cat "$pid_file")
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "  ${COLOR_GREEN}● 运行中${COLOR_NC} | ${SERVICES[$service]} | PID: $PID"
                running=$((running + 1))
            else
                echo -e "  ${COLOR_RED}○ 已停止${COLOR_NC} | ${SERVICES[$service]}"
            fi
        else
            echo -e "  ${COLOR_GRAY}○ 未启动${COLOR_NC} | ${SERVICES[$service]}"
        fi
    done
    
    echo -e "\n${COLOR_BLUE}总计: $running/$total 个服务运行中${COLOR_NC}"
}

show_dashboard() {
    echo -e "\n${COLOR_BLUE}══════════════════════════════════════════${COLOR_NC}"
    echo -e "${COLOR_BLUE}  🌐 访问地址${COLOR_NC}"
    echo -e "${COLOR_BLUE}══════════════════════════════════════════${COLOR_NC}\n"
    
    echo -e "  ${COLOR_GREEN}REST API:${COLOR_NC}       http://localhost:5000"
    echo -e "  ${COLOR_GREEN}API 文档:${COLOR_NC}       http://localhost:5000/docs"
    echo -e "  ${COLOR_GREEN}WebSocket:${COLOR_NC}      ws://localhost:8088"
    echo -e "  ${COLOR_GREEN}健康检查:${COLOR_NC}      http://localhost:5000/health"
    echo -e "  ${COLOR_GREEN}Prometheus:${COLOR_NC}     http://localhost:9090/metrics"
    echo -e "\n  ${COLOR_YELLOW}日志目录:${COLOR_NC}     $LOG_DIR/"
    echo -e "  ${COLOR_YELLOW}进程PID:${COLOR_NC}       $PID_DIR/"
    echo ""
}

main() {
    case "${1:-start}" in
        --stop|stop)
            stop_all_services
            ;;
        --status|status)
            show_status
            ;;
        --api-only)
            print_banner
            check_dependencies
            start_api_server
            show_dashboard
            ;;
        start|--help|-h|"")
            print_banner
            check_dependencies
            
            echo -e "\n${COLOR_YELLOW}开始启动所有服务...${COLOR_NC}\n"
            
            start_api_server
            start_monitor
            start_scheduler
            
            echo -e "\n${COLOR_GREEN}══════════════════════════════════════════${COLOR_NC}"
            echo -e "${COLOR_GREEN}  ✅ 所有服务启动完成！${COLOR_NC}"
            echo -e "${COLOR_GREEN}══════════════════════════════════════════${COLOR_NC}"
            
            show_status
            show_dashboard
            
            echo -e "${COLOR_YELLOW}提示: 使用 './start_all.sh --stop' 停止所有服务${COLOR_NC}"
            echo -e "${COLOR_YELLOW}提示: 使用 './start_all.sh --status' 查看运行状态${COLOR_NC}"
            ;;
        *)
            echo -e "${COLOR_RED}未知参数: $1${COLOR_NC}"
            echo "用法: $0 [--stop|--status|--api-only]"
            exit 1
            ;;
    esac
}

main "$@"