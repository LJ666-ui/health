# ============================================================
#  智康云枢 - 云部署包打包工具 (PowerShell版)
#  用途: 打包需要上传到云服务器的文件
#  输出: zhihealth-deploy.zip (Windows原生格式)
# ============================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  智康云枢 云部署包打包工具" -ForegroundColor Green
Write-Host "  时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan

# 切换到项目根目录
Set-Location "e:\Health"

# 创建临时目录
$tempDir = "e:\Health\deploy_temp"
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

Write-Host "`n[1/5] 复制部署脚本..." -ForegroundColor Yellow
Copy-Item -Path "deploy" -Destination "$tempDir\deploy" -Recurse

Write-Host "[2/5] 复制后端代码 (排除target和.git)..." -ForegroundColor Yellow
Copy-Item -Path "zhihealth-cloud" -Destination "$tempDir\zhihealth-cloud" -Recurse
# 排除target目录
Get-ChildItem -Path "$tempDir\zhihealth-cloud" -Directory -Recurse -Filter "target" | Remove-Item -Recurse -Force
Get-Item "$tempDir\zhihealth-cloud\target" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
# 排除.git目录
Get-Item "$tempDir\zhihealth-cloud\.git" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

Write-Host "[3/5] 复制前端代码 (排除node_modules和dist)..." -ForegroundColor Yellow
Copy-Item -Path "zhihealth-frontend" -Destination "$tempDir\zhihealth-frontend" -Recurse
Get-Item "$tempDir\zhihealth-frontend\node_modules" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-Item "$temp_temp\zhihealth-frontend\dist" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

Write-Host "[4/5] 复制数据库初始化脚本..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "$tempDir\sql" -ErrorAction SilentlyContinue | Out-Null
if (Test-Path "zhihealth-cloud\docker\sql") {
    Copy-Item -Path "zhihealth-cloud\docker\sql\*.sql" -Destination "$tempDir\sql\" -ErrorAction SilentlyContinue
}

# 打包为ZIP（Windows原生格式，Linux服务器可用unzip解压）
Write-Host "`n[5/5] 正在打包..." -ForegroundColor Yellow
$zipFile = "e:\Health\zhihealth-deploy.zip"

# 使用.NET Framework压缩（无需额外软件）
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($tempDir, $zipFile)

# 清理临时目录
Remove-Item $tempDir -Recurse -Force

# 显示结果
$fileInfo = Get-Item $zipFile
$sizeMB = [math]::Round($fileInfo.Length / 1MB, 2)

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  打包完成!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "文件名: zhihealth-deploy.zip" -ForegroundColor White
Write-Host "大小:   $sizeMB MB" -ForegroundColor White
Write-Host "位置:   e:\Health\zhihealth-deploy.zip" -ForegroundColor White
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "  方式1: 使用WinSCP上传到服务器" -ForegroundColor White
Write-Host "  方式2: 使用scp命令上传" -ForegroundColor White
Write-Host ""
Write-Host "  上传到主节点: scp e:\Health\zhihealth-deploy.zip root@182.92.1.136:/opt/" -ForegroundColor Gray
Write-Host "  上传到从节点: scp e:\Health\zhihealth-deploy.zip root@39.105.129.207:/opt/" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan

# 询问是否打开文件夹
$open = Read-Host "`n是否打开所在文件夹? (y/n)"
if ($open -eq 'y' -or $open -eq 'Y') {
    explorer.exe "e:\Health"
}
