# CICCAS Docker 部署与操作管理文档

## 📋 系统概述

**CICCAS v3.0** (China Urban Residents Income-Consumption Coupling Analysis System)

- **架构**: Docker Compose 微服务架构
- **技术栈**: Python 3.11 + Streamlit + MySQL 8.0 + Redis 7 + Nginx
- **功能**: 城镇居民收入-消费耦合协调分析系统，支持数据导入、耦合度计算、计量分析、AI预测等

---

## 🚀 快速部署

### 1. 环境准备

**必要条件:**
- Docker Desktop 4.0+ (Windows/Mac) 或 Docker Engine 20.10+ (Linux)
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 10GB 磁盘空间

**安装Docker Desktop:**

Windows用户:
```powershell
# 1. 下载安装包
https://www.docker.com/products/docker-desktop

# 2. 安装后验证
docker --version
docker-compose --version
```

### 2. 项目部署

```bash
# 1. 克隆/解压项目到本地目录
cd CICCAS

# 2. 创建必要目录
mkdir -p data/{raw,processed,backup} logs

# 3. 启动所有服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f
```

### 3. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| 主应用 | http://localhost | Streamlit应用入口 |
| 数据库管理 | http://localhost:8080 | phpMyAdmin |
| 数据库直连 | localhost:3306 | MySQL连接 |
| Redis缓存 | localhost:6379 | Redis连接 |

---

## 📊 数据库管理

### MySQL 数据库配置

**连接信息:**
```
主机: localhost:3306
数据库: ciccas_db
用户名: ciccas_admin
密码: CICCAS_Admin_2024
root密码: CICCAS_2024_Secure
```

**使用phpMyAdmin管理:**
1. 访问 http://localhost:8080
2. 服务器: `mysql`
3. 用户名: `ciccas_admin`
4. 密码: `CICCAS_Admin_2024`

**使用命令行:**
```bash
# 进入MySQL容器
docker exec -it ciccas_mysql mysql -u ciccas_admin -p

# 选择数据库
USE ciccas_db;

# 查看表结构
SHOW TABLES;
DESCRIBE income_data;
DESCRIBE consumption_data;
```

### 数据库表结构

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `provinces` | 省份基础信息 | province_code, region_type |
| `income_data` | 收入数据 | disposable_income, real_income, data_source |
| `consumption_data` | 消费数据 | consumption_expenditure, 八大类消费 |
| `macro_indicators` | 宏观经济指标 | cpi, unemployment_rate, urbanization_rate |
| `coupling_results` | 耦合协调度计算结果 | coupling_degree_c, coordination_degree_d |
| `spatial_analysis` | 空间分析结果 | moran_i, sigma_convergence |
| `econometric_models` | 计量模型结果 | model_params, r_squared |
| `data_import_log` | 数据导入日志 | import_batch_id, processing_status |

---

## 📥 数据导入操作

### 方式一：网页上传（推荐）

1. 进入系统 → 📥 数据治理中心 → 数据导入
2. 选择数据源类型：国家统计局/本地文件/API
3. 上传Excel/CSV文件
4. 系统自动进行：格式验证 → CPI平减 → 缺失值填充 → 数据入库

### 方式二：命令行导入

```bash
# 进入应用容器
docker exec -it ciccas_app bash

# 执行导入脚本
python -c "
from utils.data_importer import IncomeDataImporter
importer = IncomeDataImporter()
importer.import_from_excel(
    '/app/data/raw/income_2024.xlsx',
    year=2024,
    data_source='国家统计局'
)
"
```

### 方式三：批量导入脚本

```bash
# 准备数据文件
# 放在 data/raw/ 目录下:
# - income_2010.xlsx ~ income_2024.xlsx
# - consumption_2010.xlsx ~ consumption_2024.xlsx

# 执行批量导入
docker exec ciccas_app python scripts/batch_import.py
```

### 数据格式要求

**收入数据Excel格式:**
| 列名 | 说明 | 示例 |
|------|------|------|
| 省份 | 省份名称 | 北京 |
| 人均可支配收入 | 元 | 77441 |
| 工资性收入 | 元 | 50000 |
| 经营净收入 | 元 | 8000 |
| 财产净收入 | 元 | 10000 |
| 转移净收入 | 元 | 9441 |

**消费数据Excel格式:**
| 列名 | 说明 | 示例 |
|------|------|------|
| 省份 | 省份名称 | 北京 |
| 人均消费支出 | 元 | 44585 |
| 食品烟酒 | 元 | 12000 |
| 衣着 | 元 | 2500 |
| 居住 | 元 | 15000 |
| ... | ... | ... |

---

## 🔧 日常运维命令

### 查看服务状态

```bash
# 查看所有服务
docker-compose ps

# 查看特定服务
docker-compose ps mysql
docker-compose ps app

# 查看资源使用
docker stats
```

### 查看日志

```bash
# 查看所有日志
docker-compose logs

# 查看特定服务日志
docker-compose logs -f mysql
docker-compose logs -f app

# 查看最近100行
docker-compose logs --tail=100 app
```

### 重启服务

```bash
# 重启单个服务
docker-compose restart app
docker-compose restart mysql

# 重启所有服务
docker-compose restart

# 重建并重启（代码更新后）
docker-compose up -d --build app
```

### 数据备份

```bash
# 1. 备份数据库
docker exec ciccas_mysql mysqldump -u ciccas_admin -pCICCAS_Admin_2024 ciccas_db > backup/ciccas_backup_$(date +%Y%m%d).sql

# 2. 备份数据目录
tar -czvf backup/data_backup_$(date +%Y%m%d).tar.gz data/

# 3. 自动备份脚本（添加到crontab）
0 2 * * * cd /path/to/CICCAS && ./scripts/backup.sh
```

### 数据恢复

```bash
# 恢复数据库
docker exec -i ciccas_mysql mysql -u ciccas_admin -pCICCAS_Admin_2024 ciccas_db < backup/ciccas_backup_20240101.sql

# 恢复数据文件
tar -xzvf backup/data_backup_20240101.tar.gz
```

---

## 🔄 系统更新

### 更新应用代码

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建应用镜像
docker-compose build --no-cache app

# 3. 重启服务
docker-compose up -d

# 4. 验证更新
docker-compose logs app | tail -20
```

### 更新数据库Schema

```bash
# 进入MySQL容器
docker exec -it ciccas_mysql bash

# 执行迁移脚本
mysql -u ciccas_admin -p ciccas_db < /docker-entrypoint-initdb.d/migration_v2.sql
```

---

## 🐛 故障排查

### 常见问题

**问题1: 数据库连接失败**
```bash
# 检查MySQL容器状态
docker-compose ps mysql

# 查看MySQL日志
docker-compose logs mysql

# 重置MySQL数据（注意：会丢失数据！）
docker-compose down -v
docker-compose up -d mysql
```

**问题2: 应用无法启动**
```bash
# 检查依赖安装
docker-compose exec app pip list

# 重新构建应用
docker-compose build --no-cache app
docker-compose up -d app
```

**问题3: 内存不足**
```bash
# 增加Docker内存限制
# Docker Desktop → Settings → Resources → Memory → 4GB+

# 清理未使用的容器和镜像
docker system prune -a
```

### 性能优化

```bash
# 查看数据库慢查询
# 在phpMyAdmin → SQL中执行：
SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;

# 优化查询缓存
# 在my.cnf中配置query_cache_size

# 监控Redis缓存
docker exec ciccas_redis redis-cli info stats
```

---

## 📈 系统监控

### 内置监控

访问系统首页 → 系统状态卡片可查看:
- 数据库连接状态
- 数据完整率
- 系统运行时间
- 缓存命中率

### 外部监控（可选）

```bash
# 安装cAdvisor监控容器
docker run -d \
  --name=cadvisor \
  -p 8081:8080 \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  google/cadvisor:latest
```

---

## 🔒 安全设置

### 修改默认密码

```bash
# 1. 修改MySQL密码
docker exec -it ciccas_mysql mysql -u root -p

ALTER USER 'ciccas_admin'@'%' IDENTIFIED BY '新密码';
FLUSH PRIVILEGES;

# 2. 更新docker-compose.yml中的环境变量
# 3. 重启服务
```

### 配置HTTPS

```bash
# 1. 生成SSL证书
mkdir nginx/ssl
cd nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ciccas.key -out ciccas.crt

# 2. 启用nginx配置中的HTTPS部分
# 3. 重启nginx
docker-compose restart nginx
```

---

## 📞 技术支持

**系统版本**: CICCAS Pro v3.0 Docker Edition
**技术栈**: Python 3.11, Streamlit 1.29, MySQL 8.0, Redis 7
**许可证**: MIT License

**常见问题:**
- 数据库问题查看 `docker-compose logs mysql`
- 应用问题查看 `docker-compose logs app`
- 网络问题检查 `docker network ls`

---

*文档最后更新: 2024年12月*
