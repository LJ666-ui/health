@echo off
chcp 65001 >nul
echo ============================================
echo   智康云枢 - 云服务器部署包打包工具
echo ============================================

set "sourceDir=e:\Health"
set "tempDir=%TEMP%\zhihealth-deploy"
set "zipFile=e:\Health\zhihealth-cloud-deploy.zip"

echo [1/4] 清理临时目录...
if exist "%tempDir%" rmdir /s /q "%tempDir%"
mkdir "%tempDir%"

echo [2/4] 复制项目文件（排除大文件）...
xcopy "%sourceDir%\deploy" "%tempDir%\deploy\" /E /I /Y >nul 2>&1
xcopy "%sourceDir%\zhihealth-cloud" "%tempDir%\zhihealth-cloud\" /E /I /Y >nul 2>&1
xcopy "%sourceDir%\zhihealth-frontend" "%tempDir%\zhihealth-frontend\" /E /I /Y >nul 2>&1
xcopy "%sourceDir%\zhihealth-python" "%tempDir%\zhihealth-python\" /E /I /Y >nul 2>&1
xcopy "%sourceDir%\docs" "%tempDir%\docs\" /E /I /Y >nul 2>&1
copy "%sourceDir%\.gitignore" "%tempDir%\" >nul 2>&1
copy "%sourceDir%\mysql-schema.sql" "%tempDir%\" >nul 2>&1

echo [3/4] 删除大文件和不需要的文件夹...
if exist "%tempDir%\zhihealth-cloud\docker\hive\downloads" rmdir /s /q "%tempDir%\zhihealth-cloud\docker\hive\downloads"
if exist "%tempDir%\zhihealth-frontend\node_modules" rmdir /s /q "%tempDir%\zhihealth-frontend\node_modules"
if exist "%tempDir%\zhihealth-frontend\dist" rmdir /s /q "%tempDir%\zhihealth-frontend\dist"
if exist "%tempDir%\zhihealth-cloud\target" rmdir /s /q "%tempDir%\zhihealth-cloud\target"
for /d %%d in ("%tempDir%\*") do if exist "%%d\node_modules" rmdir /s /q "%%d\node_modules"

echo [4/4] 压缩为ZIP...
if exist "%zipFile%" del "%zipFile%"

powershell -Command "Compress-Archive -Path '%tempDir%\*' -DestinationPath '%zipFile%' -Force"

echo.
echo ============================================
echo   ✅ 打包完成！
echo ============================================
echo   文件位置: %zipFile%
echo   文件大小:
for %%A in ("%zipFile%") do echo   %%~zA bytes (约 %%~zA/1048576 MB)
echo.
echo 下一步：
echo   1. 通过VNC/远程桌面连接云服务器
echo   2. 将此ZIP文件上传到服务器的 /opt 目录
echo   3. 解压并执行部署脚本
echo.
pause
