"use server";

import { createMerchant, getJourneyProgress } from "@/lib/api";
import { requireServerAdmin } from "@/lib/server-access";
import type { JourneyProgressData } from "@/lib/contracts";
import type { MerchantPayload } from "@/components/merchant-form";

export async function createMerchantAction(payload: MerchantPayload): Promise<{ id: string }> {
  await requireServerAdmin();
  return createMerchant(payload);
}

export async function getJourneyProgressAction(merchantId: string): Promise<JourneyProgressData | null> {
  return getJourneyProgress(merchantId);
}
