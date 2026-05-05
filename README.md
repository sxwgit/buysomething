# 采购管理系统

企业内部采购申请、跟踪、附件归档与数据透视分析的 Web 系统。

## 功能概览

| 模块 | 能力 |
|------|------|
| 采购列表 | 多条件筛选、服务端分页、行内编辑、批量操作、Excel 导入导出 |
| 附件管理 | 按月按部门归档、上传覆盖率检查、文件下载 |
| 透视报表 | 业务看板、部门汇总、种类分布、月度趋势、交叉矩阵、图表导出 |
| 系统设置 | 下拉选项维护、管理员账号管理、密码修改 |

## 技术架构

```
┌─────────────────────────────────────────────────┐
│  Vue 3 + Vite + ECharts                         │  前端 SPA
│  frontend/src/App.vue                           │
└──────────────────────┬──────────────────────────┘
                       │  /api/*  /admin/*
┌──────────────────────▼──────────────────────────┐
│  Flask + SQLAlchemy + Gunicorn                   │  后端 API
│  app.py → routes/*.py → models.py               │
└──────────────────────┬──────────────────────────┘
                       │
              ┌────────▼────────┐
              │  SQLite          │  数据库
              │  data/procurement.db
              └─────────────────┘
```

- **后端**: Python 3.9+ / Flask / SQLAlchemy / SQLite
- **前端**: Vue 3 / Vite / ECharts / Lucide Icons
- **部署**: Gunicorn + Nginx + systemd

## 项目结构

```
.
├── app.py                 # Flask 入口，注册蓝图，提供 SPA 页面
├── config.py              # 配置（数据库路径、密钥、上传限制）
├── models.py              # 数据模型（6 张表）
├── init_db.py             # 数据库初始化脚本
├── gunicorn.conf.py       # Gunicorn 生产环境配置
├── requirements.txt       # Python 依赖
│
├── routes/                # 后端 API 路由（按业务拆分）
│   ├── procurement.py     #   采购 CRUD、筛选、汇总、批量操作
│   ├── attachment.py      #   附件上传、下载、覆盖率检查
│   ├── report.py          #   报表查询、Excel 导出
│   ├── data_import.py     #   Excel 导入、模板下载、数据导出
│   ├── admin.py           #   管理员认证、账号管理
│   └── settings.py        #   下拉选项 CRUD
│
├── frontend/              # Vue 3 前端
│   ├── src/
│   │   ├── App.vue        #   全部页面和逻辑（SPA 单文件）
│   │   ├── main.js        #   入口
│   │   └── styles.css     #   全局样式
│   ├── index.html
│   ├── vite.config.js     #   Vite 配置（开发代理）
│   └── package.json
│
├── deploy/                # 部署相关
│   ├── deploy.md          #   完整部署指南
│   ├── manage.sh          #   多服务统一管理脚本
│   ├── systemd/           #   systemd 服务配置
│   │   ├── procurement.service
│   │   └── _template.service
│   └── nginx/             #   Nginx 反向代理配置
│       ├── procurement.conf
│       └── multi-service.conf
│
├── data/                  # SQLite 数据库（运行时生成）
└── uploads/attachments/   # 上传附件存储目录
```

## 数据模型

| 表 | 用途 |
|----|------|
| Procurement | 采购主表，16 个业务字段，逻辑删除 |
| Attachment | 附件记录，关联年/月/部门 |
| DropdownOption | 通用下拉选项（资产分类、部门、状态） |
| AdminUser | 管理员账号，支持根管理员分级 |
| AdminPassword | 旧版密码表（兼容迁移） |
| DataVersion | 数据版本号，驱动前端轮询刷新 |

## 权限设计

- 未登录用户：可查看所有数据，不可增删改
- 普通管理员：可增删改采购数据、上传附件
- 根管理员：额外可管理管理员账号

认证方式：Session + 2 小时过期。

## 本地开发

### 后端

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python init_db.py                  # 首次运行，初始化数据库
python app.py                      # 启动 Flask，监听 0.0.0.0:5000
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev                           # 启动 Vite，监听 0.0.0.0:5173
```

Vite 开发服务器会自动将 `/api`、`/admin`、`/uploads` 请求代理到 Flask（端口 5001）。

生产模式不需要 Vite，由 Flask 直接提供 `frontend/dist/` 构建产物。

### 构建前端

```bash
cd frontend && pnpm build
# 产物在 frontend/dist/ 下
```

## API 一览

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/procurements | 采购列表（分页+筛选） | - |
| GET | /api/procurements/summary | 汇总统计 | - |
| GET | /api/procurements/filter-metadata | 筛选器元数据 | - |
| GET | /api/procurements/:id | 单条详情 | - |
| POST | /api/procurements | 新增 | 管理员 |
| PUT | /api/procurements/:id | 修改 | 管理员 |
| DELETE | /api/procurements/:id | 删除（软删除） | 管理员 |
| POST | /api/procurements/batch-status | 批量改状态 | 管理员 |
| GET | /api/attachments | 附件列表 | - |
| GET | /api/attachments/coverage | 上传覆盖率 | - |
| POST | /api/attachments/upload | 上传附件 | 管理员 |
| GET | /api/attachments/:id/download | 下载附件 | - |
| DELETE | /api/attachments/:id | 删除附件 | 管理员 |
| GET | /api/reports/overview | 业务看板 | - |
| GET | /api/reports/department-summary | 部门汇总 | - |
| GET | /api/reports/department-ratio | 部门占比 | - |
| GET | /api/reports/category-distribution | 种类分布 | - |
| GET | /api/reports/monthly-trend | 月度趋势 | - |
| GET | /api/reports/department-category-matrix | 交叉矩阵 | - |
| GET | /api/reports/export | Excel 导出 | 管理员 |
| GET | /api/options/:category | 下拉选项 | - |
| POST | /api/options | 新增选项 | 管理员 |
| PUT | /api/options/:id | 修改选项 | 管理员 |
| DELETE | /api/options/:id | 删除选项 | 管理员 |
| GET | /api/import/template | 下载导入模板 | - |
| GET | /api/import/export-data | 全量导出 | 管理员 |
| POST | /api/import/excel | Excel 导入 | 管理员 |
| GET | /api/data-version | 数据版本号 | - |
| POST | /admin/login | 管理员登录 | - |
| POST | /admin/logout | 管理员登出 | - |
| GET | /admin/check | 检查登录状态 | - |
| POST | /api/admin/change-password | 修改密码 | 管理员 |
| GET | /api/admin/users | 管理员列表 | 根管理员 |
| POST | /api/admin/users | 新增管理员 | 根管理员 |
| DELETE | /api/admin/users/:id | 删除管理员 | 根管理员 |

---

## 部署与多服务管理

以下内容适用于将本系统和其他服务统一部署到内网 Ubuntu 服务器。

### 部署方式

完整操作步骤见 [deploy/deploy.md](deploy/deploy.md)，核心流程：

```bash
# 1. 克隆项目到 /opt/services/procurement
# 2. 创建 venv、安装依赖、初始化数据库
# 3. 注册 systemd 服务
sudo cp deploy/systemd/procurement.service /etc/systemd/system/
sudo systemctl enable --now procurement
# 4. 配置 nginx 反向代理
sudo cp deploy/nginx/procurement.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/procurement.conf /etc/nginx/sites-enabled/
sudo systemctl reload nginx
# 5. 访问 http://服务器IP:10001/
```

### 多服务统一管理

所有服务遵循统一规范：

| 规范 | 约定 |
|------|------|
| 代码目录 | `/opt/services/<服务名>/` |
| 端口分配 | 10001, 10002, 10003... 顺序递增 |
| 进程管理 | systemd，每个服务一个 `.service` 文件 |
| 反向代理 | nginx，每个服务一个 `.conf` 文件 |
| 管理工具 | `/opt/services/manage.sh` |

#### manage.sh 使用

```bash
./manage.sh list                    # 列出所有服务及端口
./manage.sh status                  # 一眼看所有服务运行状态
./manage.sh status procurement      # 查看单个服务
./manage.sh start procurement       # 启动
./manage.sh stop procurement        # 停止
./manage.sh restart procurement     # 重启
./manage.sh logs procurement        # 实时日志（Ctrl+C 退出）
./manage.sh logs procurement 100    # 最近 100 行日志
```

#### 新增服务的步骤

```bash
# 1. 放代码到 /opt/services/新服务名/
# 2. 复制 systemd 模板并修改
sudo cp /opt/services/procurement/deploy/systemd/_template.service \
        /etc/systemd/system/新服务名.service
sudo vim /etc/systemd/system/新服务名.service     # 改 WorkingDirectory、ExecStart

# 3. 添加 nginx 配置
sudo vim /etc/nginx/sites-available/新服务名.conf  # listen 10002; proxy_pass 127.0.0.1:10002
sudo ln -s /etc/nginx/sites-available/新服务名.conf /etc/nginx/sites-enabled/

# 4. 注册到 manage.sh 的 SERVICES 数组
# 5. 启用
sudo systemctl daemon-reload
sudo systemctl enable --now 新服务名
sudo nginx -t && sudo systemctl reload nginx
```

### 相关配置文件

| 文件 | 用途 |
|------|------|
| [deploy/deploy.md](deploy/deploy.md) | 完整部署指南（12 个章节） |
| [deploy/manage.sh](deploy/manage.sh) | 多服务统一管理脚本 |
| [deploy/systemd/procurement.service](deploy/systemd/procurement.service) | 本项目 systemd 配置 |
| [deploy/systemd/_template.service](deploy/systemd/_template.service) | 通用 systemd 模板 |
| [deploy/nginx/procurement.conf](deploy/nginx/procurement.conf) | 本项目 nginx 配置 |
| [deploy/nginx/multi-service.conf](deploy/nginx/multi-service.conf) | 多服务 nginx 配置示例 |
| [gunicorn.conf.py](gunicorn.conf.py) | Gunicorn 生产配置 |
