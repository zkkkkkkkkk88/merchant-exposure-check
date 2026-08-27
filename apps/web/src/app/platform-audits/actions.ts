"use server";

import { redirect } from "next/navigation";
import { requireServerAdmin, trustedApiHeaders } from "@/lib/server-access";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function createPlatformAudit(formData: FormData): Promise<void> {
  await requireServerAdmin();
  const merchantId = String(formData.get("merchantId") ?? "");
  const response = await fetch(
    `${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/platform-audits`,
    { method: "POST", headers: await trustedApiHeaders() },
  );
  if (!response.ok) throw new Error("创建平台查缺任务失败");
  redirect(`/platform-audits?merchant=${encodeURIComponent(merchantId)}`);
}

export async function adoptPlatformField(formData: FormData): Promise<void> {
  await requireServerAdmin();
  const merchantId = String(formData.get("merchantId") ?? "");
  const resultId = String(formData.get("resultId") ?? "");
  const fieldKey = String(formData.get("fieldKey") ?? "");
  const response = await fetch(
    `${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/platform-audits/results/${encodeURIComponent(resultId)}/adopt`,
    {
      method: "POST",
      headers: await trustedApiHeaders({ "content-type": "application/json" }),
      body: JSON.stringify({ field_key: fieldKey }),
    },
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail || "采用平台资料失败");
  }
  redirect(`/platform-audits?merchant=${encodeURIComponent(merchantId)}`);
}
