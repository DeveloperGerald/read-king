# ReadKing Frontend（React + Vite）

## 本地开发

```bash
npm install
npm run dev
```

## API 代理

开发环境下，Vite 会把 `/api/*` 代理到后端服务。

- 默认目标：`http://127.0.0.1:8001`
- 通过 `frontend/.env` 覆盖：

```bash
VITE_API_TARGET=http://127.0.0.1:8001
```

后端建议以 `--port 8001` 启动以保持默认配置开箱即用。
