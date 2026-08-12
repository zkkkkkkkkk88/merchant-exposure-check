"use server";

import {
  ApiError,
  generateQuerySet,
  parseMerchantProfile,
  replaceMerchantProfile,
} from "@/lib/api";
import type { MerchantProfileData, MerchantProfileFactData } from "@/lib/contracts";

type ActionResult<T> = { ok: true; data: T } | { ok: false; error: string };

function actionError(error: unknown, fallback: string): { ok: false; error: string } {
  return { ok: false, error: error instanceof ApiError ? error.message : fallback };
}

export async function parseProfileAction(
  merchantId: string,
  rawText: string,
  sourceUrls: string[],
): Promise<ActionResult<MerchantProfileData>> {
  try {
    return { ok: true, data: await parseMerchantProfile(merchantId, rawText, sourceUrls) };
  } catch (error) {
    return actionError(error, "资料识别失败，请稍后重试。");
  }
}

export async function saveProfileAction(
  merchantId: string,
  facts: MerchantProfileFactData[],
): Promise<ActionResult<MerchantProfileData>> {
  try {
    return { ok: true, data: await replaceMerchantProfile(merchantId, facts) };
  } catch (error) {
    return actionError(error, "保存失败，请稍后重试。");
  }
}

export async function saveProfileAndGenerateAction(
  merchantId: string,
  facts: MerchantProfileFactData[],
): Promise<ActionResult<{ id: string }>> {
  try {
    await replaceMerchantProfile(merchantId, facts);
    return { ok: true, data: await generateQuerySet(merchantId, 12) };
  } catch (error) {
    return actionError(error, "保存或生成问题失败，请稍后重试。");
  }
}
