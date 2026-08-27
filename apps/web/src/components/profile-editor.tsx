"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAccessRole } from "./access-role-provider";

import {
  parseProfileAction,
  saveProfileAction,
  saveProfileAndGenerateAction,
} from "@/app/merchants/[id]/actions";
import type { MerchantProfileData, MerchantProfileFactData, ProfileValue } from "@/lib/contracts";
import { profileFieldLabel } from "@/lib/profile-field-labels";

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

function ensureRequiredFacts(facts: MerchantProfileFactData[]): MerchantProfileFactData[] {
  if (facts.some((fact) => fact.field_key === "category.precise")) return facts;
  const legacyCategory = facts.find((fact) => fact.field_key === "category.legacy");
  return [
    ...facts,
    {
      field_key: "category.precise",
      value: legacyCategory?.value ?? "",
      confirmation_status: "pending",
      confidence: legacyCategory?.confidence ?? 0,
      source_urls: legacyCategory?.source_urls ?? [],
    },
  ];
}

export function ProfileEditor({
  initialProfile,
  merchantId,
}: {
  initialProfile: MerchantProfileData;
  merchantId: string;
}) {
  const router = useRouter();
  const role = useAccessRole();
  const [facts, setFacts] = useState(() => ensureRequiredFacts(initialProfile.facts));
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
      const result = await parseProfileAction(
        merchantId,
        rawText,
        sourceUrl.trim() ? [sourceUrl.trim()] : [],
      );
      if (!result.ok) throw new Error(result.error);
      const parsed = result.data;
      const parsedKeys = new Set(parsed.facts.map((fact) => fact.field_key));
      setFacts(ensureRequiredFacts([...facts.filter((fact) => !parsedKeys.has(fact.field_key)), ...parsed.facts]));
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
      const result = await saveProfileAndGenerateAction(merchantId, facts);
      if (!result.ok) throw new Error(result.error);
      router.push(`/queries?merchant=${merchantId}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败，请稍后重试。");
      setBusy(false);
    }
  }

  async function saveOnly() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await saveProfileAction(merchantId, facts);
      if (!result.ok) throw new Error(result.error);
      const saved = result.data;
      setFacts(ensureRequiredFacts(saved.facts));
      setMessage("商家画像已保存。");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="profile-editor">
      <section className="profile-facts-confirmed" aria-labelledby="confirmed-profile-title">
        <div className="section-heading"><div><p className="kicker">READ FIRST</p><h2 id="confirmed-profile-title">已确认商家资料</h2></div></div>
        <dl className="profile-fact-reading">
          {facts.map((fact) => <div key={fact.field_key}><dt>{profileFieldLabel(fact.field_key)}</dt><dd>{displayValue(fact.value) || "当前未录入"}</dd><small>{fact.confirmation_status === "confirmed" ? "已确认" : "待确认"}</small></div>)}
        </dl>
      </section>
      <section className={`profile-administration${role === "demo" ? " profile-administration-locked" : ""}`} aria-labelledby="profile-administration-title">
        <header className="section-heading"><div><p className="kicker">ADMINISTRATION</p><h2 id="profile-administration-title">管理员资料操作</h2><p className="profile-admin-note">{role === "demo" ? "演示模式仅可查看资料，管理员才能导入、编辑或保存。" : "导入公开资料并确认后，才会用于生成检测问题。"}</p></div></header>
      <section className="profile-import">
        <div className="section-heading"><div><p className="kicker">SOURCE TEXT</p><h2>导入公开资料</h2></div></div>
        <label>粘贴商家公开资料<textarea aria-label="粘贴商家公开资料" rows={6} value={rawText} onChange={(event) => setRawText(event.target.value)} /></label>
        <label>资料来源链接（可选）<input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://" /></label>
        <button className="button secondary" data-requires-admin="true" disabled={busy || rawText.trim().length < 10} onClick={parse} type="button">识别资料</button>
        {rawText.trim().length < 10 && <p className="method-copy">请先粘贴至少 10 个字的商家资料；来源链接可以不填。</p>}
        {message && <p className="save-saved" role="status">{message}</p>}
      </section>

      <section className="profile-facts">
        <div className="section-heading"><div><p className="kicker">CONFIRMATION</p><h2>确认商家画像</h2></div></div>
        <div className="profile-fact-list">
          {facts.map((fact, index) => {
            const label = profileFieldLabel(fact.field_key);
            return (
              <div className="profile-fact-row" key={fact.field_key}>
                <label className="fact-confirm">
                  <input
                    aria-label={`确认 ${label}`}
                    data-requires-admin="true"
                    checked={fact.confirmation_status === "confirmed"}
                    onChange={(event) => updateFact(index, { confirmation_status: event.target.checked ? "confirmed" : "pending" })}
                    type="checkbox"
                  />
                  <span>{label}</span>
                </label>
                <input
                  aria-label={`编辑 ${label}`}
                  data-requires-admin="true"
                  value={displayValue(fact.value)}
                  onChange={(event) => updateFact(index, { value: editValue(fact.value, event.target.value) })}
                />
                <small>{fact.confirmation_status === "confirmed" ? "已确认" : "待确认"}</small>
              </div>
            );
          })}
        </div>
        {!ready && <p className="method-copy">请确认城市和精准品类后再生成问题。</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-actions">
          <button className="button secondary" data-requires-admin="true" disabled={busy} onClick={saveOnly} type="button">仅保存修改</button>
          <button className="button primary" data-requires-admin="true" disabled={!ready || busy} onClick={saveAndGenerate} type="button">{busy ? "处理中…" : "保存并生成精准问题"}</button>
        </div>
      </section>
      </section>
    </div>
  );
}
