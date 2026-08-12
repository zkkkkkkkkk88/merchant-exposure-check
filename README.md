# 见序 · Visibility Dossier

一个基于真实公开联网回答的商家可见性诊断项目。系统先确认商家的城市、精准品类、价格、商圈、服务与场景，再生成匹配的推荐和核验问题；检测结果用于衡量画像完整度、公开信息可验证度、高意图问题命中与可见性准备度，不代表平台内部固定排名。

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

创建商家后，先进入“商家画像”粘贴美团等公开页面中的资料并逐项确认。系统只使用已确认事实生成问题，不会自行补写低价、亲子、交通方便等商家没有提供的条件。

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
# 手机版豆包实测

方舟联网检测用于批量预检，不等同于手机版豆包的真实推荐结果。进入“手机实测”后，系统会从已审核并启用的问题中固定抽取最多 15 道代表题。用户可一次粘贴多道手机问答，快速确认提及层级和竞品，并按轮次录入合并来源。

来源截图是可选证据，不要求每道问题上传，也不要求每轮重复上传完整来源列表。来源没有变化时可以沿用上一轮。确认后的手机版指标会与方舟指标分开统计，并生成目标商家与竞品的来源差距表。
