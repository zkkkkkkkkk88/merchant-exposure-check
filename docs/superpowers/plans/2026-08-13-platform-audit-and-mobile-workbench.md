# 平台查缺与手机实测工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加只负责公开信息查缺的平台核实功能，并将手机实测页面整理为按任务阶段阅读的规范工作台。

**Architecture:** 平台查缺使用独立模型、服务、API 和 worker 处理器，核实轮次与当前商家隔离，公开检索结果保存为平台字段矩阵和证据。前端新增独立页面展示总览矩阵；手机实测仅重组现有数据和组件，不改变保存与分析规则。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、Pydantic、现有 Ark 搜索适配器、Next.js 16、React、pytest、Vitest。

## Global Constraints

- 系统只查缺，不自动登录、认领、修改或发布平台资料。
- “未检索到”不得表述为“未发布”。
- 无商家基准字段时标记“商家资料待补充”，不能判为平台冲突。
- 真实核实调用必须由用户另行确认，本次实施不触发联网扫描。
- 手机实测业务规则保持三道题、集中粘贴和统一确认不变。

---

### Task 1: 平台核实领域模型与状态判定

**Files:**
- Create: `services/api/app/platform_audits/models.py`
- Create: `services/api/app/platform_audits/schemas.py`
- Create: `services/api/app/platform_audits/service.py`
- Create: `services/api/migrations/versions/0008_platform_audits.py`
- Test: `services/api/tests/platform_audits/test_service.py`

**Interfaces:**
- Produces: `PlatformAuditService.create_run(merchant_id)`、`get_latest(merchant_id)`、`complete_platform(...)`，状态为 `complete|incomplete|conflict|not_found|needs_review`。

- [ ] 写失败测试覆盖创建轮次、跨商家隔离、字段缺失、字段冲突、未检索到和无基准字段。
- [ ] 运行目标测试确认因模块不存在失败。
- [ ] 实现模型、迁移、schemas 和纯状态判定服务。
- [ ] 运行平台服务测试确认通过。

### Task 2: API 与后台公开核实处理器

**Files:**
- Create: `services/api/app/platform_audits/router.py`
- Create: `services/api/app/platform_audits/worker.py`
- Modify: `services/api/app/main.py`
- Modify: `services/api/app/scans/worker.py`
- Test: `services/api/tests/platform_audits/test_router.py`
- Test: `services/api/tests/platform_audits/test_worker.py`

**Interfaces:**
- Produces: `POST /merchants/{id}/platform-audits`、`GET /merchants/{id}/platform-audits/latest`；worker 逐个平台调用现有 `SearchAdapter.search` 并保存结构化结果。

- [ ] 写失败的 API 和 worker 测试，使用本地 fake adapter，不产生外部请求。
- [ ] 实现创建/读取路由和固定第一阶段平台目录。
- [ ] 实现受约束 JSON 提示、保守解析和逐平台失败隔离。
- [ ] 将平台任务接入现有独立 worker 循环并运行测试。

### Task 3: 平台查缺总览矩阵页面

**Files:**
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/app/platform-audits/actions.ts`
- Create: `apps/web/src/app/platform-audits/page.tsx`
- Create: `apps/web/src/components/platform-audit-matrix.tsx`
- Modify: `apps/web/src/components/app-shell.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/platform-audits.test.tsx`

**Interfaces:**
- Consumes: 最新核实轮次及平台字段、证据和状态。
- Produces: A 方案总览统计、矩阵、异常详情折叠和窄屏摘要列表。

- [ ] 写失败页面测试，覆盖状态统计、谨慎措辞、异常展开和执行按钮。
- [ ] 扩展 contracts/API/action 并实现页面和矩阵组件。
- [ ] 增加导航入口、统一样式与窄屏转换。
- [ ] 运行前端目标测试确认通过。

### Task 4: 手机实测分阶段工作台布局

**Files:**
- Modify: `apps/web/src/components/mobile-check-workspace.tsx`
- Modify: `apps/web/src/components/mobile-recommendation-playbook.tsx`
- Modify: `apps/web/src/components/source-gap-table.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/mobile-checks.test.tsx`

**Interfaces:**
- Consumes: 现有 `MobileWorkspaceData`。
- Produces: 上一轮指标、当前步骤、上一轮记录、提升方案、证据与平台查缺的单列工作台。

- [ ] 写失败测试：无有效指标不显示四个 0%，完成状态显示步骤和规范顺序。
- [ ] 重组组件顺序并实现紧凑来源空状态。
- [ ] 统一卡片标题、按钮层级、步骤条和响应式样式。
- [ ] 运行手机实测测试、相关回归和生产构建。

### Task 5: 集成验证

**Files:**
- Test only; no production changes unless verification reveals a scoped defect.

- [ ] 运行后端平台、手机实测和 worker 测试。
- [ ] 运行前端平台查缺、手机实测和真实数据页面测试。
- [ ] 运行 Next.js 生产构建和 `git diff --check`。
- [ ] 重启 API，实际检查两个页面的桌面和窄屏布局；不启动真实平台核实。
