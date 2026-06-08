# CICCAS v3.0 - 中国城镇居民收入-消费耦合协调分析系统

## 🎯 项目概述

CICCAS (China Urban Residents Income-Consumption Coupling Analysis System) 是一个基于Docker容器化部署的全栈数据分析平台，专注于2010-2024年中国31个省级行政区城镇居民收入与消费的耦合关系研究。

### 核心特性

- 📊 **多源数据整合**: 支持国家统计局、Wind、地方统计局的Excel/CSV/API数据导入
- 🔬 **耦合协调度模型**: 实现容量耦合系数模型，自动计算C值和D值
- 📈 **高级计量分析**: VAR、PVAR、空间杜宾模型、GMM、门槛回归
- 🤖 **AI预测仿真**: LSTM-BiGRU混合模型，支持5-10年预测
- 🎯 **政策模拟器**: 收入分配政策效果预测沙盘
- 📚 **学术工具箱**: 自动生成实证段落、参考文献GB/T 7714格式导出

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Desktop                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │    Nginx    │  │   Streamlit  │  │  phpMyAdmin  │       │
│  │   (80/443) │  │   (8501)     │  │   (8080)     │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│         │                │                │               │
│  ┌──────┴────────────────┴────────────────┴──────┐       │
│  │               Docker Network                    │       │
│  └──────┬────────────────┬────────────────┬──────┘       │
│         │                │                │               │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐        │
│  │   MySQL    │  │   Redis    │  │   Worker   │        │
│  │   (3306)   │  │   (6379)   │  │            │        │
│  └────────────┘  └────────────┘  └────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.11 | 核心开发语言 |
| Streamlit | 1.29 | Web界面框架 |
| MySQL | 8.0 | 关系型数据库 |
| Redis | 7 | 缓存和消息队列 |
| Nginx | Alpine | 反向代理和负载均衡 |
| Plotly | 5.17 | 交互式可视化 |
| Pandas | 2.1 | 数据处理 |
| TensorFlow | 2.15 | 深度学习模型 |

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/CICCAS.git
cd CICCAS
```

### 2. 启动服务

```bash
# 一键启动所有服务
docker-compose up -d

# 等待服务启动（约30秒）
sleep 30

# 查看服务状态
docker-compose ps
```

### 3. 访问系统

- **主应用**: http://localhost
- **数据库管理**: http://localhost:8080 (用户名: ciccas_admin, 密码: CICCAS_Admin_2024)

### 4. 导入数据

```bash
# 生成示例数据并导入
docker exec ciccas_app python scripts/batch_import.py all
```

---

## 📂 项目结构

```
CICCAS/
├── docker-compose.yml          # Docker编排配置
├── .env                        # 环境变量配置
│
├── app/                        # 应用代码
│   ├── Dockerfile             # 应用镜像构建
│   ├── requirements.txt        # Python依赖
│   ├── main.py                 # Streamlit主应用
│   ├── pages/                  # 多页面模块
│   │   ├── data_governance.py
│   │   ├── coupling_analysis.py
│   │   ├── econometric_models.py
│   │   ├── ai_prediction.py
│   │   ├── calculator.py
│   │   ├── policy_simulator.py
│   │   └── academic_tools.py
│   └── utils/                  # 工具模块
│       ├── __init__.py
│       ├── database.py         # 数据库操作封装
│       ├── data_importer.py    # 数据导入处理
│       ├── calculation.py       # 耦合度计算
│       └── visualization.py   # 可视化组件
│
├── db/                         # 数据库配置
│   ├── init/
│   │   └── 01_init_schema.sql  # 初始化脚本
│   └── config/
│       └── my.cnf              # MySQL配置
│
├── nginx/                      # Nginx配置
│   └── nginx.conf              # 反向代理配置
│
├── scripts/                    # 运维脚本
│   └── batch_import.py         # 批量导入
│
├── data/                       # 数据目录（挂载卷）
│   ├── raw/                    # 原始数据
│   ├── processed/              # 处理后数据
│   └── backup/                 # 备份数据
│
└── docs/                       # 文档
    └── DEPLOYMENT_GUIDE.md     # 部署操作指南
```

---

## 📊 核心功能

### 1. 数据治理中心

- **多源接入**: 支持国家统计局API、Excel上传、本地数据库
- **数据清洗**: CPI平减、缺失值插值、异常值检测
- **质量监控**: 完整性、一致性、准确性校验
- **版本管理**: 数据版本追踪，支持回滚

### 2. 耦合协调分析

- **容量耦合系数模型**:
  - C = 2√(U₁ × U₂) / (U₁ + U₂) — 耦合度
  - D = √(C × T) — 协调度
  - T = αU₁ + βU₂ — 综合发展水平

- **分析维度**:
  - 省级面板分析
  - 区域对比分析
  - 时序演化分析
  - 空间自相关分析

### 3. 高级计量模型

| 模型 | 应用场景 | 输出结果 |
|------|----------|----------|
| VAR | 时序动态关系 | 脉冲响应、方差分解 |
| PVAR | 面板动态分析 | 区域异质性检验 |
| 空间杜宾 | 空间溢出效应 | 空间滞后系数 |
| GMM | 内生性问题 | 系统/差分GMM估计 |
| 门槛回归 | 非线性关系 | 门槛值、F统计量 |

### 4. AI预测仿真

- **LSTM-BiGRU混合模型**: 双向长短期记忆网络
- **多模型对比**: ARIMA-GARCH、Prophet、Transformer
- **预测评估**: MSE、RMSE、R²、MAPE
- **政策仿真**: 模拟不同政策情景下的耦合度变化

---

## 🛠️ 部署配置

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DB_HOST` | mysql | 数据库主机 |
| `DB_PORT` | 3306 | 数据库端口 |
| `DB_NAME` | ciccas_db | 数据库名 |
| `DB_USER` | ciccas_admin | 数据库用户 |
| `DB_PASSWORD` | CICCAS_Admin_2024 | 数据库密码 |
| `REDIS_HOST` | redis | Redis主机 |
| `REDIS_PORT` | 6379 | Redis端口 |

### 性能调优

```bash
# 增加Docker内存限制（推荐4GB+）
# Docker Desktop → Settings → Resources → Memory

# 调整MySQL配置（my.cnf）
innodb_buffer_pool_size = 512M
innodb_log_file_size = 128M
query_cache_size = 64M

# 调整Nginx worker进程
worker_processes auto;
worker_connections 1024;
```

---

## 📖 使用指南

### 数据导入流程

```mermaid
graph LR
    A[下载国家统计局数据] --> B[上传Excel文件]
    B --> C[数据格式验证]
    C --> D[CPI平减处理]
    D --> E[缺失值填充]
    E --> F[写入数据库]
    F --> G[自动计算耦合度]
```

### 耦合度计算流程

1. 进入"🔬 耦合协调分析"模块
2. 选择分析维度（省级/区域/全国）
3. 设置时间跨度（2010-2024）
4. 调整权重参数（默认α=β=0.5）
5. 点击"执行耦合分析"
6. 查看结果：耦合度C、协调度D、等级划分

### 论文写作辅助

1. 进入"📚 学术工具箱"
2. 选择"📝 实证段落"标签
3. 选择分析类型（描述性统计/耦合分析/收敛性检验）
4. 点击"生成段落"
5. 复制到论文中

---

## 🔧 运维命令

```bash
# 查看日志
docker-compose logs -f app
docker-compose logs -f mysql

# 数据库备份
docker exec ciccas_mysql mysqldump -u root -p ciccas_db > backup.sql

# 数据恢复
docker exec -i ciccas_mysql mysql -u root -p ciccas_db < backup.sql

# 重启服务
docker-compose restart app

# 更新代码后重建
docker-compose build --no-cache app
docker-compose up -d
```

---

## 📚 参考文献

1. 生延超, 李书昊, 李斌. 中国城镇居民收入与消费的耦合协调及影响因素研究[J]. 经济地理, 2023, 43(5): 25-35.
2. 王少平, 欧阳志刚. 中国城乡收入差距与经济增长的协整分析[J]. 经济研究, 2022, 57(3): 45-62.
3. 李实, 罗楚亮. 中国收入差距的实证分析[J]. 管理世界, 2022, 38(2): 15-28.

---

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 🤝 贡献

欢迎提交Issue和PR！

## 📧 联系

- 作者: [Your Name]
- 邮箱: [your.email@example.com]
- 项目地址: https://github.com/yourusername/CICCAS

---

*CICCAS Pro v3.0 - Docker Edition*
