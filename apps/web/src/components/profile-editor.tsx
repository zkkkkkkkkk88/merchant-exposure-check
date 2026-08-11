"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  generateQuerySet,
  parseMerchantProfile,
  replaceMerchantProfile,
} from "@/lib/api";
import type { MerchantProfileData, MerchantProfileFactData, ProfileValue } from "@/lib/contracts";

const labels: Record<string, string> = {
  "location.city": "城市",
  "location.district": "区域",
  "location.venue": "商场 / 商圈",
  "location.address": "详细地址",
  "category.legacy": "原行业",
  "category.precise": "精准品类",
  "price.display": "价格区间",
  "hours.display": "营业时间",
  "product.list": "招牌产品",
  "strength.list": "特色优势",
  "service.baby_chair": "宝宝椅",
  "service.smoke_free": "无烟餐厅",
  "service.open_kitchen": "明厨亮灶",
  "service.parking": "停车",
  "service.private_room": "包间",
  "need.transport": "交通条件",
  "occasion.list": "适用场景",
};

function displayValue(value: ProfileValue): string {
  if (Array.isArray(value)) return value.join("、");
  if (typeof value === "boolean") return value ? "有" : "无";
  return String(value);
}

function editValue(original: ProfileValue, next: string): ProfileValue {
  return Array.isArray(original)
    ? next.split(/[、,，]/).map((item) => item.trim()).filter(Boolean)
    : next;
}

export function ProfileEditor({
  initialProfile,
  merchantId,
}: {
  initialProfile: MerchantProfileData;
  merchantId: string;
}) {
  const router = useRouter();
  const [facts, setFacts] = useState(initialProfile.facts);
  const [rawText, setRawText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const confirmed = new Set(
    facts.filter((fact) => fact.confirmation_status === "confirmed").map((fact) => fact.field_key),
  );
  const ready = confirmed.has("location.city") && confirmed.has("category.precise");

  function updateFact(index: number, patch: Partial<MerchantProfileFactData>) {
    setFacts((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  async function parse() {
    setBusy(true);
    setError("");
    try {
      const parsed = await parseMerchantProfile(
        merchantId,
        rawText,
        sourceUrl.trim() ? [sourceUrl.trim()] : [],
      );
      const parsedKeys = new Set(parsed.facts.map((fact) => fact.field_key));
      setFacts([...facts.filter((fact) => !parsedKeys.has(fact.field_key)), ...parsed.facts]);
      setMessage("已识别候选资料，请逐项确认。未确认内容不会用于生成问题。");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "资料识别失败。");
    } finally {
      setBusy(false);
    }
  }

  async function saveAndGenerate() {
    setBusy(true);
    setError("");
    try {
      await replaceMerchantProfile(merchantId, facts);
      await generateQuerySet(merchantId, 12);
      router.push(`/queries?merchant=${merchantId}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败，请稍后重试。");
      setBusy(false);
    }
  }

  return (
    <div className="profile-editor">
      <section className="profile-import">
        <div className="section-heading"><div><p className="kicker">SOURCE TEXT</p><h2>导入公开资料</h2></div></div>
        <label>粘贴商家公开资料<textarea aria-label="粘贴商家公开资料" rows={6} value={rawText} onChange={(event) => setRawText(event.target.value)} /></label>
        <label>资料来源链接（可选）<input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://" /></label>
        <button className="button secondary" disabled={busy || rawText.trim().length < 10} onClick={parse} type="button">识别资料</button>
        {message && <p className="save-saved" role="status">{message}</p>}
      </section>

      <section className="profile-facts">
        <div className="section-heading"><div><p className="kicker">CONFIRMATION</p><h2>确认商家画像</h2></div></div>
        <div className="profile-fact-list">
          {facts.map((fact, index) => {
            const label = labels[fact.field_key] ?? fact.field_key;
            return (
              <div className="profile-fact-row" key={fact.field_key}>
                <label className="fact-confirm">
                  <input
                    aria-label={`确认 ${label}`}
                    checked={fact.confirmation_status === "confirmed"}
                    onChange={(event) => updateFact(index, { confirmation_status: event.target.checked ? "confirmed" : "pending" })}
                    type="checkbox"
                  />
                  <span>{label}</span>
                </label>
                <input
                  aria-label={`编辑 ${label}`}
                  value={displayValue(fact.value)}
                  onChange={(event) => updateFact(index, { value: editValue(fact.value, event.target.value) })}
                />
                <small>{fact.confirmation_status === "confirmed" ? "已确认" : "待确认"}</small>
              </div>
            );
          })}
        </div>
        {!ready && <p className="method-copy">至少确认“城市”和“精准品类”后才能生成问题。</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-actions">
          <button className="button primary" disabled={!ready || busy} onClick={saveAndGenerate} type="button">{busy ? "处理中…" : "保存并生成精准问题"}</button>
        </div>
      </section>
    </div>
  );
}
