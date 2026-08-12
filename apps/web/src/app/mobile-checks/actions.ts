"use server";

import { redirect } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const sourceTypes: Record<string, string> = { 机构介绍: "profile", 工商: "registry", 招聘: "recruitment", 抖音: "douyin", 本地媒体: "local_media", 政府医院: "government", 行业内容: "industry" };

export async function createMobileValidationSet(formData: FormData): Promise<void> {
  const merchantId = String(formData.get("merchantId") ?? "");
  const response = await fetch(`${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/mobile-validation-sets`, { method: "POST" });
  if (!response.ok) throw new Error("创建手机验证题集失败，请先审核并启用问题");
  redirect(`/mobile-checks?merchant=${encodeURIComponent(merchantId)}`);
}

export async function saveMobileRound(formData: FormData): Promise<void> {
  const merchantId = String(formData.get("merchantId") ?? "");
  const validationSetId = String(formData.get("validationSetId") ?? "");
  const itemIds = String(formData.get("itemIds") ?? "").split(",").filter(Boolean);
  const results = itemIds.map((id) => ({ validation_item_id: id, mention_level: String(formData.get(`mention-${id}`) ?? "none"), competitors: String(formData.get(`competitors-${id}`) ?? "").split(/[、,，]/).map((item) => item.trim()).filter(Boolean), information_accurate: formData.get(`accurate-${id}`) === "on" ? true : null, answer_excerpt: String(formData.get(`excerpt-${id}`) ?? "") || null, is_confirmed: true }));
  const sources = String(formData.get("sources") ?? "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line) => { const [entity_name, rawType, title, rawFacts, url] = line.split("｜").map((item) => item?.trim()); return { title: title || line, url: url || null, source_type: sourceTypes[rawType] ?? "other", entity_name: entity_name || "待核对", facts: rawFacts ? rawFacts.split(/[、,，]/).filter(Boolean) : [], evidence_kind: "self_reported", access_status: "unknown", is_confirmed: Boolean(entity_name && rawType && title) }; });
  const inherited = formData.get("inheritSources") === "on" ? String(formData.get("sourceRoundId") ?? "") || null : null;
  const response = await fetch(`${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/mobile-check-rounds`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ validation_set_id: validationSetId, location_text: String(formData.get("location") ?? "") || null, web_search_enabled: formData.get("webSearch") === "on", raw_qa_text: String(formData.get("rawQaText") ?? ""), inherited_source_round_id: inherited, results, sources: inherited ? [] : sources }) });
  if (!response.ok) throw new Error("保存手机版实测失败");
  const round = await response.json() as { id: string };
  for (const entry of formData.getAll("evidence")) if (entry instanceof File && entry.size > 0) await fetch(`${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/mobile-check-rounds/${round.id}/evidence`, { method: "POST", headers: { "content-type": entry.type, "x-filename": encodeURIComponent(entry.name) }, body: entry });
  await fetch(`${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/mobile-check-rounds/${round.id}/confirm`, { method: "POST" });
  redirect(`/mobile-checks?merchant=${encodeURIComponent(merchantId)}`);
}
