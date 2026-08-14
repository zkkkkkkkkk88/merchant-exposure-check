# 问题题库与手机实测抽样分离 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每个商家维护 15 道候选问题，完整检测使用全部已审核启用问题，手机实测允许从中选择且仅选择 3 道。

**Architecture:** 保留 `QuerySet` 作为完整候选题库，`MobileValidationSet` 只保存每轮手机抽样的三个题目。后端新增显式创建手机验证集的选择接口，前端通过服务端 action 提交三个 query id；默认抽样继续由服务端按场景去重完成。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、Next.js、React、TypeScript、pytest、Vitest。

## Global Constraints

- 问题策略默认生成 15 道候选题。
- 手机实测必须且只能选择 3 道已审核、已启用的推荐问题。
- 更换手机实测题不得修改题库状态或历史轮次。
- 口腔行业使用民营同类问题；餐饮行业不得出现医疗限定。
- 只有规范化题目完全一致的手机轮次才能比较。

---

### Task 1: 完整候选题库

**Files:**
- Modify: `apps/web/src/app/queries/actions.ts`
- Modify: `services/api/app/queries/service.py`
- Test: `services/api/tests/queries/test_service.py`

**Interfaces:**
- Produces: 最新 `QuerySet` 默认包含 15 道候选题；口腔类推荐题使用民营同类范围。

- [ ] 写失败测试：生成请求默认数量为 15，口腔题库不少于 10 且最多 20，餐饮题库无“民营”。
- [ ] 运行定向测试并确认因当前默认数量或规则不足失败。
- [ ] 修改生成 action 和服务规则，使默认生成 15 道并保持行业隔离。
- [ ] 运行查询服务测试并确认通过。

### Task 2: 显式选择三道手机验证题

**Files:**
- Modify: `services/api/app/mobile_checks/schemas.py`
- Modify: `services/api/app/mobile_checks/service.py`
- Modify: `services/api/app/mobile_checks/router.py`
- Test: `services/api/tests/mobile_checks/test_service.py`
- Test: `services/api/tests/mobile_checks/test_router.py`

**Interfaces:**
- Consumes: `MobileValidationSetCreate(query_ids: list[UUID])`。
- Produces: `POST /merchants/{merchant_id}/mobile-validation-sets`，成功返回新的三题 `MobileValidationSetRead`。

- [ ] 写失败测试：恰好三个、同属最新题库、已审核启用、推荐意图时成功。
- [ ] 写失败测试：少于/多于三个、重复、未审核、停用或核验题时返回 422/409。
- [ ] 运行测试确认接口和验证逻辑尚不存在。
- [ ] 实现请求模型、服务校验及路由；只新增验证集，不修改题库和历史记录。
- [ ] 运行 mobile checks 后端测试确认通过。

### Task 3: 手机页面三题选择器

**Files:**
- Modify: `apps/web/src/app/mobile-checks/page.tsx`
- Modify: `apps/web/src/app/mobile-checks/actions.ts`
- Modify: `apps/web/src/components/mobile-check-workspace.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/mobile-checks.test.tsx`

**Interfaces:**
- Consumes: 最新题库中已审核、已启用且 `intent_type === "recommendation"` 的候选题。
- Produces: “更换本轮3题”选择器及 `selectMobileValidationSet` server action。

- [ ] 写失败测试：页面展示完整候选数量、可打开选择器、只能提交三题，并保留当前三题。
- [ ] 运行前端测试确认缺少选择器。
- [ ] 实现 action、API 调用、选择器和不足三题提示。
- [ ] 运行前端 mobile checks 测试确认通过。

### Task 4: 当前数据与端到端验收

**Files:**
- Data: `services/api/merchant-exposure.db`（仅皓雅最新题库扩展至 15 道）

**Interfaces:**
- Produces: 皓雅 15 道候选题 + 默认 3 道手机题；O'eat 现有餐饮题库和手机题保持行业语义。

- [ ] 通过应用服务为皓雅生成/补齐 15 道已审核候选题，保留当前三题验证集。
- [ ] 运行后端相关测试、前端相关测试和 webpack 构建各一次。
- [ ] 重启 API 与 Web 开发服务。
- [ ] 浏览器验收皓雅问题策略为 15 道、手机实测为 3 道且可更换；切换 O'eat 验证无医疗限定。
