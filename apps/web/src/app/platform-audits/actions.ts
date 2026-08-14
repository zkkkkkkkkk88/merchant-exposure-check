"use server";

import { redirect } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function createPlatformAudit(formData: FormData): Promise<void> {
  const merchantId = String(formData.get("merchantId") ?? "");
  const response = await fetch(
    `${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/platform-audits`,
    { method: "POST" },
  );
  if (!response.ok) throw new Error("创建平台查缺任务失败");
  redirect(`/platform-audits?merchant=${encodeURIComponent(merchantId)}`);
}
