# 见序 · Visibility Dossier

一个基于真实公开联网回答的商家可见性诊断项目。系统先确认商家的城市、精准品类、价格、商圈、服务与场景，再生成匹配的推荐和核验问题；检测结果用于衡量画像完整度、公开信息可验证度、高意图问题命中与可见性准备度，不代表平台内部固定排名。

## 本地运行

### Windows 一键启动

首次运行仍需按照下方步骤安装依赖，并按“配置”章节创建本地 `.env` 文件。之后在项目根目录运行：

```powershell
.\scripts\start-dev.cmd
```

脚本会先执行数据库迁移，再统一启动 API、后台 worker 和前端，并等待服务就绪。停止由脚本启动的进程：

```powershell
.\scripts\stop-dev.cmd
```

页面左下角会显示 API、后台任务以及豆包、高德和腾讯地图的配置状态。普通开发命令固定使用 Webpack，避免工作树共享 `node_modules` 时触发 Turbopack 软链接错误。

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

复制 `services/api/.env.example` 到 `services/api/.env`，复制 `apps/web/.env.example` 到 `apps/web/.env.local`，再填写本机或部署环境的配置。API 只接收 `ACCESS_AUTH_REQUIRED` 与 `INTERNAL_API_SECRET`；网页端接收下面七个访问变量：

```dotenv
ACCESS_AUTH_REQUIRED=true
ACCESS_ADMIN_USERNAME=
ACCESS_ADMIN_PASSWORD_HASH=
ACCESS_DEMO_USERNAME=
ACCESS_DEMO_PASSWORD_HASH=
ACCESS_SESSION_SECRET=
INTERNAL_API_SECRET=
```

不要把密码、密码哈希、会话密钥、内部 API 密钥或 API Key 写入示例文件、网页代码、提交记录或截图。生产环境中的 `ACCESS_SESSION_SECRET` 与 `INTERNAL_API_SECRET` 必须分别生成、彼此独立的高熵随机密钥。火山方舟配置仍只写入 `services/api/.env`，账号需要同时开通对应模型、Responses API 和联网搜索服务。

生成密码哈希时在网页项目目录运行交互式命令（输入内容不会写入仓库）：

```powershell
cd apps/web
node scripts/hash-access-password.mjs
```

管理员凭据允许创建、保存、生成、启动、重试和采用等写操作；演示凭据只能读取数据，网页会显示“演示模式”并解释被锁定的操作。轮换 `ACCESS_SESSION_SECRET` 会使所有现有会话失效并要求重新登录。详细角色边界与值班流程见 [操作手册](docs/operator-guide.md)。

## 数据原则

- 生产页面只读取 API 中保存的真实数据；无数据时展示空状态。
- 不自动创建示例商家、模拟回答或模拟报告。
- 测试目录中的隔离样本只用于自动化测试，不会写入实际数据库。
- 原始回答保持只读；需要重跑时新建检测记录。

详细操作见 [操作手册](docs/operator-guide.md)。
# 手机版豆包实测

方舟联网检测用于批量预检，不等同于手机版豆包的真实推荐结果。进入“手机实测”后，系统会从 10–20 道已审核候选题中固定选择 3 道代表题，并要求分别开启 3 个独立新对话。用户可一次粘贴 3 道手机问答，快速确认提及层级和竞品，并按轮次录入合并来源。

来源截图是可选证据，不要求每道问题上传，也不要求每轮重复上传完整来源列表。来源没有变化时可以沿用上一轮。确认后的手机版指标会与方舟指标分开统计，并生成目标商家与竞品的来源差距表。
