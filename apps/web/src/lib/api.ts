import type {
  DashboardData,
  HistoryData,
  MerchantData,
  QueryData,
  QuerySetData,
  QueryUpdateData,
  ReportData,
  ScanRunData,
} from "./contracts";
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

export async function getMerchants(): Promise<Array<{ id: string; name: string; branch_name: string | null }>> {
  const response = await fetch(`${API_BASE_URL}/merchants`, { cache: "no-store" });
  if (!response.ok) throw new ApiError(response.status, "暂时无法读取商家列表。");
  return response.json() as Promise<Array<{ id: string; name: string; branch_name: string | null }>>;
}

async function readJson<T>(path: string, notFoundMessage: string): Promise<T | null> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new ApiError(response.status, notFoundMessage);
  return response.json() as Promise<T>;
}

export function getMerchant(merchantId: string): Promise<MerchantData | null> {
  return readJson<MerchantData>(
    `/merchants/${encodeURIComponent(merchantId)}`,
    "暂时无法读取商家资料。",
  );
}

export async function getQuerySets(merchantId: string): Promise<QuerySetData[]> {
  const data = await readJson<QuerySetData[]>(
    `/merchants/${encodeURIComponent(merchantId)}/query-sets`,
    "暂时无法读取问题库。",
  );
  return data ?? [];
}

export async function getScanRuns(merchantId: string): Promise<ScanRunData[]> {
  const data = await readJson<ScanRunData[]>(
    `/scan-runs/merchant/${encodeURIComponent(merchantId)}/runs`,
    "暂时无法读取检测记录。",
  );
  return data ?? [];
}

export async function updateQuery(
  queryId: string,
  payload: QueryUpdateData,
): Promise<QueryData> {
  const response = await fetch(`${API_BASE_URL}/queries/${encodeURIComponent(queryId)}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, "保存问题失败，请稍后重试。");
  return response.json() as Promise<QueryData>;
}

export async function createScanRun(
  merchantId: string,
  querySetId: string,
): Promise<ScanRunData> {
  const response = await fetch(`${API_BASE_URL}/scan-runs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      merchant_id: merchantId,
      query_set_id: querySetId,
      adapter_name: "ark",
    }),
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, "创建检测任务失败，请稍后重试。");
  return response.json() as Promise<ScanRunData>;
}

export function getScanRun(scanRunId: string): Promise<ScanRunData | null> {
  return readJson<ScanRunData>(
    `/scan-runs/${encodeURIComponent(scanRunId)}`,
    "暂时无法读取检测详情。",
  );
}

export function getReport(merchantId: string, scanRunId: string): Promise<ReportData | null> {
  return readJson<ReportData>(
    `/merchants/${encodeURIComponent(merchantId)}/reports/${encodeURIComponent(scanRunId)}`,
    "暂时无法读取分析报告。",
  );
}

export function getHistory(
  merchantId: string,
  leftScanId: string,
  rightScanId: string,
): Promise<HistoryData | null> {
  const query = new URLSearchParams({ left: leftScanId, right: rightScanId });
  return readJson<HistoryData>(
    `/merchants/${encodeURIComponent(merchantId)}/history?${query.toString()}`,
    "暂时无法读取历史对比。",
  );
}
