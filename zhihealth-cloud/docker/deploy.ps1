# ============================================================
#  智康云枢 部署工具 (Windows PowerShell)
#  用法:
#    .\deploy.ps1 start       # 启动全部服务
#    .\deploy.ps1 stop        # 停止全部服务
#    .\deploy.ps1 status      # 查看状态
#    .\deploy.ps1 logs [服务名] # 查看日志
#    .\deploy.ps1 check       # 环境检测
#    .\deploy.ps1 init-db     # 初始化数据库
# ============================================================

param(
    [string]$Command = "help",
    [string]$Service = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComposeFile = Join-Path $ScriptDir "docker-compose.full.yml"

function Write-Info($msg)  { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# ==================== 环境检测 ====================
function Check-Env {
    Write-Info "===== 环境检测 ====="

    # Docker
    try {
        $v = docker --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Docker: $($v.Split(' ')[2])"
        } else { throw }
    } catch { Write-Err "Docker 未安装或未启动" }

    # Docker Compose
    try {
        docker compose version 2>$null | Out-Null
        Write-Ok "Docker Compose: $(docker compose version --short)"
    } catch { Write-Err "Docker Compose 未安装" }

    # 磁盘空间
    $drive = (Get-Item $ScriptDir).PSDrive.Name + ":"
    $freeGB = [math]::Round((Get-PSDrive $drive).Free / 1GB, 1)
    if ($freeGB -gt 5) { Write-Ok "磁盘空间: ${freeGB}GB 可用" }
    else { Write-Warn "磁盘不足: ${freeGB}GB" }

    # Ollama
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
        $models = ($resp.models | ForEach-Object { $_.name }) -join ", "
        Write-Ok "Ollama 在线 (模型: $($models -or '无'))"
    } catch { Write-Warn "Ollama 未运行或不可达" }

    Write-Ok "环境检测完成!"
}

# ==================== 启动 ====================
function Do-Start {
    Write-Info "===== 启动智康云枢 ====="

    if (-not (Test-Path $ComposeFile)) {
        Write-Err "找不到编排文件: $ComposeFile"; return
    }

    # 第一步：基础设施
    Write-Info "步骤1/3: 启动基础设施..."
    docker compose -f $ComposeFile up -d mysql-master redis-master redis-slave redis-sentinel-1 influxdb mongodb nacos1 nacos2 rabbitmq

    Write-Info "等待Nacos就绪..."
    $ready = $false
    for ($i = 0; $i -lt 24; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:8848/nacos/v1/console/health/liveness" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
        Start-Sleep -Seconds 5
        Write-Host "." -NoNewline
    }
    if ($ready) { Write-Ok "Nacos集群已就绪" }
    else { Write-Warn "Nacos可能未完全就绪，继续启动..." }

    # 第二步：微服务
    Write-Info "步骤2/3: 启动微服务..."
    docker compose -f $ComposeFile up -d gateway user-service device-service collect-service storage-service cache-service alert-service ai-service report-service log-service

    # 第三步：前端+Python
    Write-Info "步骤3/3: 启动前端 + Python AI..."
    docker compose -f $ComposeFile up -d python-ai frontend

    Write-Ok "全部服务已启动!"
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "  访问地址:" -ForegroundColor White
    Write-Host "    前端:         http://localhost" -ForegroundColor White
    Write-Host "    Nacos控制台:   http://localhost:8848/nacos (nacos/nacos)" -ForegroundColor White
    Write-Host "    RabbitMQ管理:  http://localhost:15672 (admin/rabbit_2024)" -ForegroundColor White
    Write-Host "=========================================" -ForegroundColor Green

    Do-Status
}

# ==================== 停止 ====================
function Do-Stop {
    Write-Info "停止所有服务..."
    docker compose -f $ComposeFile down
    Write-Ok "已停止"
}

# ==================== 状态 ====================
function Do-Status {
    Write-Info "===== 服务状态 ====="
    docker compose -f $ComposeFile ps
    Write-Host ""
    Write-Info "===== 资源使用 ====="
    docker stats --no-stream --format "table {{.Name}}`t{{.CPUPerc}}`t{{.MemUsage}}`t{{.NetIO}}"
}

# ==================== 日志 ====================
function Do-Logs {
    if ($Service) {
        docker compose -f $ComposeFile logs -f --tail=100 $Service
    } else {
        docker compose -f $Compose_FILE logs -f --tail=50
    }
}

# ==================== 初始化数据库 ====================
function Do-InitDb {
    Write-Info "初始化数据库..."

    # 等MySQL ready
    do { Start-Sleep 2; Write-Host "等待MySQL..." }
    until ((docker exec zhihealth-mysql-master mysqladmin ping -p123456 --silent 2>&1) -match "alive")

    $initSql = Join-Path $ScriptDir "sql\init.sql"
    if (Test-Path $initSql) {
        Get-Content $initSql | docker exec -i zhihealth-mysql-master mysql -uroot -p123456 zhihealth
        Write-Ok "MySQL表初始化完成"
    }
    Write-Ok "数据库初始化完成!"
}

# ==================== 主入口 ========================
switch ($Command.ToLower()) {
    "start"   { Check-Env; Do-Start }
    "stop"    { Do-Stop }
    "status"  { Do-Status }
    "logs"    { Do-Logs }
    "check"   { Check-Env }
    "init-db" { Do-InitDb }
    default {
        Write-Host @'

 智康云枢 部署工具 (Windows)

 用法: .\deploy.ps1 <命令>

 命令:
   start       启动全部服务 (自动检测环境)
   stop        停止全部服务
   status      查看服务状态与资源使用
   logs [服务]  查看日志 (可指定服务名)
   check       环境检测
   init-db     初始化数据库
   help        显示帮助

 示例:
   .\deploy.ps1 check          # 先检测环境
   .\deploy.ps1 init-db        # 初始化数据库
   .\deploy.ps1 start          # 一键启动
   .\deploy.ps1 logs gateway   # 查看网关日志

'@
    }
}
