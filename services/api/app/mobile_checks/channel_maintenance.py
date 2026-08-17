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
    domain = (source.domain or "").strip().lower()
    if domain:
        return domain.removeprefix("www.")
    if not source.url:
        return None
    hostname = urlsplit(source.url).hostname
    return hostname.removeprefix("www.") if hostname else None


def _access(statuses: list[str]) -> str:
    if "maintainable" in statuses:
        return "maintainable"
    if "correctable" in statuses:
        return "correctable"
    return "reference"


def build_channel_maintenance(
    sources: list[MobileRoundSource],
    actions: list[dict],
) -> dict:
    grouped: dict[str, dict] = {}
    for source in sources:
        domain = _domain(source)
        if not source.is_confirmed or not domain:
            continue
        channel = grouped.setdefault(
            domain,
            {
                "domain": domain,
                "citationCount": 0,
                "accessStatuses": [],
                "sourceTypes": [],
                "links": [],
            },
        )
        channel["citationCount"] += 1
        channel["accessStatuses"].append(source.access_status)
        source_label = SOURCE_TYPE_LABELS.get(
            source.source_type,
            SOURCE_TYPE_LABELS["other"],
        )
        if source_label not in channel["sourceTypes"]:
            channel["sourceTypes"].append(source_label)
        if source.url and not any(
            link["url"] == source.url for link in channel["links"]
        ):
            channel["links"].append({"title": source.title, "url": source.url})

    cited_channels = []
    for channel in grouped.values():
        access = _access(channel.pop("accessStatuses"))
        channel["access"] = access
        channel["accessLabel"] = ACCESS_LABELS[access]
        channel["links"] = channel["links"][:2]
        cited_channels.append(channel)

    candidate_channels = []
    seen_candidates: set[str] = set()
    for action in actions:
        for target in action.get("publishTargets", []):
            name = str(target.get("channel", "")).strip()
            if not name or name in seen_candidates:
                continue
            seen_candidates.add(name)
            candidate_channels.append(
                {
                    "channel": name,
                    "content": str(target.get("content", "")).strip(),
                }
            )

    return {
        "citedChannels": cited_channels,
        "candidateChannels": candidate_channels,
    }
