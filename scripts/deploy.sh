#!/bin/bash
# CICCAS 部署脚本

echo "============================================"
echo "CICCAS v3.0 Docker Deployment Script"
echo "============================================"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker Desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装"
    exit 1
fi

echo "✅ Docker环境检查通过"

# 创建必要目录
echo "📁 创建数据目录..."
mkdir -p data/{raw,processed,backup,uploads}
mkdir -p logs
mkdir -p nginx/ssl

# 复制环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建.env配置文件..."
    cp .env.example .env
    echo "⚠️  请修改.env文件中的数据库密码等配置"
fi

# 构建并启动服务
echo "🐳 启动Docker服务..."
docker-compose down -v 2>/dev/null || true
docker-compose build --no-cache
docker-compose up -d

# 等待MySQL初始化
echo "⏳ 等待数据库初始化..."
sleep 30

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 显示访问地址
echo ""
echo "============================================"
echo "✅ CICCAS部署成功！"
echo "============================================"
echo ""
echo "📱 应用访问地址:"
echo "   - 主应用: http://localhost"
echo "   - 数据库管理: http://localhost:8080"
echo ""
echo "🔧 常用命令:"
echo "   - 查看日志: docker-compose logs -f"
echo "   - 停止服务: docker-compose down"
echo "   - 重启服务: docker-compose restart"
echo ""
echo "📊 数据库信息:"
echo "   - 主机: localhost:3306"
echo "   - 数据库: ciccas_db"
echo "   - 用户: ciccas_admin"
echo "   - phpMyAdmin: http://localhost:8080"
echo "============================================"
