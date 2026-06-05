@echo off
chcp 65001 >nul
REM ============================================================
REM  智康云枢 - Windows本地打包脚本
REM  用途: 打包需要上传到云服务器的文件
REM  输出: zhihealth-deploy.tar.gz (预计<100MB)
REM ============================================================

echo ============================================
echo   智康云枢 云部署包打包工具
echo   时间: %date% %time%
echo ============================================

cd /d e:\Health

REM 创建临时目录
if exist deploy_temp rmdir /s /q deploy_temp
mkdir deploy_temp

REM 复制deploy目录（部署脚本和配置）
echo [1/4] 复制部署脚本...
xcopy /E /I /Y deploy deploy_temp\deploy\ >nul

REM 复制后端代码（排除target和.git）
echo [2/4] 复制后端代码...
xcopy /E /I /Y zhihealth-cloud deploy_temp\zhihealth-cloud\ >nul
if exist deploy_temp\zhihealth-cloud\target rmdir /s /q deploy_temp\zhihealth-cloud\target
for /d %%d in (deploy_temp\zhihealth-cloud\*) do (
    if exist "%%d\target" rmdir /s /q "%%d\target"
)

REM 复制前端代码（排除node_modules和dist）
echo [3/4] 复制前端代码...
xcopy /E /I /Y zhihealth-frontend deploy_temp\zhihealth-frontend\ >nul
if exist deploy_temp\zhihealth-frontend\node_modules rmdir /s /q deploy_temp\zhihealth-frontend\node_modules
if exist deploy_temp\zhihealth-frontend\dist rmdir /s /q deploy_temp\zhihealth-frontend\dist

REM 复制SQL初始化脚本
echo [4/4] 复制数据库脚本...
mkdir deploy_temp\sql 2>nul
copy zhihealth-cloud\docker\sql\*.sql deploy_temp\sql\ >nul 2>&1

REM 打包为tar.gz格式（Linux兼容）
echo.
echo 正在打包，请稍候...
tar -czvf zhihealth-deploy.tar.gz -C deploy_temp .

REM 显示结果
echo.
echo ============================================
echo   打包完成！
echo ============================================

for %%A in ("zhihealth-deploy.tar.gz") do (
    echo 文件名: zhihealth-deploy.tar.gz
    echo 大小: %%~zA bytes
)

echo.
echo 位置: e:\Health\zhihealth-deploy.tar.gz
echo.
echo 下一步操作:
echo   1. 上传到主节点: scp zhihealth-deploy.tar.gz root@182.92.1.136:/opt/
echo   2. 上传到从节点: scp zhihealth-deploy.tar.gz root@39.105.129.207:/opt/
echo.
echo 或者使用WinSCP/FileZilla图形化上传
echo ============================================

REM 清理临时目录
rmdir /s /q deploy_temp

pause
