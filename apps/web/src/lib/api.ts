import type {
  DashboardData,
  HistoryData,
  MerchantData,
  MerchantProfileData,
  MerchantProfileFactData,
  QueryData,
  QuerySetData,
  QueryUpdateData,
  ReportData,
  ScanRunData,
  MobileValidationSetData,
  MobileWorkspaceData,
  PlatformAuditRunData,
  JourneyProgressData,
  MobileSourceDiscoveryData,
  MobileSourceDiscoveryPayload,
} from "./contracts";
import type { MerchantPayload } from "@/components/merchant-form";
import { trustedApiHeaders } from "./server-access";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

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
    { cache: "no-store", headers: await trustedApiHeaders() },
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
    headers: await trustedApiHeaders({ "content-type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new ApiError(response.status, "保存失败，请稍后重试");
  return response.json() as Promise<{ id: string }>;
}

export async function getMerchants(): Promise<Array<{ id: string; name: string; branch_name: string | null }>> {
  const response = await fetch(`${API_BASE_URL}/merchants`, { cache: "no-store", headers: await trustedApiHeaders() });
  if (!response.ok) throw new ApiError(response.status, "暂时无法读取商家列表。");
  return response.json() as Promise<Array<{ id: string; name: string; branch_name: string | null }>>;
}

async function readJson<T>(path: string, notFoundMessage: string): Promise<T | null> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store", headers: await trustedApiHeaders() });
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

export function getMerchantProfile(merchantId: string): Promise<MerchantProfileData | null> {
  return readJson<MerchantProfileData>(
    `/merchants/${encodeURIComponent(merchantId)}/profile`,
    "暂时无法读取商家画像。",
  );
}

export async function parseMerchantProfile(
  merchantId: string,
  rawText: string,
  sourceUrls: string[] = [],
): Promise<MerchantProfileData> {
  const response = await fetch(`${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/profile/parse`, {
    method: "POST",
    headers: await trustedApiHeaders({ "content-type": "application/json" }),
    body: JSON.stringify({ raw_text: rawText, source_urls: sourceUrls }),
  });
  if (!response.ok) throw new ApiError(response.status, "资料识别失败，请检查内容后重试。");
  return response.json() as Promise<MerchantProfileData>;
}

export async function replaceMerchantProfile(
  merchantId: string,
  facts: MerchantProfileFactData[],
): Promise<MerchantProfileData> {
  const response = await fetch(`${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/profile`, {
    method: "PUT",
    headers: await trustedApiHeaders({ "content-type": "application/json" }),
    body: JSON.stringify({ facts }),
  });
  if (!response.ok) throw new ApiError(response.status, "保存商家画像失败，请稍后重试。");
  return response.json() as Promise<MerchantProfileData>;
}

export async function generateQuerySet(
  merchantId: string,
  count = 15,
): Promise<{ id: string }> {
  const response = await fetch(`${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/query-sets/generate`, {
    method: "POST",
    headers: await trustedApiHeaders({ "content-type": "application/json" }),
    body: JSON.stringify({ count }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({})) as { detail?: string };
    throw new ApiError(response.status, detail.detail ?? "生成问题失败，请先确认必要资料。");
  }
  return response.json() as Promise<{ id: string }>;
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
    headers: await trustedApiHeaders({ "content-type": "application/json" }),
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
    headers: await trustedApiHeaders({ "content-type": "application/json" }),
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

export async function retryScanRun(scanRunId: string): Promise<ScanRunData> {
  const response = await fetch(
    `${API_BASE_URL}/scan-runs/${encodeURIComponent(scanRunId)}/retry`,
    { method: "POST", headers: await trustedApiHeaders(), cache: "no-store" },
  );
  if (!response.ok) {
    const detail = await response.json().catch(() => ({})) as { detail?: string };
    throw new ApiError(response.status, detail.detail ?? "重新执行检测失败，请稍后再试。");
  }
  return response.json() as Promise<ScanRunData>;
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

export async function getMobileValidationSets(merchantId: string): Promise<MobileValidationSetData[]> {
  const data = await readJson<MobileValidationSetData[]>(`/merchants/${encodeURIComponent(merchantId)}/mobile-validation-sets`, "暂时无法读取手机验证题集。");
  return data ?? [];
}

export function getMobileWorkspace(merchantId: string): Promise<MobileWorkspaceData | null> {
  return readJson<MobileWorkspaceData>(`/merchants/${encodeURIComponent(merchantId)}/mobile-checks/workspace`, "暂时无法读取手机版豆包实测。");
}

export async function discoverMobileSources(
  merchantId: string,
  payload: MobileSourceDiscoveryPayload,
): Promise<MobileSourceDiscoveryData> {
  const response = await fetch(
    `${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/mobile-checks/discover-sources`,
    {
      method: "POST",
      headers: await trustedApiHeaders({ "content-type": "application/json" }),
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) {
    const detail = await response.json().catch(() => ({})) as { detail?: string };
    throw new ApiError(response.status, detail.detail ?? "自动查找公开来源失败，请稍后重试。");
  }
  return response.json() as Promise<MobileSourceDiscoveryData>;
}

export function getLatestPlatformAudit(merchantId: string): Promise<PlatformAuditRunData | null> {
  return readJson<PlatformAuditRunData>(
    `/merchants/${encodeURIComponent(merchantId)}/platform-audits/latest`,
    "暂时无法读取平台查缺结果。",
  );
}

export function getJourneyProgress(merchantId: string): Promise<JourneyProgressData | null> {
  return readJson<JourneyProgressData>(
    `/merchants/${encodeURIComponent(merchantId)}/journey-progress`,
    "暂时无法读取商家进度。",
  );
}

export async function selectMobileValidationSet(merchantId: string, queryIds: string[]): Promise<MobileValidationSetData> {
  const response = await fetch(`${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}/mobile-validation-sets/select`, {
    method: "POST",
    headers: await trustedApiHeaders({ "content-type": "application/json" }),
    body: JSON.stringify({ query_ids: queryIds }),
  });
  if (!response.ok) throw new ApiError(response.status, "保存本轮3题失败，请确认恰好选择3道已审核的推荐题。");
  return response.json() as Promise<MobileValidationSetData>;
}
