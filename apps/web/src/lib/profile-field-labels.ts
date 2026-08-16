const PROFILE_FIELD_LABELS: Record<string, string> = {
  "identity.official_name": "机构正式名称",
  "location.city": "省份 / 城市",
  "location.district": "区县 / 区域",
  "location.venue": "商场 / 商圈",
  "location.address": "详细地址",
  "category.legacy": "原行业品类",
  "category.precise": "精准品类",
  "price.display": "价格区间",
  "hours.display": "营业时间",
  "contact.phone": "联系电话",
  "product.list": "产品 / 服务项目",
  "strength.list": "特色优势",
  "service.baby_chair": "宝宝椅",
  "service.smoke_free": "无烟环境",
  "service.open_kitchen": "明厨亮灶",
  "service.parking": "停车信息",
  "service.private_room": "包间",
  "need.transport": "交通条件",
  "occasion.list": "适用场景",
};

export function profileFieldLabel(fieldKey: string): string {
  return PROFILE_FIELD_LABELS[fieldKey] ?? "其他已确认资料";
}
