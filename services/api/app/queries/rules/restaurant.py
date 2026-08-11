from dataclasses import dataclass

from app.queries.schemas import QueryCategory, QueryDraft


@dataclass
class RestaurantProfile:
    merchant_name: str
    facts: dict[str, object]


class RestaurantRulePack:
    name = "restaurant-v2"
    required_fact_keys = frozenset(
        {
            "location.city",
            "category.precise",
            "location.venue",
            "price.display",
            "product.list",
            "occasion.list",
            "need.transport",
            "service.baby_chair",
        }
    )

    def generate(self, profile: RestaurantProfile, count: int) -> list[QueryDraft]:
        if count < 6 or count > 100:
            raise ValueError("count must be between 6 and 100")

        city = self._text(profile.facts, "location.city")
        category = self._text(profile.facts, "category.precise")
        if not city or not category:
            raise ValueError("confirmed city and precise category are required")

        venue = self._text(profile.facts, "location.venue")
        district = self._text(profile.facts, "location.district")
        scopes = list(dict.fromkeys(filter(None, [f"{city}{venue}" if venue else None, district, city])))
        drafts: list[QueryDraft] = []
        seen: set[str] = set()

        def add(
            text: str,
            query_category: QueryCategory,
            reason: str,
            fact_keys: list[str],
            intent_type: str = "recommendation",
            priority: int = 1,
        ) -> None:
            normalized = " ".join(text.split())
            if normalized in seen:
                return
            seen.add(normalized)
            drafts.append(
                QueryDraft(
                    text=normalized,
                    category=query_category,
                    reason=reason,
                    priority=priority,
                    intent_type=intent_type,
                    fact_keys=fact_keys,
                )
            )

        qualifiers = ["值得去的", "口碑好的", "评价稳定的", "环境舒服的", "适合第一次去的", "近期受欢迎的"]
        for scope in scopes:
            scope_keys = ["location.city", "category.precise"]
            if venue and venue in scope:
                scope_keys.append("location.venue")
            if district and district == scope:
                scope_keys.append("location.district")
            for qualifier in qualifiers:
                add(
                    f"{scope}有什么{qualifier}{category}？",
                    "category" if scope == city else "geo",
                    "检测精准品类在真实地域推荐中的覆盖",
                    scope_keys,
                )

        price = self._text(profile.facts, "price.display")
        if price:
            for text in (
                f"{city}{price}的{category}有哪些？",
                f"请推荐{city}{price}、评价稳定的{category}",
                f"{city}预算为{price}时，哪些{category}值得考虑？",
            ):
                add(
                    text,
                    "price",
                    "检测真实价格区间下的推荐覆盖",
                    ["location.city", "category.precise", "price.display"],
                )

        occasions = profile.facts.get("occasion.list")
        if isinstance(occasions, list):
            for occasion in occasions:
                if not isinstance(occasion, str) or not occasion.strip():
                    continue
                for scope in scopes[:2]:
                    add(
                        f"{scope}适合{occasion}的{category}有哪些？",
                        "occasion",
                        "检测已确认消费场景下的推荐覆盖",
                        ["location.city", "category.precise", "occasion.list"],
                    )

        transport = self._text(profile.facts, "need.transport")
        if transport:
            for scope in scopes:
                add(
                    f"{scope}有哪些{transport}的{category}？",
                    "need",
                    "检测已确认交通条件下的推荐覆盖",
                    ["location.city", "category.precise", "need.transport"],
                )

        if profile.facts.get("service.baby_chair") is True:
            for scope in scopes:
                add(
                    f"{scope}有哪些可以带宝宝去、有宝宝椅的{category}？",
                    "need",
                    "检测已确认亲子设施下的推荐覆盖",
                    ["location.city", "category.precise", "service.baby_chair"],
                )

        verification_labels = {
            "location.venue": "门店是否位于该商场",
            "price.display": "公开价格区间是否一致",
            "service.baby_chair": "是否提供宝宝椅",
            "need.transport": "交通条件是否方便",
        }
        for field_key, label in verification_labels.items():
            if field_key not in profile.facts:
                continue
            add(
                f"{profile.merchant_name}{label}？有哪些公开来源可以证明？",
                "need" if field_key.startswith(("service.", "need.")) else "geo" if field_key.startswith("location.") else "price",
                "验证商家关键事实能否被公开检索和引用",
                [field_key],
                intent_type="verification",
            )

        add(
            f"{profile.merchant_name}是一家{city}的{category}吗？有哪些公开来源？",
            "category",
            "验证商家的精准品类公开关联",
            ["location.city", "category.precise"],
            intent_type="verification",
        )

        if len(drafts) < count:
            wording = ["推荐几家", "有哪些值得选择", "哪几家比较合适", "有哪些可供比较", "有哪些选择"]
            index = 0
            while len(drafts) < count:
                scope = scopes[index % len(scopes)]
                phrase = wording[(index // len(scopes)) % len(wording)]
                add(
                    f"{scope}{phrase}的{category}？",
                    "category",
                    "补充精准品类的自然语言推荐表达",
                    ["location.city", "category.precise"],
                    priority=2,
                )
                index += 1
                if index > 100:
                    raise ValueError("not enough confirmed profile facts to generate unique queries")

        return drafts[:count]

    @staticmethod
    def _text(facts: dict[str, object], key: str) -> str | None:
        value = facts.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None
