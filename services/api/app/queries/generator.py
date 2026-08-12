from collections.abc import Callable

from app.merchants.schemas import MerchantRead
from app.queries.schemas import QueryCategory, QueryDraft

CATEGORIES: tuple[QueryCategory, ...] = (
    "geo",
    "category",
    "product",
    "price",
    "occasion",
    "need",
)


class TemplateQueryGenerator:
    name = "template-v1"

    def generate(self, merchant: MerchantRead, count: int) -> list[QueryDraft]:
        if count < len(CATEGORIES) or count > 100:
            raise ValueError("count must be between 6 and 100")

        buckets = {
            category: self._category_drafts(merchant, category) for category in CATEGORIES
        }
        drafts: list[QueryDraft] = []
        offset = 0
        while len(drafts) < count:
            for category in CATEGORIES:
                if len(drafts) == count:
                    break
                drafts.append(buckets[category][offset])
            offset += 1
        return drafts

    def _category_drafts(
        self,
        merchant: MerchantRead,
        category: QueryCategory,
    ) -> list[QueryDraft]:
        if merchant.district:
            scopes = [merchant.district, merchant.city, f"{merchant.city}{merchant.district}"]
        else:
            scopes = [merchant.city, f"{merchant.city}市区", f"{merchant.city}市中心"]
        qualifiers = ["", "口碑好的", "本地人常去的", "环境舒服的", "评价稳定的", "近期热门的"]
        products = merchant.products or [merchant.industry]
        scenes = ["约会", "朋友聚餐", "家庭聚会", "工作日午餐", "周末休闲", "庆祝纪念日"]
        needs = ["交通方便", "可以预约", "适合拍照", "服务稳定", "菜品选择多", "适合第一次去"]
        price_labels = [merchant.price_range] if merchant.price_range else ["50元以内", "100元以内", "200元以内"]

        builders: dict[QueryCategory, Callable[[str, str, int], str]] = {
            "geo": lambda scope, qualifier, index: f"{scope}{qualifier}{merchant.industry}有哪些？",
            "category": lambda scope, qualifier, index: f"请推荐{scope}{qualifier}{merchant.industry}",
            "product": lambda scope, qualifier, index: (
                f"{scope}{qualifier}能吃到{products[index % len(products)]}的店推荐"
            ),
            "price": lambda scope, qualifier, index: (
                f"{scope}{price_labels[index % len(price_labels)]}的{qualifier}{merchant.industry}有哪些？"
            ),
            "occasion": lambda scope, qualifier, index: (
                f"{scope}{qualifier}适合{scenes[index % len(scenes)]}的{merchant.industry}推荐"
            ),
            "need": lambda scope, qualifier, index: (
                f"{scope}{qualifier}{merchant.industry}哪家{needs[index % len(needs)]}？"
            ),
        }

        drafts: list[QueryDraft] = []
        for scope in scopes:
            for qualifier in qualifiers:
                index = len(drafts)
                drafts.append(
                    QueryDraft(
                        text=builders[category](scope, qualifier, index),
                        category=category,
                        reason=self._reason(category),
                        priority=1 if index < 3 else 2,
                    )
                )
        return drafts

    @staticmethod
    def _reason(category: QueryCategory) -> str:
        reasons = {
            "geo": "验证商家在主要经营地域中的基础发现能力",
            "category": "验证商家与所属行业品类的关联强度",
            "product": "验证具体产品或服务是否能触发商家提及",
            "price": "验证价格条件下的商家覆盖情况",
            "occasion": "验证消费场景与商家的公开关联",
            "need": "验证具体决策需求下的推荐覆盖情况",
        }
        return reasons[category]
