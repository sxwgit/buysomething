# Vue 前端说明

这个目录是采购管理系统的新前端实现，使用 `Vue 3 + Vite`，后端仍沿用现有 Flask API。

## 开发运行

先启动 Flask 后端：

```bash
python3 -c "from app import app; app.run(debug=True, host='0.0.0.0', port=5001)"
```

再启动前端：

```bash
cd frontend
pnpm install
pnpm dev
```

访问：

```text
http://127.0.0.1:5173/
```

## 代理关系

`vite.config.js` 会把这些请求代理到 Flask：

- `/api`
- `/admin`
- `/uploads`

因此前端代码可以继续使用原来的接口路径，不需要在业务代码里写死后端地址。
