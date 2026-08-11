# AI 商家曝光检测

一个面向本地商家的公开信息曝光检测 MVP。系统保存原始联网回答与引用来源，识别目标商家和竞争品牌，计算确定性指标，并生成可追溯的信息缺口报告。

## 本地开发

### 后端

```powershell
cd services/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
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

`worker` 服务将在检测执行功能完成后通过 `--profile scans` 启动。`ARK_API_KEY` 只允许配置在服务端环境中；手动导入模式不需要该密钥。

## 当前阶段

项目按 [实施计划](docs/superpowers/plans/2026-08-11-doubao-geo-mvp.md) 分阶段构建。自动检测结果是豆包相关联网搜索的代理指标，不等同于豆包 App 固定排名。
