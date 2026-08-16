# Mobile Source Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在手机实测录入页自动查找目标商家与重复竞品的公开来源，让用户勾选核验后随本轮结果保存。

**Architecture:** 后端新增无持久化的来源发现服务与接口，优先复用目标商家最近一次平台查缺证据，再通过现有 Ark 联网适配器对缺少来源的机构各搜索一次。前端在答案解析后统计重复竞品，通过 Server Action 调用接口，展示候选来源复选框，并将选中结果转换为现有 `MobileSourceCreate` 数据随本轮保存。

**Tech Stack:** FastAPI、Pydantic、SQLAlchemy、Ark SearchAdapter、Next.js Server Actions、React、TypeScript、pytest、Vitest。

## Global Constraints

- 每轮固定包含目标商家，只包含在3份答案中至少出现2次的竞品。
- 目标商家与竞品合计最多4家，每家最多3条来源，每家最多1次综合搜索。
- 缺少真实 HTTP(S) 网址的结果必须丢弃。
- “本次未找到”不得解释为“商家没有发布”。
- 自动结果必须经用户勾选后才能作为已确认来源保存。
- 保留折叠式手工补充入口。
- 不新增数据库表或迁移。

---

### Task 1: 后端来源范围与候选整理

**Files:**
- Create: `services/api/app/mobile_checks/source_discovery.py`
- Modify: `services/api/app/mobile_checks/schemas.py`
- Test: `services/api/tests/mobile_checks/test_source_discovery.py`

**Interfaces:**
- Produces: `select_discovery_entities(merchant_name: str, competitors: list[CompetitorOccurrence]) -> list[str]`
- Produces: `MobileSourceDiscoveryService(session, adapter).discover(merchant_id, payload) -> MobileSourceDiscoveryRead`
- Consumes: `SearchAdapter.search(SearchRequest)` 与最近一次 `PlatformAuditRun.platforms[*].evidence`

- [ ] **Step 1: 编写实体筛选失败测试**

```python
def test_select_discovery_entities_keeps_target_and_recurring_competitors():
    selected = select_discovery_entities(
        "澜沧皓雅口腔门诊部",
        [
            CompetitorOccurrence(name="王天佑口腔诊所", occurrence_count=3),
            CompetitorOccurrence(name="福康口腔", occurrence_count=2),
            CompetitorOccurrence(name="偶发诊所", occurrence_count=1),
            CompetitorOccurrence(name="德玉口腔", occurrence_count=2),
            CompetitorOccurrence(name="第五家", occurrence_count=3),
        ],
    )
    assert selected == ["澜沧皓雅口腔门诊部", "王天佑口腔诊所", "第五家", "福康口腔"]
```

- [ ] **Step 2: 运行测试并确认因模块不存在而失败**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/mobile_checks/test_source_discovery.py -q`
Expected: FAIL，提示 `app.mobile_checks.source_discovery` 不存在。

- [ ] **Step 3: 增加请求与返回模型**

在 `schemas.py` 新增：

```python
class CompetitorOccurrence(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    occurrence_count: int = Field(ge=1, le=3)

class MobileSourceDiscoveryCreate(BaseModel):
    location_text: str | None = Field(default=None, max_length=300)
    competitors: list[CompetitorOccurrence] = Field(default_factory=list, max_length=20)

class MobileSourceCandidate(BaseModel):
    entity_name: str
    source_type: Literal["profile", "registry", "recruitment", "douyin", "local_media", "government", "industry", "other"]
    title: str
    facts: list[str] = Field(default_factory=list)
    url: str
    evidence_kind: Literal["official", "third_party"]
    access_status: Literal["correctable", "reference"]
    reused_from_audit: bool = False

class MobileSourceDiscoveryGroup(BaseModel):
    entity_name: str
    sources: list[MobileSourceCandidate] = Field(default_factory=list)
    error: str | None = None

class MobileSourceDiscoveryRead(BaseModel):
    groups: list[MobileSourceDiscoveryGroup]
    external_call_count: int
```

- [ ] **Step 4: 实现实体限制、网址规范化和来源分类**

`select_discovery_entities` 按出现次数降序、首次输入顺序稳定排序，去除目标商家别名与重复名称，最后裁剪到3个竞品。`normalize_http_url` 仅接受 `http`、`https` 且必须包含域名。`classify_citation` 使用域名与标题关键词把 `.gov.cn`/登记页归为 `government` 或 `registry`，地图归为 `profile`，招聘归为 `recruitment`，其余归为 `other`。

- [ ] **Step 5: 实现混合来源发现服务**

服务先读取目标商家最近一次 `completed` 或 `partial` 平台查缺证据，按网址去重取最多3条。对来源不足3条的目标商家及所有竞品，各调用一次：

```python
response = await adapter.search(SearchRequest(
    query=build_source_query(entity_name, merchant.city, payload.location_text),
    merchant_id=merchant.id,
    correlation_id=f"mobile-source:{merchant.id}:{index}",
))
```

只从 `response.citations` 生成候选，事实摘要使用非空 `snippet`，每家最终最多3条。单家异常写入该组 `error="本次检索未完成"`，继续处理其他机构。

- [ ] **Step 6: 增加服务行为测试并运行**

覆盖平台证据复用不产生调用、竞品每家一次调用、无效网址过滤、网址去重、单家失败不影响其他组、每家最多3条和总调用不超过4。

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/mobile_checks/test_source_discovery.py -q`
Expected: PASS。

- [ ] **Step 7: 提交后端服务**

```powershell
git add services/api/app/mobile_checks/source_discovery.py services/api/app/mobile_checks/schemas.py services/api/tests/mobile_checks/test_source_discovery.py
git commit -m "feat: discover mobile check sources"
```

### Task 2: 来源发现 API

**Files:**
- Modify: `services/api/app/mobile_checks/router.py`
- Test: `services/api/tests/mobile_checks/test_router.py`

**Interfaces:**
- Produces: `POST /merchants/{merchant_id}/mobile-checks/discover-sources`
- Produces: `get_mobile_source_adapter() -> SearchAdapter`
- Consumes: `MobileSourceDiscoveryCreate` 与 `MobileSourceDiscoveryService.discover`

- [ ] **Step 1: 编写接口失败测试**

使用 `app.dependency_overrides[get_mobile_source_adapter] = lambda: fake_adapter`，提交一个重复2次的竞品，并断言返回目标商家组、竞品组和 `external_call_count <= 2`；不存在商家返回404，未配置适配器返回503。

- [ ] **Step 2: 运行接口测试并确认404路由失败**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/mobile_checks/test_router.py -q`
Expected: 新接口测试 FAIL，当前路由返回404。

- [ ] **Step 3: 实现适配器依赖与异步路由**

```python
def get_mobile_source_adapter() -> SearchAdapter:
    settings = get_settings()
    api_key = settings.ark_api_key.get_secret_value()
    if not api_key:
        raise HTTPException(status_code=503, detail="未配置联网公开来源搜索服务")
    return ArkSearchAdapter(api_key=api_key, model=settings.ark_model)

@router.post(
    "/merchants/{merchant_id}/mobile-checks/discover-sources",
    response_model=MobileSourceDiscoveryRead,
)
async def discover_mobile_sources(...):
    return await MobileSourceDiscoveryService(session, adapter).discover(merchant_id, payload)
```

- [ ] **Step 4: 运行手机实测路由测试**

Run: `services/api/.venv/Scripts/python.exe -m pytest services/api/tests/mobile_checks/test_router.py -q`
Expected: PASS。

- [ ] **Step 5: 提交 API**

```powershell
git add services/api/app/mobile_checks/router.py services/api/tests/mobile_checks/test_router.py
git commit -m "feat: expose mobile source discovery api"
```

### Task 3: 前端来源数据与 Server Action

**Files:**
- Create: `apps/web/src/lib/mobile-source-discovery.ts`
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/mobile-checks/actions.ts`
- Test: `apps/web/tests/mobile-source-discovery.test.ts`

**Interfaces:**
- Produces: `countRecurringCompetitors(drafts, merchantName) -> Array<{ name: string; occurrence_count: number }>`
- Produces: `discoverMobileSources(merchantId, payload) -> Promise<MobileSourceDiscoveryData>`
- Produces: `discoverMobileSourcesAction(input) -> Promise<MobileSourceDiscoveryData>`
- Consumes: 后端来源发现接口与 `ParsedMobileAnswer.competitors`

- [ ] **Step 1: 编写竞品统计失败测试**

```typescript
expect(countRecurringCompetitors([
  { competitors: ["王天佑口腔", "福康口腔"] },
  { competitors: ["王天佑口腔"] },
  { competitors: ["王天佑口腔", "福康口腔", "偶发诊所"] },
] as ParsedMobileAnswer[], "澜沧皓雅口腔")).toEqual([
  { name: "王天佑口腔", occurrence_count: 3 },
  { name: "福康口腔", occurrence_count: 2 },
]);
```

- [ ] **Step 2: 运行测试并确认模块不存在**

Run: `npm.cmd test -- --run tests/mobile-source-discovery.test.ts`
Expected: FAIL，提示模块不存在。

- [ ] **Step 3: 实现纯函数与 TypeScript 合同**

新增 `MobileSourceCandidateData`、`MobileSourceDiscoveryGroupData`、`MobileSourceDiscoveryData`，并实现按每份答案去重计数、过滤目标商家和出现1次竞品的纯函数。

- [ ] **Step 4: 实现 API 客户端与 Server Action**

`discoverMobileSources` 向新接口发送 JSON；非2xx时读取 `detail` 并抛出 `ApiError`。`discoverMobileSourcesAction` 接收可序列化对象并直接返回结果，不执行重定向。

- [ ] **Step 5: 运行前端纯函数测试**

Run: `npm.cmd test -- --run tests/mobile-source-discovery.test.ts`
Expected: PASS。

- [ ] **Step 6: 提交前端数据层**

```powershell
git add apps/web/src/lib/mobile-source-discovery.ts apps/web/src/lib/contracts.ts apps/web/src/lib/api.ts apps/web/src/app/mobile-checks/actions.ts apps/web/tests/mobile-source-discovery.test.ts
git commit -m "feat: connect mobile source discovery"
```

### Task 4: 自动来源核验界面与保存

**Files:**
- Create: `apps/web/src/components/mobile-source-review.tsx`
- Modify: `apps/web/src/components/mobile-check-workspace.tsx`
- Modify: `apps/web/src/app/mobile-checks/actions.ts`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/mobile-source-review.test.tsx`
- Test: `apps/web/tests/mobile-check-workspace.test.tsx`

**Interfaces:**
- Produces: `MobileSourceReview({ groups, loading, error, onDiscover, onRediscover })`
- Produces: 表单字段 `confirmedAutoSources`，每个选中值为一个候选来源 JSON 字符串
- Consumes: `countRecurringCompetitors` 与 `discoverMobileSourcesAction`

- [ ] **Step 1: 编写来源核验组件失败测试**

测试目标：答案识别前没有自动查找按钮；识别后出现按钮；点击后显示加载状态；成功后按机构分组；候选默认未勾选；勾选值进入 `confirmedAutoSources`；无结果显示“不代表商家没有发布”；手工补充使用 `<details>` 折叠。

- [ ] **Step 2: 运行组件测试并确认失败**

Run: `npm.cmd test -- --run tests/mobile-source-review.test.tsx tests/mobile-check-workspace.test.tsx`
Expected: FAIL，组件或按钮不存在。

- [ ] **Step 3: 实现独立核验组件**

组件渲染来源组、错误提示、外链和复选框：

```tsx
<label className="source-candidate">
  <input name="confirmedAutoSources" type="checkbox" value={JSON.stringify(source)} />
  <span>{source.title}</span>
  <a href={source.url} target="_blank" rel="noreferrer">查看来源</a>
</label>
```

没有候选时显示固定文案：“本次未找到可核验来源，不代表商家没有发布。”

- [ ] **Step 4: 接入工作区状态和调用**

在 `MobileCheckWorkspace` 中增加位置受控状态、`sourceGroups`、`sourceLoading`、`sourceError`。答案解析后通过 `countRecurringCompetitors(drafts, merchantName)` 生成请求；第一次按钮文案为“自动查找公开来源”，已有结果后为“重新查找”。

- [ ] **Step 5: 合并自动与手工来源保存**

`saveMobileRound` 解析 `formData.getAll("confirmedAutoSources")`，只接受包含 `entity_name`、`title`、HTTP(S) `url` 的对象，强制写入 `is_confirmed: true`；再与手工文本解析结果合并并按网址去重。手工输入名称改为 `manualSources`。

- [ ] **Step 6: 增加规范布局样式**

来源区域使用分组卡片、两列信息布局和移动端单列；按钮、加载态、错误态及折叠入口沿用现有色彩和边框变量，不新增视觉体系。

- [ ] **Step 7: 运行组件与保存测试**

Run: `npm.cmd test -- --run tests/mobile-source-review.test.tsx tests/mobile-check-workspace.test.tsx`
Expected: PASS。

- [ ] **Step 8: 提交界面与保存流程**

```powershell
git add apps/web/src/components/mobile-source-review.tsx apps/web/src/components/mobile-check-workspace.tsx apps/web/src/app/mobile-checks/actions.ts apps/web/src/styles/globals.css apps/web/tests/mobile-source-review.test.tsx apps/web/tests/mobile-check-workspace.test.tsx
git commit -m "feat: review discovered mobile sources"
```

### Task 5: 完整验证与运行复核

**Files:**
- Modify only if verification exposes a defect in files already listed above.

**Interfaces:**
- Consumes: Tasks 1-4 的完整实现。
- Produces: 可运行且通过测试的自动来源查找流程。

- [ ] **Step 1: 运行后端完整测试**

Run: `services/api/.venv/Scripts/python.exe -m pytest -q`
Expected: 全部 PASS。

- [ ] **Step 2: 运行前端完整测试、类型检查和构建**

Run: `npm.cmd test -- --run`
Run: `npx.cmd tsc --noEmit`
Run: `npm.cmd run build`
Expected: 全部退出码为0。

- [ ] **Step 3: 检查差异并重启项目**

Run: `git diff --check`
Run: `scripts/stop-dev.cmd`
Run: `scripts/start-dev.cmd`
Expected: `/system/status` 中 API、数据库、Worker 均为 `ok`，`/mobile-checks` 返回200。
