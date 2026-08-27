"use client";

import { FormEvent, useState } from "react";

export interface MerchantPayload {
  name: string;
  branch_name: string | null;
  city: string;
  district: string | null;
  industry: string;
  address: string | null;
  price_range: string | null;
  opening_hours: string | null;
  products: string[];
  strengths: string[];
  sources: Array<{ kind: string; url: string; is_verified: boolean }>;
}

export function MerchantForm({ onSubmit }: { onSubmit: (payload: MerchantPayload) => Promise<void> }) {
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const name = String(values.get("name") ?? "").trim();
    const city = String(values.get("city") ?? "").trim();
    const industry = String(values.get("industry") ?? "").trim();
    if (!name || !city || !industry) { setError("请填写商家名称、城市和行业"); return; }
    const source = String(values.get("source") ?? "").trim();
    if (source) {
      try { new URL(source); } catch { setError("请输入完整的公开来源网址"); return; }
    }
    const text = (key: string) => String(values.get(key) ?? "").trim() || null;
    const list = (key: string) => String(values.get(key) ?? "").split(/[,，\n]/).map((item) => item.trim()).filter(Boolean);
    setSaving(true); setError("");
    try {
      await onSubmit({ name, branch_name: text("branch_name"), city, district: text("district"), industry, address: text("address"), price_range: text("price_range"), opening_hours: text("opening_hours"), products: list("products"), strengths: list("strengths"), sources: source ? [{ kind: "other", url: source, is_verified: false }] : [] });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "保存失败，请稍后重试"); }
    finally { setSaving(false); }
  }

  return <form className="editorial-form" data-requires-admin="true" onSubmit={submit} noValidate>
    <div className="form-grid"><label>商家名称<input name="name" autoComplete="organization" /></label><label>门店名称<input name="branch_name" /></label><label>城市<input name="city" autoComplete="address-level1" /></label><label>商圈 / 区县<input name="district" /></label><label>行业<input name="industry" /></label><label>详细地址<input name="address" autoComplete="street-address" /></label><label>价格区间<input name="price_range" placeholder="如 ¥200–300 / 人" /></label><label>营业时间<input name="opening_hours" placeholder="如 11:30–22:00" /></label></div>
    <label className="wide-field">代表产品<textarea name="products" rows={2} placeholder="使用逗号分隔" /></label>
    <label className="wide-field">商家优势<textarea name="strengths" rows={2} placeholder="只填写可被公开信息核验的事实" /></label>
    <fieldset><legend>公开来源</legend><label>公开来源 1（选填）<input name="source" type="url" placeholder="https://" /></label><p>可填写官网、门店页或公开报道；美团等平台没有可复制链接时可以留空。</p></fieldset>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="form-actions"><button className="button primary" data-requires-admin="true" disabled={saving} type="submit">{saving ? "保存中…" : "保存并生成问题"}</button></div>
  </form>;
}
