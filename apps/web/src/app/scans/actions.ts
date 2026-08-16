"use server";

import { redirect } from "next/navigation";

import { retryScanRun } from "@/lib/api";

export async function retryScanAction(formData: FormData): Promise<void> {
  const scanRunId = String(formData.get("scanRunId") ?? "");
  const merchantId = String(formData.get("merchantId") ?? "");
  if (!scanRunId || !merchantId) return;
  const run = await retryScanRun(scanRunId);
  redirect(`/scans/${encodeURIComponent(run.id)}?merchant=${encodeURIComponent(merchantId)}`);
}
