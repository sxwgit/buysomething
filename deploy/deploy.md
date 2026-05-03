# 采购管理系统 — 部署指南

## 1. 服务器要求

- 操作系统：Ubuntu 20.04 / 22.04 / 24.04
- Python 3.9+
- 内存：1G 足够
- 磁盘：预留 500M（含数据库和上传附件空间）

---

## 2. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx git
```

---

## 3. 创建部署目录

```bash
# 所有服务统一放在 /opt/services 下
sudo mkdir -p /opt/services
sudo chown $(whoami):$(whoami) /opt/services

# 克隆项目
cd /opt/services
git clone https://github.com/sxwgit/buysomething.git procurement
cd procurement
```

如果内网没有 git，可以从开发机打包上传：

```bash
# 开发机上执行
tar czf procurement.tar.gz --exclude=node_modules --exclude=__pycache__ --exclude=.git .
scp procurement.tar.gz user@服务器IP:/opt/services/

# 服务器上执行
cd /opt/services
mkdir procurement && cd procurement
tar xzf ../procurement.tar.gz
```

---

## 4. 创建 Python 虚拟环境并安装依赖

```bash
cd /opt/services/procurement

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

确认 gunicorn 已安装：

```bash
which gunicorn
# 应输出 /opt/services/procurement/.venv/bin/gunicorn
```

---

## 5. 初始化数据库

```bash
cd /opt/services/procurement
source .venv/bin/activate

# 初始化数据库，设置管理员密码
python init_db.py
# 提示输入密码，直接回车使用默认密码 admin123
```

数据库文件会自动创建在 `data/procurement.db`。

---

## 6. 构建前端（如果 dist 目录不存在）

如果 clone 下来的代码中 `frontend/dist/` 已存在（已在仓库中跟踪），可跳过此步。

否则需要构建：

```bash
# 需要先安装 Node.js（构建时用，服务器不需要常驻）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

cd /opt/services/procurement/frontend
npm install -g pnpm
pnpm install
pnpm build
# 构建产物在 frontend/dist/ 下
```

---

## 7. 配置 Gunicorn

项目根目录创建 `gunicorn.conf.py`（已包含在仓库中）：

```python
# gunicorn.conf.py
bind = "127.0.0.1:10001"
workers = 2
threads = 4
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

参数说明：

| 参数 | 值 | 含义 |
|------|-----|------|
| bind | 127.0.0.1:10001 | 只监听本地，由 nginx 代理对外 |
| workers | 2 | 工作进程数，一般设为 CPU 核数 × 2 + 1 |
| threads | 4 | 每个进程的线程数 |
| timeout | 120 | 请求超时（秒），导入大文件时需要较长 |
| keepalive | 5 | 保持连接的秒数 |
| accesslog | "-" | 访问日志输出到 stdout（被 systemd 接管） |

先手动测试能否正常启动：

```bash
cd /opt/services/procurement
source .venv/bin/activate
gunicorn -c gunicorn.conf.py "app:create_app()"

# 另一个终端测试
curl http://127.0.0.1:10001/
curl http://127.0.0.1:10001/admin/check

# 测试通过后 Ctrl+C 停掉
```

---

## 8. 配置 systemd 服务

将配置文件复制到 systemd 目录：

```bash
sudo cp /opt/services/procurement/deploy/systemd/procurement.service /etc/systemd/system/
sudo systemctl daemon-reload
```

启动并设置开机自启：

```bash
sudo systemctl start procurement
sudo systemctl enable procurement
```

验证：

```bash
sudo systemctl status procurement
# 应显示 active (running)

curl http://127.0.0.1:10001/admin/check
# 应返回 {"is_admin":false,"is_root":false,"username":""}
```

常用操作：

```bash
sudo systemctl start procurement       # 启动
sudo systemctl stop procurement        # 停止
sudo systemctl restart procurement     # 重启
sudo systemctl status procurement      # 查看状态
sudo journalctl -u procurement -f      # 查看实时日志
sudo journalctl -u procurement --since "1 hour ago"  # 查看最近 1 小时日志
```

---

## 9. 配置 Nginx 反向代理

将配置文件复制到 nginx 目录：

```bash
sudo cp /opt/services/procurement/deploy/nginx/procurement.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/procurement.conf /etc/nginx/sites-enabled/

# 检查配置是否正确
sudo nginx -t

# 重载 nginx
sudo systemctl reload nginx
```

验证：

```bash
# 在服务器上测试
curl http://127.0.0.1:10001/

# 在内网其他机器上用浏览器访问
# http://服务器IP:10001/
```

---

## 10. 防火墙（如果服务器启用了 ufw）

```bash
sudo ufw allow 10001/tcp
sudo ufw status
```

---

## 11. 日常维护

### 更新代码

```bash
cd /opt/services/procurement
git pull
source .venv/bin/activate
pip install -r requirements.txt    # 依赖有变化时执行

# 前端有变化时重新构建
cd frontend && pnpm build && cd ..

# 重启服务
sudo systemctl restart procurement
```

### 备份数据库

```bash
# SQLite 直接复制文件即可
cp /opt/services/procurement/data/procurement.db /backup/procurement_$(date +%Y%m%d).db
```

### 查看日志

```bash
# 实时查看最近日志
sudo journalctl -u procurement -f

# 查看最近 100 行
sudo journalctl -u procurement -n 100

# 查看错误日志
sudo journalctl -u procurement -p err
```

---

## 12. 常见问题

### Q: 启动报错 `Address already in use`

```bash
# 查看谁占用了端口
sudo lsof -i :10001
# 或
sudo ss -tlnp | grep 10001

# 如果是旧进程未退出，先停掉
sudo systemctl stop procurement
sudo kill $(sudo lsof -t -i:10001)
sudo systemctl start procurement
```

### Q: 页面能访问但 API 返回 502

gunicorn 进程可能崩溃了：

```bash
sudo systemctl status procurement
sudo journalctl -u procurement -n 50
```

### Q: 上传附件报错 413 Request Entity Too Large

nginx 默认限制上传大小为 1M，配置中已设置 `client_max_body_size 20m`，确认配置生效：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Q: 数据库锁定错误（SQLite 并发写入）

gunicorn 默认多 worker 同时写 SQLite 可能冲突。把 workers 降到 1 或使用 threads 模式：

```bash
# 编辑 gunicorn.conf.py
workers = 1
threads = 4
```
