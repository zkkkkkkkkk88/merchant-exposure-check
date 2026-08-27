# 见序操作手册

## 1. 启动服务

先运行数据库迁移，再用三个独立 PowerShell 窗口分别启动 API、worker 和网页。项目不会自动写入演示数据。

```powershell
cd services/api
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

```powershell
cd services/api
.\.venv\Scripts\python.exe -m app.scans.worker
```

```powershell
cd apps/web
npm.cmd run dev
```

## 2. 访问角色与安全配置

从示例文件复制配置后再填写本地值：`services/api/.env.example` 只包含 API 所需的 `ACCESS_AUTH_REQUIRED`、`INTERNAL_API_SECRET`；`apps/web/.env.example` 包含全部七个访问变量。示例文件保持空值，绝不放入真实凭据。

```dotenv
ACCESS_AUTH_REQUIRED=true
ACCESS_ADMIN_USERNAME=
ACCESS_ADMIN_PASSWORD_HASH=
ACCESS_DEMO_USERNAME=
ACCESS_DEMO_PASSWORD_HASH=
ACCESS_SESSION_SECRET=
INTERNAL_API_SECRET=
```

管理员凭据允许写入；演示凭据是只读权限。演示用户仍可浏览商家、问题、证据和报告，创建、保存、解析、生成、启动、重试、确认、上传、采用及清理等写操作会显示“当前为演示权限，实际操作请联系管理员。”。管理员切换商家和查看公开证据等只读流程不受影响。

为每个角色生成密码哈希：

```powershell
cd apps/web
node scripts/hash-access-password.mjs
```

生产环境请为 `ACCESS_SESSION_SECRET` 与 `INTERNAL_API_SECRET` 分别生成独立的高熵随机密钥，并仅通过部署环境注入。轮换 `ACCESS_SESSION_SECRET` 会签出所有用户；轮换 `INTERNAL_API_SECRET` 需要同步更新 API 与网页端配置。

## 3. 配置火山方舟

只在 `services/api/.env` 中设置 `ARK_API_KEY` 和 `ARK_MODEL`。当前验证可用的模型为 `doubao-seed-2-0-pro-260215`。账号还需开通 Responses API 与联网搜索服务。

## 4. 真实检测流程

1. 创建商家后进入“商家画像”，粘贴美团等公开页面中的资料。
2. 确认城市和精准品类，并按真实资料确认价格、商圈、服务、交通与使用场景；未确认事实不会进入问题。
3. 保存画像并生成精准问题，通过意图与分类标签筛选；编辑文字后移开焦点即可保存。
4. 批准并启用确实需要检测的问题。只有“已批准且已启用”的问题会进入任务。
5. 点击“开始后台检测”。任务创建后立即进入详情页，用户可以离开页面继续其他操作。
6. worker 在后台逐条执行，检测记录页会显示等待、运行、完成或部分失败状态。
7. 完成后在检测详情中核对逐题原始回答和引用，再进入报告查看指标。

如果 worker 没有启动，新任务不会丢失，而是保持“等待执行”。启动或重启 worker 后会继续从数据库领取排队任务。API 和 worker 必须读取同一个 `merchant-exposure.db` 与同一份 `.env` 配置。

## 5. 指标口径

- 可见性准备度：综合商家画像完整度、公开信息可验证度、高意图问题命中和来源覆盖得到的 0–100 分。
- 商家画像完整度：关键字段中已由用户确认的比例。
- 公开信息可验证度：已确认事实中带有可追溯公开来源的比例。
- 高意图问题命中：推荐意图问题中目标商家被提到的比例。
- 可见性阶段：未识别、信息相关、被提及、进入推荐四个阶段；用于描述当前样本中的进展，不是平台内部名次。
- 品牌出现率保留为辅助证据，不再作为主指标。
- 待核验：证据不足，只能作为线索，不能写成事实结论。

自动检测结果是公开联网回答的代理指标，不等同于豆包 App 固定排名，也不承诺能够控制平台内部排序。

## 6. 历史对比

历史页只比较真实完成的检测。少于两次有效检测时显示空状态，不生成模拟趋势。两次检测应尽量沿用相同问题版本、执行方式和样本规模。
