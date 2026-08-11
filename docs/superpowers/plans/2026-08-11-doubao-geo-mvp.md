# AI 商家曝光检测 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可录入多个商家、生成问题库、执行联网检测、提取品牌与信源、计算曝光指标并比较历史结果的单管理员 MVP。

**Architecture:** 使用 Next.js 管理后台、FastAPI 业务 API、PostgreSQL 持久化和独立 Python worker 组成模块化单体。所有搜索服务通过统一 `SearchAdapter` 接口接入，原始回答不可变保存，结构化提取、确定性指标和证据化缺口分析分别处理。

**Tech Stack:** Next.js、TypeScript、React、Tailwind CSS、Vitest、Playwright、Python 3.12+、FastAPI、Pydantic v2、SQLAlchemy 2、Alembic、PostgreSQL、pytest、Docker Compose、火山方舟 Responses API。

## Global Constraints

- 第一版只有单管理员角色，但所有业务表必须按 `merchant_id` 隔离。
- 第一条演示数据是 `O'eat Gastronomy（杭州万象城店）`，不得为它硬编码分析逻辑。
- 原始回答不可被结构化结果或人工修正覆盖。
- 无明确排序时不计算前三推荐，只保存可确认的提及位置。
- 外部网页、模型回答和导入内容全部视为不可信数据。
- API 密钥只允许从服务端环境变量读取，不得进入数据库、日志或前端。
- 同一外部调用连续失败两次后停止自动重试，并保存可读错误原因。
- UI 使用暖白或浅灰背景、深灰文字和单一强调色；禁止紫蓝渐变、玻璃拟态、发光边框、机器人或星光装饰。
- 第一版不实现注册、权限、支付、自动发布、多 AI 平台和定时复测。
- 每个功能任务必须先写失败测试，再实现最小代码，再只运行与本任务相关的测试。

---

## Planned File Structure

```text
.
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
├── apps/
│   └── web/
│       ├── package.json
│       ├── next.config.ts
│       ├── tsconfig.json
│       ├── vitest.config.ts
│       ├── playwright.config.ts
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx
│       │   │   ├── page.tsx
│       │   │   ├── merchants/
│       │   │   ├── queries/
│       │   │   ├── scans/
│       │   │   ├── reports/
│       │   │   └── history/
│       │   ├── components/
│       │   ├── lib/api.ts
│       │   ├── lib/contracts.ts
│       │   └── styles/globals.css
│       └── tests/
├── services/
│   └── api/
│       ├── pyproject.toml
│       ├── alembic.ini
│       ├── migrations/
│       ├── app/
│       │   ├── main.py
│       │   ├── core/
│       │   ├── db/
│       │   ├── merchants/
│       │   ├── queries/
│       │   ├── scans/
│       │   ├── analysis/
│       │   └── reports/
│       ├── scripts/seed_demo.py
│       └── tests/
└── docs/superpowers/
```

Each Python feature package owns its models, schemas, service and router. Cross-feature database setup lives in `app/db`; external calls live only in `app/scans/adapters`; deterministic calculations live only in `app/analysis`.

---

### Task 1: Runnable Project Foundation

**Files:**
- Create: `.env.example`
- Create: `.gitignore`
- Create: `docker-compose.yml`
- Create: `README.md`
- Create: `services/api/pyproject.toml`
- Create: `services/api/app/main.py`
- Create: `services/api/app/core/config.py`
- Create: `services/api/app/db/session.py`
- Create: `services/api/tests/test_health.py`
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/styles/globals.css`
- Create: `apps/web/tests/home.test.tsx`

**Interfaces:**
- Produces: `GET /health -> {"status":"ok"}`.
- Produces: `get_settings() -> Settings` with `database_url`, `ark_api_key`, `ark_model`, `api_base_url`.
- Produces: a web root page containing `商家曝光检测` and an API health state.

- [ ] **Step 1: Write the backend health test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the backend test and verify it fails**

Run: `cd services/api; python -m pytest tests/test_health.py -v`

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Add the Python project and minimal FastAPI app**

Create `pyproject.toml` with runtime dependencies `fastapi`, `uvicorn`, `pydantic-settings`, `sqlalchemy`, `psycopg[binary]`, `alembic`, `httpx`, and development dependencies `pytest`, `pytest-asyncio`, `ruff`.

```python
# services/api/app/main.py
from fastapi import FastAPI

app = FastAPI(title="Merchant Exposure API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

```python
# services/api/app/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/exposure"
    ark_api_key: str = ""
    ark_model: str = "doubao-seed-2-0-lite-260215"
    api_base_url: str = "http://localhost:8000"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run the backend health test**

Run: `cd services/api; python -m pytest tests/test_health.py -v`

Expected: PASS.

- [ ] **Step 5: Write the frontend root-page test**

```tsx
import { render, screen } from "@testing-library/react";
import Home from "../src/app/page";

it("introduces the merchant exposure workspace", () => {
  render(<Home />);
  expect(screen.getByRole("heading", { name: "商家曝光检测" })).toBeVisible();
});
```

- [ ] **Step 6: Run the frontend test and verify it fails**

Run: `cd apps/web; npm test -- home.test.tsx`

Expected: FAIL because the web project is not configured.

- [ ] **Step 7: Add the Next.js shell and restrained global design tokens**

Use CSS variables with these exact defaults:

```css
:root {
  --canvas: #f4f3ef;
  --surface: #fbfaf7;
  --ink: #1f2421;
  --muted: #6f756f;
  --line: #dadbd5;
  --accent: #176b54;
  --danger: #a94736;
  --radius: 12px;
}
```

`page.tsx` renders a simple heading and health placeholder without gradients, oversized hero text or decorative AI imagery.

- [ ] **Step 8: Run foundation checks**

Run: `cd services/api; python -m pytest tests/test_health.py -v`

Expected: PASS.

Run: `cd apps/web; npm test -- home.test.tsx`

Expected: PASS.

- [ ] **Step 9: Add Docker Compose and setup documentation**

`docker-compose.yml` must define `db`, `api`, `worker`, and `web`. Both `api` and `worker` use the same Python image and source tree; `worker` runs `python -m app.scans.worker`. `.env.example` contains blank `ARK_API_KEY` and non-secret local defaults.

- [ ] **Step 10: Commit the foundation**

```bash
git add .env.example .gitignore docker-compose.yml README.md services/api apps/web
git commit -m "chore: scaffold merchant exposure workspace"
```

---

### Task 2: Merchant Records and Public Sources

**Files:**
- Create: `services/api/app/db/base.py`
- Create: `services/api/app/merchants/models.py`
- Create: `services/api/app/merchants/schemas.py`
- Create: `services/api/app/merchants/service.py`
- Create: `services/api/app/merchants/router.py`
- Create: `services/api/migrations/env.py`
- Create: `services/api/migrations/versions/0001_merchants.py`
- Create: `services/api/tests/merchants/test_service.py`
- Create: `services/api/tests/merchants/test_router.py`
- Modify: `services/api/app/main.py`

**Interfaces:**
- Produces: `MerchantService.create(session, MerchantCreate) -> Merchant`.
- Produces: `MerchantService.list(session) -> list[Merchant]`.
- Produces: `MerchantService.update(session, merchant_id, MerchantUpdate) -> Merchant`.
- Produces: REST endpoints `POST /merchants`, `GET /merchants`, `GET /merchants/{id}`, `PATCH /merchants/{id}`.
- Produces: nested public sources through `MerchantCreate.sources` and `MerchantRead.sources`.

- [ ] **Step 1: Write failing merchant service tests**

```python
def test_create_merchant_keeps_sources(db_session):
    payload = MerchantCreate(
        name="O'eat Gastronomy",
        branch_name="杭州万象城店",
        city="杭州",
        district="上城区",
        industry="餐饮",
        products=["西餐", "约会餐厅"],
        sources=[MerchantSourceCreate(kind="meituan", url="https://pmtmeishi.meituan.com/dp/prefer/list/1510759369")],
    )
    merchant = MerchantService.create(db_session, payload)
    assert merchant.city == "杭州"
    assert merchant.sources[0].kind == "meituan"
```

- [ ] **Step 2: Run the merchant service test and verify it fails**

Run: `cd services/api; python -m pytest tests/merchants/test_service.py -v`

Expected: FAIL because merchant models and service are absent.

- [ ] **Step 3: Add models and migration**

Implement `Merchant` with UUID primary key, normalized name, branch name, city, district, industry, address, price range, opening hours, products as JSON array, strengths as JSON array, timestamps and relationship to `MerchantSource`.

Implement `MerchantSource` with UUID, merchant foreign key, `kind`, `url`, `is_verified`, and timestamp. Add a unique constraint on `(merchant_id, url)`.

- [ ] **Step 4: Add Pydantic schemas and service**

```python
class MerchantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    branch_name: str | None = Field(default=None, max_length=160)
    city: str = Field(min_length=1, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    industry: str = Field(min_length=1, max_length=80)
    address: str | None = Field(default=None, max_length=300)
    price_range: str | None = Field(default=None, max_length=80)
    opening_hours: str | None = Field(default=None, max_length=160)
    products: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    sources: list[MerchantSourceCreate] = Field(default_factory=list)
```

Normalize whitespace, reject non-HTTP(S) source URLs and never fetch URLs during merchant creation.

- [ ] **Step 5: Run service tests**

Run: `cd services/api; python -m pytest tests/merchants/test_service.py -v`

Expected: PASS.

- [ ] **Step 6: Write failing router tests**

Test that `POST /merchants` returns 201, `GET /merchants` includes the new merchant, an unknown UUID returns 404, and invalid `ftp://` sources return 422.

- [ ] **Step 7: Implement and register the router**

Use response schemas rather than returning ORM objects directly. The router owns HTTP status codes; the service owns data operations.

- [ ] **Step 8: Run merchant tests**

Run: `cd services/api; python -m pytest tests/merchants -v`

Expected: PASS.

- [ ] **Step 9: Commit merchant records**

```bash
git add services/api/app/db services/api/app/merchants services/api/migrations services/api/tests/merchants services/api/app/main.py
git commit -m "feat: add merchant and source records"
```

---

### Task 3: Versioned Query Library

**Files:**
- Create: `services/api/app/queries/models.py`
- Create: `services/api/app/queries/schemas.py`
- Create: `services/api/app/queries/generator.py`
- Create: `services/api/app/queries/service.py`
- Create: `services/api/app/queries/router.py`
- Create: `services/api/migrations/versions/0002_queries.py`
- Create: `services/api/tests/queries/test_generator.py`
- Create: `services/api/tests/queries/test_service.py`
- Create: `services/api/tests/queries/test_router.py`
- Modify: `services/api/app/main.py`

**Interfaces:**
- Produces: `QueryCategory = Literal["geo", "category", "product", "price", "occasion", "need"]`.
- Produces: `QueryDraft(text: str, category: QueryCategory, reason: str, priority: int)`.
- Produces: `QueryGenerator.generate(merchant: MerchantRead, count: int) -> list[QueryDraft]`.
- Produces: `POST /merchants/{id}/query-sets/generate`, `GET /merchants/{id}/query-sets`, `PATCH /queries/{id}`.

- [ ] **Step 1: Write a failing deterministic generator test**

```python
def test_template_generator_covers_required_categories(o_eat_merchant):
    drafts = TemplateQueryGenerator().generate(o_eat_merchant, count=30)
    assert len(drafts) == 30
    assert {d.category for d in drafts} == {"geo", "category", "product", "price", "occasion", "need"}
    assert len({d.text for d in drafts}) == 30
    assert all("O'eat" not in d.text for d in drafts if d.category != "need")
```

- [ ] **Step 2: Run the generator test and verify it fails**

Run: `cd services/api; python -m pytest tests/queries/test_generator.py -v`

Expected: FAIL because the generator is absent.

- [ ] **Step 3: Implement a deterministic template generator**

Generate six balanced categories using merchant city, district, industry and products. Ensure generic discovery questions do not contain the target brand. Deduplicate normalized question text and attach a concrete generation reason to every draft.

- [ ] **Step 4: Run generator tests**

Run: `cd services/api; python -m pytest tests/queries/test_generator.py -v`

Expected: PASS.

- [ ] **Step 5: Write failing versioning and review tests**

Test that generating creates immutable `QuerySet(version=1)`, a second generation creates version 2, editing a query changes `text`, `priority`, `is_enabled`, and `review_status`, and scan creation can reference an exact query-set version.

- [ ] **Step 6: Add query models, migration and service**

`QuerySet` contains UUID, merchant ID, integer version, generator name and creation time. `Query` contains UUID, query-set ID, text, category, reason, priority from 1 to 5, review status (`pending`, `approved`, `rejected`) and enabled flag.

- [ ] **Step 7: Add query REST endpoints**

Generation defaults to 30 and accepts only counts from 6 through 100. Return 409 when trying to generate for an unknown or incomplete merchant record.

- [ ] **Step 8: Run query tests**

Run: `cd services/api; python -m pytest tests/queries -v`

Expected: PASS.

- [ ] **Step 9: Commit the query library**

```bash
git add services/api/app/queries services/api/migrations/versions/0002_queries.py services/api/tests/queries services/api/app/main.py
git commit -m "feat: add versioned merchant query library"
```

---

### Task 4: Search Adapters and Durable Scan Execution

**Files:**
- Create: `services/api/app/scans/models.py`
- Create: `services/api/app/scans/schemas.py`
- Create: `services/api/app/scans/adapters/base.py`
- Create: `services/api/app/scans/adapters/manual.py`
- Create: `services/api/app/scans/adapters/ark.py`
- Create: `services/api/app/scans/service.py`
- Create: `services/api/app/scans/worker.py`
- Create: `services/api/app/scans/router.py`
- Create: `services/api/migrations/versions/0003_scans.py`
- Create: `services/api/tests/scans/test_adapters.py`
- Create: `services/api/tests/scans/test_worker.py`
- Create: `services/api/tests/scans/test_router.py`
- Modify: `services/api/app/main.py`

**Interfaces:**
- Produces: `SearchRequest(query: str, merchant_id: UUID, correlation_id: str)`.
- Produces: `SearchResponse(raw_text: str, citations: list[RawCitation], provider_request_id: str | None)`.
- Produces: `SearchAdapter.search(request: SearchRequest) -> SearchResponse`.
- Produces: `ScanService.create_run(session, merchant_id, query_set_id, adapter_name) -> ScanRun`.
- Produces: `process_next_scan(session_factory, adapter_registry) -> UUID | None`.
- Produces: REST endpoints `POST /scan-runs`, `GET /scan-runs/{id}`, `POST /scan-runs/{id}/manual-results`.

- [ ] **Step 1: Write failing adapter contract tests**

```python
@pytest.mark.asyncio
async def test_manual_adapter_returns_supplied_result():
    adapter = ManualSearchAdapter({"杭州约会餐厅推荐": SearchResponse(raw_text="推荐 O'eat。", citations=[])})
    result = await adapter.search(SearchRequest(query="杭州约会餐厅推荐", merchant_id=uuid4(), correlation_id="q-1"))
    assert result.raw_text == "推荐 O'eat。"


@pytest.mark.asyncio
async def test_ark_adapter_requires_server_side_key():
    with pytest.raises(AdapterConfigurationError):
        ArkSearchAdapter(api_key="", model="model")
```

- [ ] **Step 2: Run adapter tests and verify they fail**

Run: `cd services/api; python -m pytest tests/scans/test_adapters.py -v`

Expected: FAIL because adapters are absent.

- [ ] **Step 3: Define the adapter protocol and implementations**

`ArkSearchAdapter` calls `POST https://ark.cn-beijing.volces.com/api/v3/responses` with bearer authentication, the configured model, the question as user input and the Web Search tool enabled. It maps only response text, citations and provider request ID into `SearchResponse`; it never logs authorization headers or full environment values.

`ManualSearchAdapter` returns administrator-supplied results and is deterministic for tests and demos.

- [ ] **Step 4: Run adapter tests**

Run: `cd services/api; python -m pytest tests/scans/test_adapters.py -v`

Expected: PASS without making a network call.

- [ ] **Step 5: Write failing durable worker tests**

Test these exact state transitions:

```text
queued → running → completed
queued → running → partial (at least one result succeeded)
queued → running → failed (no result succeeded)
```

Also verify that each query result stores immutable `raw_text`, citations, adapter name, attempt count, started time and finished time. Simulate a rate-limit error twice and assert there are exactly two attempts.

- [ ] **Step 6: Add scan models and migration**

Create `ScanRun`, `QueryResult`, and `Citation`. Add database constraints for valid statuses and a uniqueness constraint on `(scan_run_id, query_id)`. Use a JSON column only for provider metadata; searchable facts must have typed columns.

- [ ] **Step 7: Implement scan creation and worker processing**

Claim one queued run using `SELECT ... FOR UPDATE SKIP LOCKED`. Process approved and enabled questions in priority order. Commit after each query result so a process restart retains progress. Retry only `429`, connection timeout and temporary `5xx` errors, with delays of 2 and 5 seconds; the second failed attempt becomes the final failure.

- [ ] **Step 8: Add scan endpoints**

Reject scan creation when the selected query set has no approved enabled questions. Manual imports must validate that every supplied `query_id` belongs to the scan run's query set.

- [ ] **Step 9: Run scan tests**

Run: `cd services/api; python -m pytest tests/scans -v`

Expected: PASS.

- [ ] **Step 10: Commit scan execution**

```bash
git add services/api/app/scans services/api/migrations/versions/0003_scans.py services/api/tests/scans services/api/app/main.py
git commit -m "feat: add durable search scan execution"
```

---

### Task 5: Structured Extraction, Metrics and Evidence-Based Findings

**Files:**
- Create: `services/api/app/analysis/contracts.py`
- Create: `services/api/app/analysis/normalization.py`
- Create: `services/api/app/analysis/extractor.py`
- Create: `services/api/app/analysis/metrics.py`
- Create: `services/api/app/analysis/findings.py`
- Create: `services/api/app/reports/schemas.py`
- Create: `services/api/app/reports/service.py`
- Create: `services/api/app/reports/router.py`
- Create: `services/api/app/reports/models.py`
- Create: `services/api/migrations/versions/0004_analysis.py`
- Create: `services/api/tests/analysis/test_normalization.py`
- Create: `services/api/tests/analysis/test_metrics.py`
- Create: `services/api/tests/analysis/test_findings.py`
- Create: `services/api/tests/reports/test_router.py`
- Modify: `services/api/app/main.py`

**Interfaces:**
- Produces: `ExtractedResult(mentions: list[ExtractedMention], facts: list[ExtractedFact], confidence: float)`.
- Produces: `normalize_brand_name(value: str) -> str`.
- Produces: `calculate_metrics(results: Sequence[AnalyzedQueryResult], target_brand_id: UUID) -> MetricSnapshot`.
- Produces: `build_findings(context: FindingContext) -> list[GapFindingDraft]`.
- Produces: `GET /merchants/{id}/reports/{scan_run_id}` and `GET /merchants/{id}/history?left={id}&right={id}`.
- Produces: `POST /scan-runs/{id}/manual-checks` and `GET /scan-runs/{id}/manual-checks`.

- [ ] **Step 1: Write failing brand normalization tests**

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("O'eat Gastronomy（杭州万象城店）", "o'eat gastronomy杭州万象城店"),
        (" O’EAT   Gastronomy ", "o'eat gastronomy"),
        ("欧逸 O'eat", "欧逸o'eat"),
    ],
)
def test_normalize_brand_name(raw, expected):
    assert normalize_brand_name(raw) == expected
```

- [ ] **Step 2: Run normalization tests and verify they fail**

Run: `cd services/api; python -m pytest tests/analysis/test_normalization.py -v`

Expected: FAIL because normalization is absent.

- [ ] **Step 3: Implement normalization and extraction contracts**

Normalization applies Unicode NFKC, lowercasing, apostrophe normalization, whitespace collapse and removal of punctuation that does not distinguish a brand. Preserve raw brand text alongside normalized text.

Extraction JSON must reject positions below 1, confidence outside 0 through 1, citations not present in the saved query result, and invented source URLs.

- [ ] **Step 4: Write failing metric tests**

Use a fixed six-result fixture and assert exact values:

```python
assert snapshot.valid_query_count == 5
assert snapshot.mention_rate == Decimal("0.4000")
assert snapshot.first_position_rate == Decimal("0.2500")
assert snapshot.task_valid_rate == Decimal("0.8333")
assert snapshot.independent_source_count == 3
```

One result must be invalid, two valid results must mention the target, and only four valid results may have explicit rankings. Assert that unranked mentions do not enter the first-position denominator.

- [ ] **Step 5: Implement deterministic metrics**

Use `Decimal` and quantize rates to four decimal places. Compute category coverage, competitor counts, source coverage and field completeness. The function must not call a model or database.

- [ ] **Step 6: Run analysis metric tests**

Run: `cd services/api; python -m pytest tests/analysis/test_normalization.py tests/analysis/test_metrics.py -v`

Expected: PASS.

- [ ] **Step 7: Write failing finding tests**

Assert that a price-information finding is created only when the target lacks confirmed price evidence and at least one frequent competitor has it. Assert every finding contains at least one `EvidenceRef(query_result_id, citation_id | None)` and that low-confidence evidence produces an `uncertain` finding rather than a factual assertion.

- [ ] **Step 8: Implement rule-first findings and report service**

Start with explicit rules for missing address, opening hours, price, product detail, occasion association and independent third-party sources. A model may rewrite the explanation, but it cannot create a finding type or evidence reference not produced by the rules.

- [ ] **Step 9: Add report, history and manual-check persistence**

Add `GapFinding`, `ActionItem`, and `ManualCheck`. History comparison returns both snapshots plus numeric deltas; it does not claim causality. Manual checks store question, answer summary, mentioned flag, position, source list and checked time. Add create/list manual-check endpoints; reject a check whose question does not belong to the scan run's query set, and allow `position` only when `mentioned=true`.

- [ ] **Step 10: Run analysis and report tests**

Run: `cd services/api; python -m pytest tests/analysis tests/reports -v`

Expected: PASS.

- [ ] **Step 11: Commit analysis and reporting**

```bash
git add services/api/app/analysis services/api/app/reports services/api/migrations/versions/0004_analysis.py services/api/tests/analysis services/api/tests/reports services/api/app/main.py
git commit -m "feat: add exposure metrics and evidence reports"
```

---

### Task 6: Editorial Dashboard and Shared Frontend Components

**Files:**
- Create: `apps/web/src/lib/contracts.ts`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/components/app-shell.tsx`
- Create: `apps/web/src/components/metric-strip.tsx`
- Create: `apps/web/src/components/exposure-trend.tsx`
- Create: `apps/web/src/components/category-coverage.tsx`
- Create: `apps/web/src/components/competitor-table.tsx`
- Create: `apps/web/src/components/action-list.tsx`
- Create: `apps/web/src/components/status-badge.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/tests/dashboard.test.tsx`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/styles/globals.css`

**Interfaces:**
- Consumes: report endpoint from Task 5.
- Produces: `getDashboard(merchantId: string) -> Promise<DashboardData>`.
- Produces: reusable visual components accepting typed props from `contracts.ts`.

- [ ] **Step 1: Write a failing dashboard behavior test**

```tsx
it("shows evidence-led metrics without AI marketing copy", async () => {
  mockDashboard({ mentionRate: 0.4, firstPositionRate: 0.25, highPriorityFindingCount: 2 });
  render(await DashboardPage({ searchParams: Promise.resolve({ merchant: "merchant-1" }) }));
  expect(screen.getByText("品牌出现率")).toBeVisible();
  expect(screen.getByText("40%" )).toBeVisible();
  expect(screen.getByText("高优先级行动")).toBeVisible();
  expect(screen.queryByText(/AI 洞察|智能魔法|一键增长/)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the dashboard test and verify it fails**

Run: `cd apps/web; npm test -- dashboard.test.tsx`

Expected: FAIL because dashboard components are absent.

- [ ] **Step 3: Implement typed API access and the application shell**

`api.ts` must use a single `NEXT_PUBLIC_API_BASE_URL`, throw an `ApiError` containing status and safe message, and never expose server secrets. `AppShell` uses a 216-pixel desktop navigation rail and a compact mobile header.

- [ ] **Step 4: Implement the editorial dashboard**

Use this hierarchy:

```text
Merchant switcher + New scan action
Thin metric strip
Exposure trend (two-thirds) + priority actions (one-third)
Category coverage + competitor comparison
Methodology and last-run note
```

Use dividers and whitespace rather than a card around every block. Charts use the accent green for the target, graphite for competitors and muted gray for context. All chart values have visible text equivalents.

- [ ] **Step 5: Add loading, empty and error states**

The empty state says `创建第一个商家后开始检测` and links to `/merchants/new`. The error state contains `重新加载` and the safe API message. Loading uses neutral skeleton lines without shimmer gradients.

- [ ] **Step 6: Run dashboard tests and accessibility assertions**

Run: `cd apps/web; npm test -- dashboard.test.tsx`

Expected: PASS, including assertions for headings, accessible table names and keyboard-reachable actions.

- [ ] **Step 7: Commit the dashboard**

```bash
git add apps/web/src/lib apps/web/src/components apps/web/src/app/page.tsx apps/web/src/app/layout.tsx apps/web/src/styles/globals.css apps/web/tests/dashboard.test.tsx
git commit -m "feat: add editorial exposure dashboard"
```

---

### Task 7: Merchant, Query, Scan, Report and History Screens

**Files:**
- Create: `apps/web/src/app/merchants/page.tsx`
- Create: `apps/web/src/app/merchants/new/page.tsx`
- Create: `apps/web/src/app/merchants/[id]/page.tsx`
- Create: `apps/web/src/app/queries/page.tsx`
- Create: `apps/web/src/app/scans/page.tsx`
- Create: `apps/web/src/app/scans/[id]/page.tsx`
- Create: `apps/web/src/app/reports/[scanId]/page.tsx`
- Create: `apps/web/src/app/history/page.tsx`
- Create: `apps/web/src/components/merchant-form.tsx`
- Create: `apps/web/src/components/query-table.tsx`
- Create: `apps/web/src/components/scan-progress.tsx`
- Create: `apps/web/src/components/evidence-drawer.tsx`
- Create: `apps/web/src/components/history-comparison.tsx`
- Create: `apps/web/tests/merchant-form.test.tsx`
- Create: `apps/web/tests/query-table.test.tsx`
- Create: `apps/web/tests/scan-report.test.tsx`

**Interfaces:**
- Consumes: merchant, query, scan and report endpoints from Tasks 2 through 5.
- Produces: administrator workflow from merchant creation through historical comparison.
- Produces: `EvidenceDrawer` that shows raw result, sources, extracted facts and uncertainty without editing raw data.

- [ ] **Step 1: Write failing merchant-form tests**

Test successful submission, required name/city/industry validation, invalid source URL rejection, product entry, and server error display. The form must submit a `MerchantCreate` matching the backend schema exactly.

- [ ] **Step 2: Implement merchant list, creation and detail pages**

Use labeled form fields and a source repeater. Display completeness as confirmed fields out of total fields, not as an unexplained model score.

- [ ] **Step 3: Run merchant UI tests**

Run: `cd apps/web; npm test -- merchant-form.test.tsx`

Expected: PASS.

- [ ] **Step 4: Write failing query review tests**

Test category filters, inline edit, approval, rejection, enable toggle and batch approval. Ensure disabled or rejected queries are visibly excluded from the scan count.

- [ ] **Step 5: Implement the query library screen**

Use a dense accessible table with category tabs. Show question, category, reason, priority, review state and enabled state. The primary action is `批准并用于检测`, not a conversational AI button.

- [ ] **Step 6: Run query UI tests**

Run: `cd apps/web; npm test -- query-table.test.tsx`

Expected: PASS.

- [ ] **Step 7: Write failing scan and report tests**

Test queued/running/completed/partial/failed progress, single-result retry availability, raw evidence expansion, uncertain labels, report metric rendering and history delta direction.

- [ ] **Step 8: Implement scan, report and history screens**

Poll a running scan every five seconds and stop polling in terminal states. Evidence opens in a side drawer. Facts, inferences and recommendations use distinct labels. The history page requires explicit left and right scan selection and shows deltas without causal language.

- [ ] **Step 9: Run workflow UI tests**

Run: `cd apps/web; npm test -- merchant-form.test.tsx query-table.test.tsx scan-report.test.tsx`

Expected: PASS.

- [ ] **Step 10: Commit management screens**

```bash
git add apps/web/src/app apps/web/src/components apps/web/tests
git commit -m "feat: add merchant exposure management workflow"
```

---

### Task 8: O'eat Demo Seed, End-to-End Proof and Operator Documentation

**Files:**
- Create: `services/api/scripts/seed_demo.py`
- Create: `services/api/tests/scripts/test_seed_demo.py`
- Create: `apps/web/e2e/demo-flow.spec.ts`
- Create: `docs/operator-guide.md`
- Modify: `README.md`
- Modify: `apps/web/playwright.config.ts`

**Interfaces:**
- Consumes: all earlier application interfaces.
- Produces: idempotent `python -m scripts.seed_demo` command.
- Produces: one browser-level proof from seeded merchant to report evidence.
- Produces: operator instructions for API mode, manual mode and App sampling.

- [ ] **Step 1: Write a failing idempotent seed test**

```python
def test_seed_demo_is_idempotent(db_session):
    first = seed_demo(db_session)
    second = seed_demo(db_session)
    assert first.merchant_id == second.merchant_id
    assert count_merchants(db_session, normalized_name="o'eat gastronomy") == 1
    assert count_queries(db_session, first.query_set_id) == 30
```

- [ ] **Step 2: Run the seed test and verify it fails**

Run: `cd services/api; python -m pytest tests/scripts/test_seed_demo.py -v`

Expected: FAIL because the seed command is absent.

- [ ] **Step 3: Implement the O'eat demo seed**

Seed the verified public facts only: name `O'eat Gastronomy`, branch `杭州万象城店`, city `杭州`, industry `餐饮`, and the public Meituan URL. Leave address, price and opening hours unset unless a cited source is added. Generate 30 questions through the normal query generator and approve them through the service API.

- [ ] **Step 4: Run the seed test**

Run: `cd services/api; python -m pytest tests/scripts/test_seed_demo.py -v`

Expected: PASS.

- [ ] **Step 5: Write the browser-level demo test**

```ts
test("operator can inspect a completed evidence report", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("选择商家").selectOption({ label: "O'eat Gastronomy（杭州万象城店）" });
  await expect(page.getByText("品牌出现率")).toBeVisible();
  await page.getByRole("link", { name: "查看检测报告" }).click();
  await page.getByRole("button", { name: "查看证据" }).first().click();
  await expect(page.getByRole("heading", { name: "原始回答" })).toBeVisible();
  await expect(page.getByText("自动检测结果不等同于豆包 App 固定排名")).toBeVisible();
});
```

- [ ] **Step 6: Add deterministic E2E fixtures and run the demo test**

Use the manual adapter fixture so the test makes no paid or network calls.

Run: `cd apps/web; npx playwright test e2e/demo-flow.spec.ts`

Expected: PASS.

- [ ] **Step 7: Write operator documentation**

Document these exact workflows:

1. Start PostgreSQL, API, worker and web with Docker Compose.
2. Run migrations and seed O'eat.
3. Use manual adapter mode without API credentials.
4. Configure `ARK_API_KEY` only in the server environment.
5. Create and monitor a live scan.
6. Record 10豆包 App manual checks without copying personal reviewer data.
7. Interpret mention rate, first-position rate, source coverage and uncertainty.
8. Run a second scan and compare dates without claiming causality.

- [ ] **Step 8: Run the final relevant verification once**

Run: `cd services/api; python -m pytest -v`

Expected: all backend tests PASS.

Run: `cd apps/web; npm test`

Expected: all frontend unit tests PASS.

Run: `cd apps/web; npx playwright test e2e/demo-flow.spec.ts`

Expected: demo flow PASS.

Run: `docker compose config`

Expected: valid Compose configuration with `db`, `api`, `worker`, and `web`.

- [ ] **Step 9: Commit the demo and documentation**

```bash
git add services/api/scripts services/api/tests/scripts apps/web/e2e apps/web/playwright.config.ts docs/operator-guide.md README.md
git commit -m "test: prove merchant exposure demo workflow"
```

---

## Implementation Completion Checklist

- [ ] All eight tasks are committed in order with no unrelated files staged.
- [ ] O'eat is seed data rather than hard-coded product behavior.
- [ ] Manual mode passes without network access or paid calls.
- [ ] Live Ark mode reads its key only from the server environment.
- [ ] Raw answers and citations remain unchanged after re-analysis.
- [ ] Every finding links to at least one saved evidence reference.
- [ ] Metrics use deterministic code and documented denominators.
- [ ] Partial and failed scans remain inspectable.
- [ ] Dashboard follows the approved editorial visual rules.
- [ ] Final backend, frontend, E2E and Compose checks pass once after the last change.
