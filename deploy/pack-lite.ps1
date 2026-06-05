# 智康云枢 - 轻量级云部署打包脚本
# 排除: node_modules, target, .git, dist 等大文件夹

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ZhiHealth Cloud Deployment Packager" -ForegroundColor Green
Write-Host "  Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan

$sourceDir = "e:\Health"
$tempDir = "$sourceDir\temp_deploy"
$zipFile = "$sourceDir\zhihealth-deploy-lite.zip"

# Clean up
if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
if (Test-Path $zipFile) { Remove-Item $zipFile -Force }
New-Item -ItemType Directory -Path $tempDir | Out-Null

Write-Host "`n[1/4] Copying deploy scripts..." -ForegroundColor Yellow
Copy-Item "$sourceDir\deploy" "$tempDir\deploy" -Recurse

Write-Host "[2/4] Copying backend code (excluding target/.git)..." -ForegroundColor Yellow
Copy-Item "$sourceDir\zhihealth-cloud" "$tempDir\zhihealth-cloud" -Recurse
# Remove large folders
@("$tempDir\zhihealth-cloud\target", 
  "$tempDir\zhihealth-cloud\.git",
  "$tempDir\zhihealth-cloud\.idea") | ForEach-Object {
    if (Test-Path $_) { Remove-Item $_ -Recurse -Force }
}
# Remove target in subdirectories
Get-ChildItem $tempDir\zhihealth-cloud -Directory -Recurse -Filter "target" | Remove-Item -Recurse -Force

Write-Host "[3/4] Copying frontend code (excluding node_modules/dist)..." -ForegroundColor Yellow
Copy-Item "$sourceDir\zhihealth-frontend" "$tempDir\zhihealth-frontend" -Recurse
@("$tempDir\zhihealth-frontend\node_modules",
  "$tempDir\zhihealth-frontend\dist",
  "$tempDir\zhihealth-frontend\.git") | ForEach-Object {
    if (Test-Path $_) { Remove-Item $_ -Recurse -Force }
}

Write-Host "[4/4] Creating ZIP archive..." -ForegroundColor Yellow
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($tempDir, $zipFile)

# Cleanup temp
Remove-Item $tempDir -Recurse -Force

# Show result
$fileInfo = Get-Item $zipFile
$sizeMB = [math]::Round($fileInfo.Length / 1MB, 2)

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  SUCCESS! Package created." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "File: zhihealth-deploy-lite.zip" -ForegroundColor White
Write-Host "Size: $sizeMB MB" -ForegroundColor White
Write-Host "Location: e:\Health\zhihealth-deploy-lite.zip" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Upload to master: scp zhihealth-deploy-lite.zip root@182.92.1.136:/opt/" -ForegroundColor Gray
Write-Host "  2. Upload to slave:  scp zhihealth-deploy-lite.zip root@39.105.129.207:/opt/" -ForegroundColor Gray
Write-Host "  3. On server: unzip zhihealth-deploy-lite.zip && cd deploy && ./deploy-master.sh" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
