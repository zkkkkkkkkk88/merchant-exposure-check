import type { DashboardData } from "./contracts";
import type { MerchantPayload } from "@/components/merchant-form";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function getDashboard(merchantId: string): Promise<DashboardData | null> {
  const response = await fetch(
    `${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/dashboard`,
    { cache: "no-store" },
  );
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new ApiError(response.status, "暂时无法读取检测数据，请稍后再试。");
  }
  return response.json() as Promise<DashboardData>;
}

export async function createMerchant(payload: MerchantPayload): Promise<{ id: string }> {
  const response = await fetch(`${API_BASE_URL}/merchants`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new ApiError(response.status, "保存失败，请稍后重试");
  return response.json() as Promise<{ id: string }>;
}
