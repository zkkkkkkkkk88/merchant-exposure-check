# Public Information Channel Maintenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an actionable “公开信息渠道维护清单” to the delivery report using confirmed API-discovered sources and existing publish-target recommendations.

**Architecture:** A pure backend helper groups confirmed sources by normalized domain and converts existing playbook publish targets into deduplicated candidate channels. The mobile workspace API exposes this view model, and a focused React component renders it inside report section 04 without introducing persistent task state.

**Tech Stack:** Python 3, FastAPI/SQLAlchemy models, pytest, Next.js/React/TypeScript, Vitest/Testing Library, existing CSS design tokens.

## Global Constraints

- Separate “本轮实际引用” from “候选维护渠道”.
- Never invent a URL; render only URLs stored on confirmed sources.
- Map `maintainable` to “可直接维护”, `correctable` to “需要认领或纠错”, and `reference`/`unknown` to “仅供参考”.
- Keep the module in printed/PDF reports; only the raw-answer appendix remains print-hidden.
- State that maintenance can improve retrieval and accurate citation probability but cannot guarantee first-batch recommendation.
- Preserve the existing delivery report visual system and avoid unrelated refactors.

---

### Task 1: Build the channel-maintenance view model

**Files:**
- Create: `services/api/app/mobile_checks/channel_maintenance.py`
- Create: `services/api/tests/mobile_checks/test_channel_maintenance.py`

**Interfaces:**
- Consumes: `list[MobileRoundSource]` and playbook action dictionaries containing `publishTargets`.
- Produces: `build_channel_maintenance(sources: list[MobileRoundSource], actions: list[dict]) -> dict` with `citedChannels` and `candidateChannels`.

- [ ] **Step 1: Write failing aggregation tests**

```python
from app.mobile_checks.channel_maintenance import build_channel_maintenance
from app.mobile_checks.models import MobileRoundSource


def source(*, domain: str | None, url: str | None, access_status: str, title: str, source_type: str = "profile") -> MobileRoundSource:
    return MobileRoundSource(
        title=title,
        url=url,
        domain=domain,
        source_type=source_type,
        entity_name="示例口腔",
        facts=[],
        evidence_kind="third_party",
        access_status=access_status,
        is_confirmed=True,
    )


def test_groups_confirmed_sources_and_deduplicates_links_and_candidates():
    result = build_channel_maintenance(
        [
            source(domain="m.map.360.cn", url="https://m.map.360.cn/store/1", access_status="correctable", title="地图门店"),
            source(domain="m.map.360.cn", url="https://m.map.360.cn/store/1", access_status="reference", title="重复页面"),
            source(domain=None, url="https://m.jobui.com/company/2", access_status="maintainable", title="企业主页", source_type="recruitment"),
        ],
        [
            {"publishTargets": [{"priority": 1, "channel": "地图商户页", "content": "补充地址和服务"}]},
            {"publishTargets": [{"priority": 2, "channel": "地图商户页", "content": "重复建议"}, {"priority": 1, "channel": "机构官网", "content": "发布完整介绍"}]},
        ],
    )

    assert result["citedChannels"][0] == {
        "domain": "m.map.360.cn",
        "citationCount": 2,
        "access": "correctable",
        "accessLabel": "需要认领或纠错",
        "sourceTypes": ["机构或门店主页"],
        "links": [{"title": "地图门店", "url": "https://m.map.360.cn/store/1"}],
    }
    assert result["citedChannels"][1]["domain"] == "m.jobui.com"
    assert result["candidateChannels"] == [
        {"channel": "地图商户页", "content": "补充地址和服务"},
        {"channel": "机构官网", "content": "发布完整介绍"},
    ]


def test_ignores_unconfirmed_and_unidentifiable_sources():
    hidden = source(domain=None, url=None, access_status="unknown", title="无域名")
    hidden.is_confirmed = False
    result = build_channel_maintenance([hidden], [])
    assert result == {"citedChannels": [], "candidateChannels": []}
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest services/api/tests/mobile_checks/test_channel_maintenance.py -q`

Expected: FAIL because `app.mobile_checks.channel_maintenance` does not exist.

- [ ] **Step 3: Implement the pure aggregator**

Create `channel_maintenance.py` with:

```python
from urllib.parse import urlsplit

from app.mobile_checks.models import MobileRoundSource

ACCESS_LABELS = {
    "maintainable": "可直接维护",
    "correctable": "需要认领或纠错",
    "reference": "仅供参考",
}
SOURCE_TYPE_LABELS = {
    "profile": "机构或门店主页",
    "registry": "登记或资质页面",
    "recruitment": "招聘或企业主页",
    "douyin": "短视频公开主页",
    "local_media": "本地媒体",
    "government": "政府公开页面",
    "industry": "行业平台",
    "other": "其他公开来源",
}


def _domain(source: MobileRoundSource) -> str | None:
    value = (source.domain or "").strip().lower()
    if value:
        return value.removeprefix("www.")
    if source.url:
        return urlsplit(source.url).hostname.removeprefix("www.") if urlsplit(source.url).hostname else None
    return None


def build_channel_maintenance(sources: list[MobileRoundSource], actions: list[dict]) -> dict:
    grouped: dict[str, dict] = {}
    for source in sources:
        domain = _domain(source)
        if not source.is_confirmed or not domain:
            continue
        channel = grouped.setdefault(domain, {
            "domain": domain,
            "citationCount": 0,
            "accessStatuses": [],
            "sourceTypes": [],
            "links": [],
        })
        channel["citationCount"] += 1
        channel["accessStatuses"].append(source.access_status)
        source_label = SOURCE_TYPE_LABELS.get(source.source_type, SOURCE_TYPE_LABELS["other"])
        if source_label not in channel["sourceTypes"]:
            channel["sourceTypes"].append(source_label)
        if source.url and not any(link["url"] == source.url for link in channel["links"]):
            channel["links"].append({"title": source.title, "url": source.url})

    cited_channels = []
    for channel in grouped.values():
        statuses = channel.pop("accessStatuses")
        access = "maintainable" if "maintainable" in statuses else "correctable" if "correctable" in statuses else "reference"
        channel["access"] = access
        channel["accessLabel"] = ACCESS_LABELS[access]
        channel["links"] = channel["links"][:2]
        cited_channels.append(channel)

    candidate_channels = []
    seen_candidates: set[str] = set()
    for action in actions:
        for target in action.get("publishTargets", []):
            channel = str(target.get("channel", "")).strip()
            if not channel or channel in seen_candidates:
                continue
            seen_candidates.add(channel)
            candidate_channels.append({
                "channel": channel,
                "content": str(target.get("content", "")).strip(),
            })

    return {"citedChannels": cited_channels, "candidateChannels": candidate_channels}
```

Implement stable first-seen ordering. For access aggregation use `maintainable`, then `correctable`, otherwise `reference`. Deduplicate candidate channels by exact trimmed channel name and retain the first content string.

- [ ] **Step 4: Run the focused backend tests and verify GREEN**

Run: `python -m pytest services/api/tests/mobile_checks/test_channel_maintenance.py -q`

Expected: 2 passed.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- services/api/app/mobile_checks/channel_maintenance.py services/api/tests/mobile_checks/test_channel_maintenance.py
git commit -m "feat: aggregate public maintenance channels"
```

---

### Task 2: Expose channel maintenance in the mobile workspace API

**Files:**
- Modify: `services/api/app/mobile_checks/service.py`
- Modify: `services/api/app/mobile_checks/schemas.py`
- Modify: `services/api/tests/mobile_checks/test_service.py`
- Modify: `apps/web/src/lib/contracts.ts`

**Interfaces:**
- Consumes: `build_channel_maintenance(confirmed_sources, playbook["actions"])` from Task 1.
- Produces: `MobileWorkspaceData.channelMaintenance` matching the spec.

- [ ] **Step 1: Extend the service test with a failing API assertion**

In the workspace test that creates confirmed sources, add representative `MobileRoundSource` rows and assert:

```python
assert workspace["channelMaintenance"] == {
    "citedChannels": [{
        "domain": "m.map.360.cn",
        "citationCount": 2,
        "access": "correctable",
        "accessLabel": "需要认领或纠错",
        "sourceTypes": ["机构或门店主页"],
        "links": [{"title": "地图门店", "url": "https://m.map.360.cn/store/1"}],
    }],
    "candidateChannels": workspace["channelMaintenance"]["candidateChannels"],
}
```

Also extend the empty-workspace assertion:

```python
assert workspace["channelMaintenance"] == {"citedChannels": [], "candidateChannels": []}
```

- [ ] **Step 2: Run the service tests and verify RED**

Run: `python -m pytest services/api/tests/mobile_checks/test_service.py -q`

Expected: FAIL because `channelMaintenance` is absent.

- [ ] **Step 3: Wire the helper into `get_workspace`**

Import `build_channel_maintenance`. Return empty arrays when no latest round exists. After `playbook` is built, compute:

```python
channel_maintenance = build_channel_maintenance(
    confirmed_sources,
    playbook.get("actions", []),
)
```

Include it as `"channelMaintenance": channel_maintenance` in the workspace response. Add `channelMaintenance: dict` to `MobileWorkspaceResponse` in `schemas.py`.

- [ ] **Step 4: Add the TypeScript contract**

Add to `MobileWorkspaceData`:

```ts
channelMaintenance?: {
  citedChannels: Array<{
    domain: string;
    citationCount: number;
    access: "maintainable" | "correctable" | "reference";
    accessLabel: string;
    sourceTypes: string[];
    links: Array<{ title: string; url: string }>;
  }>;
  candidateChannels: Array<{ channel: string; content: string }>;
};
```

- [ ] **Step 5: Run backend service tests and Web type-aware tests**

Run: `python -m pytest services/api/tests/mobile_checks/test_service.py services/api/tests/mobile_checks/test_channel_maintenance.py -q`

Run: `npm test -- tests/delivery-report.test.tsx`

Expected: backend tests pass; existing delivery report test passes without requiring the optional field.

- [ ] **Step 6: Commit Task 2**

```powershell
git add -- services/api/app/mobile_checks/service.py services/api/app/mobile_checks/schemas.py services/api/tests/mobile_checks/test_service.py apps/web/src/lib/contracts.ts
git commit -m "feat: expose maintenance channels in workspace"
```

---

### Task 3: Render the report maintenance checklist

**Files:**
- Create: `apps/web/src/components/public-channel-maintenance.tsx`
- Modify: `apps/web/src/app/delivery-report/page.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Modify: `apps/web/tests/delivery-report.test.tsx`

**Interfaces:**
- Consumes: `MobileWorkspaceData["channelMaintenance"]` from Task 2.
- Produces: accessible report markup with real external links and printable content.

- [ ] **Step 1: Add failing report assertions**

Extend the mocked workspace:

```ts
channelMaintenance: {
  citedChannels: [{
    domain: "m.map.360.cn",
    citationCount: 2,
    access: "correctable",
    accessLabel: "需要认领或纠错",
    sourceTypes: ["机构或门店主页"],
    links: [{ title: "地图门店", url: "https://m.map.360.cn/store/1" }],
  }],
  candidateChannels: [{ channel: "机构官网", content: "发布完整机构介绍" }],
},
```

Assert:

```ts
expect(screen.getByRole("heading", { name: "公开信息渠道维护清单" })).toBeVisible();
expect(screen.getByText("m.map.360.cn")).toBeVisible();
expect(screen.getByText("引用 2 次")).toBeVisible();
expect(screen.getByText("需要认领或纠错")).toBeVisible();
expect(screen.getByRole("link", { name: "地图门店" })).toHaveAttribute("href", "https://m.map.360.cn/store/1");
expect(screen.getByText("机构官网")).toBeVisible();
expect(screen.getByText(/不保证首批推荐/)).toBeVisible();
```

- [ ] **Step 2: Run the report test and verify RED**

Run: `npm test -- tests/delivery-report.test.tsx`

Expected: FAIL because the maintenance module is not rendered.

- [ ] **Step 3: Create the focused component**

Create `PublicChannelMaintenance` with this structure:

```tsx
import type { MobileWorkspaceData } from "@/lib/contracts";

type Data = NonNullable<MobileWorkspaceData["channelMaintenance"]>;

export function PublicChannelMaintenance({ data }: { data: Data }) {
  return <section className="report-channel-maintenance" aria-label="公开信息渠道维护清单">
    <header>
      <h3>公开信息渠道维护清单</h3>
      <p>根据本轮公开来源整理，实际引用与候选维护渠道分开展示。</p>
    </header>
    <div className="report-channel-block">
      <h4>本轮实际引用</h4>
      {data.citedChannels.length > 0 ? <div className="report-cited-channel-grid">
        {data.citedChannels.map((channel) => <article key={channel.domain}>
          <header><strong>{channel.domain}</strong><span className={`report-channel-badge ${channel.access}`}>{channel.accessLabel}</span></header>
          <p>引用 {channel.citationCount} 次 · {channel.sourceTypes.join("、")}</p>
          {channel.links.length > 0 && <ul>{channel.links.map((link) => <li key={link.url}><a href={link.url} target="_blank" rel="noreferrer">{link.title}</a></li>)}</ul>}
        </article>)}
      </div> : <p className="report-empty">本轮没有可确认域名的实际引用来源。</p>}
    </div>
    <div className="report-channel-block">
      <h4>候选维护渠道</h4>
      {data.candidateChannels.length > 0 ? <ul className="report-candidate-channel-list">
        {data.candidateChannels.map((candidate) => <li key={candidate.channel}><strong>{candidate.channel}</strong><span>{candidate.content}</span></li>)}
      </ul> : <p className="report-empty">本轮暂无额外候选维护渠道。</p>}
    </div>
    <div className="report-channel-guidance">
      <p><strong>统一信息要求：</strong>商家名称、城市、品类、地址、电话和核心服务保持一致。</p>
      <p>完善公开信息可以提高被检索和正确引用的概率，但不保证进入首批推荐。</p>
    </div>
  </section>;
}
```

Render actual links with `target="_blank" rel="noreferrer"`. Show a clear empty state when `citedChannels` is empty. Always render the consistency requirement and boundary statement when the component is present.

- [ ] **Step 4: Integrate into section 04 and style responsively**

Import the component in `delivery-report/page.tsx` and render:

```tsx
{workspace?.channelMaintenance && (
  <PublicChannelMaintenance data={workspace.channelMaintenance} />
)}
```

Add `.report-channel-maintenance`, `.report-cited-channel-grid`, `.report-channel-badge`, and `.report-candidate-channel-list` styles using existing `--line`, `--muted`, `--accent`, `--ink`, and serif tokens. Use a three-column cited-channel grid on desktop and one column inside the existing `@media (max-width: 800px)` block. Do not add the module to the print-hidden selector.

- [ ] **Step 5: Run focused frontend tests and verify GREEN**

Run: `npm test -- tests/delivery-report.test.tsx`

Expected: all delivery-report tests pass.

- [ ] **Step 6: Run full relevant verification**

Run: `python -m pytest services/api/tests/mobile_checks -q`

Run: `npm test`

Expected: both suites exit 0 with no failures.

- [ ] **Step 7: Visually verify the existing local report**

Open the current merchant delivery report in the user-selected in-app browser. Verify:

- actual and candidate channels are visually distinct;
- long domains and URLs wrap without overflow;
- mobile width collapses to one column;
- the module remains visible in print CSS;
- the raw-answer appendix remains print-hidden.

- [ ] **Step 8: Commit Task 3**

```powershell
git add -- apps/web/src/components/public-channel-maintenance.tsx apps/web/src/app/delivery-report/page.tsx apps/web/src/styles/globals.css apps/web/tests/delivery-report.test.tsx
git commit -m "feat: add report channel maintenance checklist"
```
