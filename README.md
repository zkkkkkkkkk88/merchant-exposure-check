# AI 商家曝光检测

一个面向本地商家的公开信息曝光检测 MVP。系统保存原始联网回答与引用来源，识别目标商家和竞争品牌，计算确定性指标，并生成可追溯的信息缺口报告。

## 本地开发

### 后端

```powershell
cd services/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.seed_demo
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### 前端

```powershell
cd apps/web
npm.cmd install
npm.cmd test
npm.cmd run dev
```

### Docker Compose

复制 `.env.example` 为 `.env`，再运行：

```powershell
docker compose up --build
```

`worker` 服务通过 `--profile scans` 启动。`ARK_API_KEY` 只允许配置在服务端环境中；手动导入模式不需要该密钥。

## 演示与验证

`python -m scripts.seed_demo` 会幂等创建 O'eat 示例商家、30 条已批准问题和一次无需网络的人工检测。详细流程见 [操作手册](docs/operator-guide.md)。

```powershell
cd apps/web
npm.cmd test
npx.cmd playwright test e2e/demo-flow.spec.ts
```

自动检测结果是豆包相关联网搜索的代理指标，不等同于豆包 App 固定排名。
