"use server";

import { ApiError, createScanRun, updateQuery } from "@/lib/api";
import type { QueryData, ScanRunData } from "@/lib/contracts";

export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

export interface QueryActionChanges {
  text?: string;
  priority?: number;
  reviewStatus?: "pending" | "approved" | "rejected";
  isEnabled?: boolean;
}

export async function updateQueryAction(
  queryId: string,
  changes: QueryActionChanges,
): Promise<ActionResult<QueryData>> {
  try {
    const data = await updateQuery(queryId, {
      text: changes.text,
      priority: changes.priority,
      review_status: changes.reviewStatus,
      is_enabled: changes.isEnabled,
    });
    return { ok: true, data };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { ok: false, error: "这个问题已不存在，请刷新页面后重试。" };
    }
    return { ok: false, error: "保存失败，请稍后重试。" };
  }
}

export async function createScanAction(
  merchantId: string,
  querySetId: string,
): Promise<ActionResult<Pick<ScanRunData, "id" | "status">>> {
  try {
    const data = await createScanRun(merchantId, querySetId);
    return { ok: true, data: { id: data.id, status: data.status } };
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      return { ok: false, error: "当前没有已批准且启用的问题，请先审核问题库。" };
    }
    return { ok: false, error: "创建检测任务失败，请稍后重试。" };
  }
}
