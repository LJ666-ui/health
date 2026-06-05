@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: ZhiHealth 一键部署脚本 (Windows)
:: 用法: deploy.bat [start|stop|restart|status|logs|init]

cd /d "%~dp0"

if "%1"=="" goto start
if /i "%1"=="start" goto start
if /i "%1"=="stop" goto stop
if /i "%1"=="restart" goto restart
if /i "%1"=="status" goto status
if /i "%1"=="logs" goto logs
if /i "%1"=="init" goto init
goto usage

:start
echo.
echo ============================================================
echo   ZhiHealth 智慧健康大数据平台 - 启动中...
echo ============================================================
echo.

:: 创建环境配置文件
if not exist ".env" (
    echo [INFO] 创建 .env 配置文件...
    (
        echo COMPOSE_PROJECT_NAME=zhihealth
        echo MYSQL_ROOT_PASSWORD=ZhiHealth@2026
        echo MYSQL_DATABASE=zhihealth
        echo MYSQL_USER=zhihealth
        echo MYSQL_PASSWORD=ZhiHealth123
        echo REDIS_PASSWORD=
        echo MONGO_INITDB_ROOT_USERNAME=admin
        echo MONGO_INITDB_ROOT_PASSWORD=ZhiHealthMongo2026
        echo INFLUXDB_ADMIN_USER=admin
        echo INFLUXDB_ADMIN_PASSWORD=ZhiHealthInflux2026
        echo GF_SECURITY_ADMIN_USER=admin
        echo GF_SECURITY_ADMIN_PASSWORD=ZhiHealthGrafana2026
    ) > .env
    echo [OK] .env 已创建
)

echo [1/4] 构建Python API镜像...
docker compose build python-api
if errorlevel 1 (
    echo [ERROR] 镜像构建失败
    pause
    exit /b 1
)

echo.
echo [2/4] 启动基础设施服务 (MySQL, Redis, MongoDB, InfluxDB, Kafka, Nacos)...
docker compose up -d mysql redis mongodb influxdb zookeeper kafka nacos
timeout /t 10 /nobreak >nul

echo.
echo [3/4] 等待服务就绪...
timeout /t 15 /nobreak >nul

echo.
echo [4/4] 启动应用服务 (Python API, Grafana)...
docker compose up -d python-api grafana

echo.
echo ============================================================
echo   ✅ 部署完成！
echo ============================================================
echo.
echo   服务访问地址:
echo   ┌─────────────────────────────────────────────────────┐
echo   │ 🌐 Python API:       http://localhost:5000          │
echo   │ 📊 可视化大屏:      http://localhost:5000/          │
echo   │ 📈 Grafana面板:     http://localhost:3000          │
echo   │                     用户: admin                      │
echo   │                     密码: ZhiHealthGrafana2026      │
echo   │ ⚙️  Nacos控制台:    http://localhost:8848/nacos     │
echo   │                     用户: nacos / nacos             │
echo   │ 💾 MySQL:           localhost:3306                  │
echo   │ 🔴 Redis:           localhost:6379                  │
echo   │ 🟢 MongoDB:         localhost:27017                 │
echo   │ ⏱️  InfluxDB:        localhost:8086                 │
echo   │ 📨 Kafka:           localhost:9092                  │
echo   └─────────────────────────────────────────────────────┘
echo.
pause
goto :eof

:stop
echo.
echo [INFO] 停止所有服务...
docker compose down
echo [OK] 所有服务已停止
pause
goto :eof

:restart
call :stop
call :start
goto :eof

:status
echo.
echo ============================================================
echo   ZhiHealth 服务状态
echo ============================================================
echo.
docker compose ps
echo.
pause
goto :eof

:logs
set "SERVICE=%2"
if "%SERVICE%"=="" (
    docker compose logs -f --tail=100
) else (
    docker compose logs -f --tail=100 %SERVICE%
)
goto :eof

:init
echo.
echo ============================================================
echo   初始化测试数据
echo ============================================================
echo.

echo [1/3] 生成测试数据...
docker compose exec python-api python main.py generate --count 1000 --output data\test_data.csv

echo.
echo [2/3] 运行ETL流程...
docker compose exec python-api python main.py etl --mode full --input data\test_data.csv

echo.
echo [3/3] 运行AI分析...
docker compose exec python-api python main.py ai --mode analyze --input data\test_data.csv

echo.
echo ✅ 测试数据初始化完成！
pause
goto :eof

:usage
echo.
echo ZhiHealth 一键部署工具
echo.
echo 用法: %~nx0 [命令]
echo.
echo 命令:
echo   start   - 启动所有服务（默认）
echo   stop    - 停止所有服务
echo   restart - 重启所有服务
echo   status  - 查看服务状态
echo   logs    - 查看日志 [服务名]
echo   init    - 初始化测试数据
echo.
echo 示例:
echo   %~nx0 start          # 启动平台
echo   %~nx0 stop           # 停止平台
echo   %~nx0 logs python-api # 查看API日志
echo   %~nx0 init           # 初始化测试数据
echo.
pause