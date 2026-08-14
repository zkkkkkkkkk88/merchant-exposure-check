# 上一轮手机实测问答展示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在手机实测完成状态中以默认折叠方式展示当前商家最近一轮的三组问题、原回答和确认结果。

**Architecture:** 后端 workspace 在已有最近轮次查询中组装 `latestRoundAnswers`，前端 contracts 接收后由独立只读组件渲染折叠详情。沿用现有轮次和结果模型，不新增表、不改变保存流程。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、Next.js 16、React、Vitest、pytest。

## Global Constraints

- 默认收起，仅显示当前商家最近一轮已确认数据。
- 每项显示题号、问题、完整回答、提及状态和目标商家排名。
- 没有回答时显示“本题未保存回答内容”。
- 不增加编辑、删除或完整历史列表功能。

---

### Task 1: 扩展 workspace 最近轮次问答数据

**Files:**
- Modify: `services/api/app/mobile_checks/schemas.py`
- Modify: `services/api/app/mobile_checks/service.py`
- Test: `services/api/tests/mobile_checks/test_service.py`

**Interfaces:**
- Produces: `latestRoundAnswers: list[dict]`，每项含 `position`、`question`、`answer`、`mentionLevel`、`mentionLabel`、`targetPosition`。

- [ ] 在 service 测试中断言最近轮次按题号返回问题、完整回答与确认结果，并先运行确认失败。
- [ ] 在空 workspace 响应和 `MobileWorkspaceRead` 中加入空数组字段。
- [ ] 在已有 latest round 结果上按 validation item position 排序并组装字段。
- [ ] 运行 `pytest tests/mobile_checks/test_service.py -q` 确认通过。

### Task 2: 添加前端折叠展示

**Files:**
- Modify: `apps/web/src/lib/contracts.ts`
- Create: `apps/web/src/components/latest-mobile-round-answers.tsx`
- Modify: `apps/web/src/components/mobile-check-workspace.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/mobile-checks.test.tsx`

**Interfaces:**
- Consumes: `MobileWorkspaceData.latestRoundAnswers`。
- Produces: 默认折叠的“查看上一轮问题与答案”区域。

- [ ] 在页面测试中加入最近一轮问答，断言默认不显示回答、点击后显示问题、回答和确认结果，并先运行确认失败。
- [ ] 扩展 TypeScript contract 并创建只读折叠组件，空回答显示明确提示。
- [ ] 将组件放入完成状态区域并补充紧凑卡片样式。
- [ ] 运行 `npm.cmd test -- --run tests/mobile-checks.test.tsx` 确认通过。
- [ ] 运行 `npx.cmd next build --webpack`，再在本地页面验证展开交互。
