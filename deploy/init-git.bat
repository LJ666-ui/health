@echo off
chcp 65001 >nul
REM ============================================================
REM  智康云枢 - Git仓库初始化 + 推送工具
REM  用途: 将项目推送到Gitee/GitHub，然后云服务器可clone
REM ============================================================

echo ============================================
echo   智康云枢 Git 初始化与推送工具
echo ============================================

cd /d e:\Health

REM 检查是否已初始化Git
if not exist ".git" (
    echo [1/5] 初始化Git仓库...
    git init
    echo [2/5] 创建.gitignore文件...
    call :create_gitignore
) else (
    echo [1/5] Git仓库已存在，跳过初始化
)

echo [3/5] 添加所有文件到暂存区...
git add .

echo [4/5] 创建初始提交...
git commit -m "Initial commit: ZhiHealth Cloud v1.0 - Full microservices deployment package"

echo.
echo 请选择远程仓库平台:
echo   1. Gitee (推荐 - 国内速度快)
echo   2. GitHub
echo   3. 跳过（稍后手动添加）
set /p choice=请输入选项 (1/2/3):

if "%choice%"=="1" goto gitee
if "%choice%"=="2" goto github
if "%choice%"=="3" goto end

:gitee
echo.
echo ============================================
echo   Gitee 推送配置
echo ============================================
set /p gitee_url=请输入Gitee仓库地址 (例如: https://gitee.com/yourname/zhihealth.git):
if "%gitee_url%"=="" (
    echo ❌ 地址不能为空
    goto end
)
git remote add origin %gitee_url%
echo [5/5] 推送到Gitee...
git push -u origin main 2>nul || git push -u origin master
goto success

:github
echo.
echo ============================================
echo   GitHub 推送配置
echo ============================================
set /p github_url=请输入GitHub仓库地址 (例如: https://github.com/yourname/zhihealth.git):
if "%github_url%"=="" (
    echo ❌ 地址不能为空
    goto end
)
git remote add origin %github_url%
echo [5/5] 推送到GitHub...
git push -u origin main 2>nul || git push -u origin master
goto success

:success
echo.
echo ============================================
echo   ✅ 推送成功！
echo ============================================
echo.
echo 下一步：在云服务器执行以下命令:
echo.
echo   主节点 (182.92.1.136):
echo     ssh root@182.92.1.136
echo     cd /opt && git clone 你的仓库地址 zhihealth && cd zhihealth/deploy && bash deploy-master-git.sh
echo.
echo   从节点 (39.105.129.207):
echo     ssh root@39.105.129.207
echo     cd /opt && mkdir zhihealth && cd zhihealth && scp -r root@182.92.1.136:/opt/zhihealth/deploy ./deploy && cd deploy && bash deploy-slave-git.sh
echo.
goto end

:end
pause
exit /b 0

:create_gitignore>(
# Dependencies
node_modules/
target/
*.jar
*.war
*.class

# IDE
.idea/
*.iml
.vscode/

# OS
.DS_Store
Thumbs.db

# Env
.env
.env.local

# Logs
logs/
*.log

# Docker volumes (server side)
data/
backups/
)
goto :eof
