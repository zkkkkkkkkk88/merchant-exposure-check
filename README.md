# 商家公开信息曝光检测

一个基于真实公开联网回答的商家曝光检测项目。系统保存模型原始回答与引用来源，计算目标商家出现率、首位推荐率和来源覆盖率。检测结果只描述当前问题样本，不代表平台内部固定排名。

## 本地运行

项目正常运行需要三个独立进程，建议分别打开三个 PowerShell 窗口。API 负责保存和查询数据，worker 负责后台调用方舟，前端负责页面交互。

后端：

```powershell
cd services/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

在第二个 PowerShell 窗口启动 worker：

```powershell
cd services/api
.\.venv\Scripts\python.exe -m app.scans.worker
```

在第三个 PowerShell 窗口启动前端：

```powershell
cd apps/web
npm.cmd install
npm.cmd run dev
```

打开 `http://127.0.0.1:3000`。API 文档位于 `http://127.0.0.1:8000/docs`。

点击“开始后台检测”后页面会立即返回任务详情，不会等待模型逐条回答。关闭或离开页面不影响任务；如果 worker 暂停，任务会保留为“等待执行”，重新启动 worker 后继续领取。

## 配置

真实密钥只写入 `services/api/.env`：

```dotenv
DATABASE_URL=sqlite+pysqlite:///./merchant-exposure.db
ARK_API_KEY=
ARK_MODEL=doubao-seed-2-0-pro-260215
```

不要把 API Key 写入 `.env.example`、网页代码、提交记录或截图。火山方舟账号需要同时开通对应模型、Responses API 和联网搜索服务。

## 数据原则

- 生产页面只读取 API 中保存的真实数据；无数据时展示空状态。
- 不自动创建示例商家、模拟回答或模拟报告。
- 测试目录中的隔离样本只用于自动化测试，不会写入实际数据库。
- 原始回答保持只读；需要重跑时新建检测记录。

详细操作见 [操作手册](docs/operator-guide.md)。
