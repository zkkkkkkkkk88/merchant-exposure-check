from app.mobile_checks.channel_maintenance import build_channel_maintenance
from app.mobile_checks.models import MobileRoundSource


def source(
    *,
    domain: str | None,
    url: str | None,
    access_status: str,
    title: str,
    source_type: str = "profile",
) -> MobileRoundSource:
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


def test_groups_confirmed_sources_and_deduplicates_links_and_candidates() -> None:
    result = build_channel_maintenance(
        [
            source(
                domain="m.map.360.cn",
                url="https://m.map.360.cn/store/1",
                access_status="correctable",
                title="地图门店",
            ),
            source(
                domain="m.map.360.cn",
                url="https://m.map.360.cn/store/1",
                access_status="reference",
                title="重复页面",
            ),
            source(
                domain=None,
                url="https://m.jobui.com/company/2",
                access_status="maintainable",
                title="企业主页",
                source_type="recruitment",
            ),
        ],
        [
            {
                "publishTargets": [
                    {
                        "priority": 1,
                        "channel": "地图商户页",
                        "content": "补充地址和服务",
                    }
                ]
            },
            {
                "publishTargets": [
                    {
                        "priority": 2,
                        "channel": "地图商户页",
                        "content": "重复建议",
                    },
                    {
                        "priority": 1,
                        "channel": "机构官网",
                        "content": "发布完整介绍",
                    },
                ]
            },
        ],
    )

    assert result["citedChannels"] == [
        {
            "domain": "m.map.360.cn",
            "citationCount": 2,
            "access": "correctable",
            "accessLabel": "需要认领或纠错",
            "sourceTypes": ["机构或门店主页"],
            "links": [
                {
                    "title": "地图门店",
                    "url": "https://m.map.360.cn/store/1",
                }
            ],
        },
        {
            "domain": "m.jobui.com",
            "citationCount": 1,
            "access": "maintainable",
            "accessLabel": "可直接维护",
            "sourceTypes": ["招聘或企业主页"],
            "links": [
                {
                    "title": "企业主页",
                    "url": "https://m.jobui.com/company/2",
                }
            ],
        },
    ]
    assert result["candidateChannels"] == [
        {"channel": "地图商户页", "content": "补充地址和服务"},
        {"channel": "机构官网", "content": "发布完整介绍"},
    ]


def test_ignores_unconfirmed_and_unidentifiable_sources() -> None:
    unconfirmed = source(
        domain="example.com",
        url="https://example.com/hidden",
        access_status="unknown",
        title="未确认来源",
    )
    unconfirmed.is_confirmed = False
    no_domain = source(
        domain=None,
        url=None,
        access_status="unknown",
        title="无域名来源",
    )

    result = build_channel_maintenance([unconfirmed, no_domain], [])

    assert result == {"citedChannels": [], "candidateChannels": []}
