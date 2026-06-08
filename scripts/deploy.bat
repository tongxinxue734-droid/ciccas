@echo off
chcp 65001 >nul
REM CICCAS Windows部署脚本

echo ============================================
echo CICCAS v3.0 Docker Deployment Script (Windows)
echo ============================================

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker未安装，请先安装Docker Desktop
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose未安装
    pause
    exit /b 1
)

echo ✅ Docker环境检查通过

REM 创建必要目录
echo 📁 创建数据目录...
if not exist data\raw mkdir data\raw
if not exist data\processed mkdir data\processed
if not exist data\backup mkdir data\backup
if not exist data\uploads mkdir data\uploads
if not exist logs mkdir logs
if not exist nginx\ssl mkdir nginx\ssl

REM 复制环境变量文件
if not exist .env (
    echo 📝 创建.env配置文件...
    copy .env.example .env
    echo ⚠️ 请修改.env文件中的数据库密码等配置
)

REM 构建并启动服务
echo 🐳 启动Docker服务...
docker-compose down -v 2>nul
docker-compose build --no-cache
docker-compose up -d

REM 等待MySQL初始化
echo ⏳ 等待数据库初始化...
timeout /t 30 /nobreak >nul

REM 检查服务状态
echo 🔍 检查服务状态...
docker-compose ps

echo.
echo ============================================
echo ✅ CICCAS部署成功！
echo ============================================
echo.
echo 📱 应用访问地址:
echo    - 主应用: http://localhost
echo    - 数据库管理: http://localhost:8080
echo.
echo 🔧 常用命令:
echo    - 查看日志: docker-compose logs -f
echo    - 停止服务: docker-compose down
echo    - 重启服务: docker-compose restart
echo.
echo 📊 数据库信息:
echo    - 主机: localhost:3306
echo    - 数据库: ciccas_db
echo    - 用户: ciccas_admin
echo    - phpMyAdmin: http://localhost:8080
echo ============================================

pause
