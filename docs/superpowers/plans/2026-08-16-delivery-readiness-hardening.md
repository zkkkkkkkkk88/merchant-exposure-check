# Delivery Readiness Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复项目复查中影响交付可信度的后台任务、题库、进度口径与前端展示问题，使当前六步流程状态一致、可执行、可解释。

**Architecture:** 保留现有 FastAPI、SQLAlchemy、Next.js 架构。后端以单一判定函数统一题库与复测状态，worker 增加监督循环与可诊断日志；前端只消费明确状态并把内部字段转换为商家语言。每项修改采用测试先行，不调用新的外部 API。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy、pytest、Next.js 16、React、TypeScript、Vitest。

## Global Constraints

- 不改变“手机版豆包实测固定 3 个独立对话”的产品约束。
- 口腔商家使用“民营口腔门诊或诊所”，餐饮等其他行业保持原有品类语义。
- 历史题目和检测结果不得删除；新题库生成后只归档旧题库。
- 不新增外部依赖，不消耗豆包或地图 API 配额完成验证。
- 页面必须同时适配桌面和 390px 小屏。

---

### Task 1: Worker 监督循环与启动诊断

**Files:**
- Modify: `services/api/app/scans/worker.py`
- Modify: `scripts/start-dev.ps1`
- Test: `services/api/tests/scans/test_worker.py`
- Test: `services/api/tests/test_dev_startup.py`

**Interfaces:**
- Produces: `run_worker_cycle(...) -> tuple[UUID | None, UUID | None, UUID | None]`；单轮异常由监督循环记录后继续运行。
- Produces: 启动脚本等待 `worker-heartbeat.json` 更新，并将三个进程输出写入 `.runtime/*.log`。

- [ ] 编写失败测试：单个处理器抛出未预期异常时，worker 监督循环不会永久退出。
- [ ] 运行目标测试并确认因缺少异常隔离而失败。
- [ ] 抽取单轮执行函数，在主循环捕获未预期异常、写错误日志并继续心跳。
- [ ] 编写启动脚本失败测试：脚本必须重定向日志并等待新鲜 worker 心跳。
- [ ] 修改启动脚本，若 worker 提前退出或心跳超时则停止已启动进程并给出明确错误。
- [ ] 运行 worker 与启动脚本测试。

### Task 2: 题库版本与候选题覆盖

**Files:**
- Modify: `services/api/app/queries/service.py`
- Modify: `services/api/app/queries/rules/restaurant.py`
- Test: `services/api/tests/queries/test_service.py`
- Test: `services/api/tests/queries/test_restaurant_rules.py`

**Interfaces:**
- Produces: `QueryLibraryService.generate(...)` 在保存新版本前归档所有旧活动版本。
- Produces: `RestaurantRulePack.generate(...)` 使用已确认的 `product.list` 生成 `product` 类推荐问题；口腔品类仍由服务层限定为民营同类。

- [ ] 编写失败测试：生成新题库后旧的有引用版本被归档，历史结果仍可读取。
- [ ] 运行测试并确认当前存在多个活动版本。
- [ ] 实现生成时归档旧版本。
- [ ] 编写失败测试：有 `product.list` 时，15 道候选题至少包含产品/服务问题。
- [ ] 运行测试并确认当前规则忽略产品列表。
- [ ] 添加产品问题并保持餐饮与口腔共用的事实驱动表达。
- [ ] 运行题库测试。

### Task 3: 六步进度与同题复测统一

**Files:**
- Modify: `services/api/app/mobile_checks/playbook.py`
- Modify: `services/api/app/reports/router.py`
- Test: `services/api/tests/mobile_checks/test_playbook.py`
- Test: `services/api/tests/reports/test_router.py`

**Interfaces:**
- Produces: `comparable_rounds(latest, previous) -> bool`，与报告 comparison 使用相同题目文本集合判定。
- Journey rule: 已确认手机轮次证明问题策略历史上已完成；复测仅在最新轮与上一轮可直接比较时完成。

- [ ] 编写失败测试：旧轮次曾同题但最新两轮不同题时，复测状态不得完成。
- [ ] 编写失败测试：已有确认手机轮次时，问题策略不得回退为未完成。
- [ ] 运行测试确认现有口径矛盾。
- [ ] 抽取并复用同题比较判定，调整 journey progress。
- [ ] 运行报告与手机实测测试。

### Task 4: 交付报告、状态文案与手机问题审核

**Files:**
- Create: `apps/web/src/lib/profile-field-labels.ts`
- Create: `apps/web/src/app/methodology/page.tsx`
- Modify: `apps/web/src/app/delivery-report/page.tsx`
- Modify: `apps/web/src/components/service-status.tsx`
- Modify: `apps/web/src/components/query-table.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Modify: `README.md`
- Test: `apps/web/tests/delivery-report.test.tsx`
- Test: `apps/web/tests/navigation.test.tsx`
- Test: `apps/web/tests/query-table.test.tsx`

**Interfaces:**
- Produces: `profileFieldLabel(fieldKey: string): string`，将内部字段键转换为中文标签。
- Produces: `/methodology` 方法口径页面。
- Mobile table: 每个单元格提供 `data-label`，小屏转为卡片式布局。

- [ ] 编写失败测试：交付报告不显示内部字段键，并显示中文标签。
- [ ] 编写失败测试：紧凑服务状态明确显示“后台任务未运行”。
- [ ] 编写失败测试：问题表格含移动端字段标签。
- [ ] 运行目标前端测试确认失败。
- [ ] 实现字段标签、方法页、明确状态文案和移动端卡片布局。
- [ ] 将 README 手机实测说明改为固定 3 个独立对话。
- [ ] 运行前端目标测试与 TypeScript 检查。

### Task 5: 完整验证与运行复核

**Files:**
- Verify only; do not add generated build artifacts.

**Interfaces:**
- Consumes: Tasks 1–4 的全部行为。
- Produces: 可复现的测试、构建与运行状态证据。

- [ ] 运行 `services/api/.venv/Scripts/python.exe -m pytest -q`。
- [ ] 运行 `npm.cmd test`、`npx.cmd tsc --noEmit` 和 `npm.cmd run build`。
- [ ] 清理 `tsconfig.tsbuildinfo` 等生成文件。
- [ ] 使用一键脚本重启项目，确认 API、网页与 worker 心跳均正常。
- [ ] 检查关键桌面和 390px 页面，无控制台错误、无核心操作溢出。
- [ ] 核对 `git diff --check` 与最终改动范围。
