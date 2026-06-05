@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
:: ZhiHealth 智慧健康大数据平台 - 一键启动脚本 (Windows)
::
:: 用法:
::   start_all.bat              启动全部服务
::   start_all.bat --api-only   仅启动API服务
::   start_all.bat --stop       停止所有服务
::   start_all.bat --status     查看服务状态
::
:: 启动的服务:
::   1. REST API Server      :5000
::   2. WebSocket Server     :8088
::   3. Prometheus Monitor   :9090
::   4. Task Scheduler       :后台运行
:: ============================================================

title ZhiHealth Platform v2.0 - Service Manager

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PID_DIR=.pids"
if not exist "%PID_DIR%" mkdir "%PID_DIR%"
set "LOG_DIR=logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:print_banner
echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║                                                           ║
echo ║     🏥 ZhiHealth 智慧健康大数据平台 v2.0                   ║
echo ║     🚀 一键启动全部服务                                    ║
echo ║                                                           ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

goto :check_args

:check_args
if "%1"=="--stop" goto :stop_services
if "%1"=="stop" goto :stop_services
if "%1"=="--status" goto :show_status
if "%1"=="status" goto :show_status
if "%1"=="--api-only" goto :start_api_only
if "%1"=="" goto :start_all
if "%1"=="start" goto :start_all
if "%1"=="--help" goto :show_help
if "%1"=="-h" goto :show_help

echo [错误] 未知参数: %1
goto :show_help

:show_help
echo 用法: %0 [选项]
echo.
echo 选项:
echo   (无参数)    启动全部服务（默认）
echo   --stop      停止所有服务
echo   --status    查看服务运行状态
echo   --api-only  仅启动API服务
echo   --help, -h  显示帮助信息
echo.
goto :eof

:start_all
call :check_dependencies

echo [信息] 开始启动所有服务...
echo.

call :start_api_server
call :start_monitor
call :start_scheduler

echo.
echo ════════════════════════════════════════════════════════════
echo   ✅ 所有服务启动完成！
echo ════════════════════════════════════════════════════════════
echo.

call :show_status
call :show_dashboard

echo 提示: 使用 '%0 --stop' 停止所有服务
echo 提示: 使用 '%0 --status' 查看运行状态
echo.
goto :eof

:start_api_only
call :check_dependencies
call :start_api_server
call :show_dashboard
goto :eof

:check_dependencies
echo [检查] 验证Python环境...

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未安装或未添加到PATH
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
    echo [OK] Python 版本: %%v
)

if not exist requirements.txt (
    echo [错误] requirements.txt 不存在
    pause
    exit /b 1
)

echo [提示] 如需安装依赖: pip install -r requirements.txt
echo.
goto :eof

:start_api_server
echo [启动] REST API + WebSocket 服务...

start "ZHealth-API" /min python main.py api start --host 0.0.0.0 --port 5000 --ws-port 8088 --enable-ws > "%LOG_DIR%\api_server.log" 2>&1

timeout /t 2 /nobreak >nul

echo [OK] API服务已启动 | http://localhost:5000
echo [OK] WebSocket已启动 | ws://localhost:8088
echo.
goto :eof

:start_monitor
echo [启动] Prometheus 监控端点...

start "ZHealth-Monitor" /min python main.py monitor start --host 0.0.0.0 --port 9090 > "%LOG_DIR%\monitor.log" 2>&1

timeout /t 1 /nobreak >nul

echo [OK] 监控端点已启动 | http://localhost:9090/metrics
echo.
goto :eof

:start_scheduler
echo [启动] 定时任务调度器...

start "ZHealth-Scheduler" /min python main.py scheduler run --workers 4 > "%LOG_DIR%\scheduler.log" 2>&1

timeout /t 1 /nobreak >nul

echo [OK] 调度器已启动
echo.
goto :eof

:stop_services
echo [停止] 正在关闭所有服务...

taskkill /fi "WINDOWTITLE eq ZHealth-API*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq ZHealth-Monitor*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq ZHealth-Scheduler*" /f >nul 2>&1

echo [完成] 已发送停止信号给所有服务
echo.
goto :eof

:show_status
echo ════════════════════════════════════════════════════════════
echo   ZhiHealth 服务状态
echo ════════════════════════════════════════════════════════════
echo.

set RUNNING_COUNT=0

tasklist /fi "WINDOWTITLE eq ZHealth-API*" /nh 2>nul | findstr /i python >nul
if !errorlevel! equ 0 (
    echo   ● 运行中 ^| REST API Server ^(:5000^)
    set /a RUNNING_COUNT+=1
) else (
    echo   ○ 已停止 ^| REST API Server ^(:5000^)
)

tasklist /fi "WINDOWTITLE eq ZHealth-Monitor*" /nh 2>nul | findstr /i python >nul
if !errorlevel! equ 0 (
    echo   ● 运行中 ^| Prometheus Monitor ^(:9090^)
    set /a RUNNING_COUNT+=1
) else (
    echo   ○ 已停止 ^| Prometheus Monitor ^(:9090^)
)

tasklist /fi "WINDOWTITLE eq ZHealth-Scheduler*" /nh 2>nul | findstr /i python >nul
if !errorlevel! equ 0 (
    echo   ● 运行中 ^| Task Scheduler
    set /a RUNNING_COUNT+=1
) else (
    echo   ○ 已停止 ^| Task Scheduler
)

echo.
echo 总计: %RUNNING_COUNT%/3 个服务运行中
echo.
goto :eof

:show_dashboard
echo ════════════════════════════════════════════════════════════
echo   🌐 访问地址
echo ════════════════════════════════════════════════════════════
echo.
echo   REST API:       http://localhost:5000
echo   API 文档:       http://localhost:5000/docs
echo   WebSocket:      ws://localhost:8088
echo   健康检查:      http://localhost:5000/health
echo   Prometheus:     http://localhost:9090/metrics
echo.
echo   日志目录:       %LOG_DIR%\
echo.
goto :eof

endlocal