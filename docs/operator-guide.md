# 商家曝光检测操作手册

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

## 2. 配置火山方舟

只在 `services/api/.env` 中设置 `ARK_API_KEY` 和 `ARK_MODEL`。当前验证可用的模型为 `doubao-seed-2-0-pro-260215`。账号还需开通 Responses API 与联网搜索服务。

## 3. 真实检测流程

1. 创建商家并填写名称、城市、行业和可核验公开来源。
2. 生成问题库，通过分类标签筛选问题；编辑文字后移开焦点即可保存。
3. 批准并启用确实需要检测的问题。只有“已批准且已启用”的问题会进入任务。
4. 点击“开始后台检测”。任务创建后立即进入详情页，用户可以离开页面继续其他操作。
5. worker 在后台逐条执行，检测记录页会显示等待、运行、完成或部分失败状态。
6. 完成后在检测详情中核对逐题原始回答和引用，再进入报告查看指标。

如果 worker 没有启动，新任务不会丢失，而是保持“等待执行”。启动或重启 worker 后会继续从数据库领取排队任务。API 和 worker 必须读取同一个 `merchant-exposure.db` 与同一份 `.env` 配置。

## 4. 指标口径

- 品牌出现率：有效回答中提到目标商家的比例。
- 首位推荐率：存在明确排序的有效回答中，目标商家位于第一的比例。
- 来源覆盖率：目标商家被提及时，同时带有已保存公开来源的比例。
- 待核验：证据不足，只能作为线索，不能写成事实结论。

自动检测结果是公开联网回答的代理指标，不等同于豆包 App 固定排名，也不承诺能够控制平台内部排序。

## 5. 历史对比

历史页只比较真实完成的检测。少于两次有效检测时显示空状态，不生成模拟趋势。两次检测应尽量沿用相同问题版本、执行方式和样本规模。
