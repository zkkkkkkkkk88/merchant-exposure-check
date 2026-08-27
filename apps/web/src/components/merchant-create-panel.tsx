"use client";

import { useRouter } from "next/navigation";

import { createMerchantAction } from "@/app/server-actions";
import { MerchantForm } from "./merchant-form";

export function MerchantCreatePanel() {
  const router = useRouter();
  return <MerchantForm onSubmit={async (payload) => {
    const merchant = await createMerchantAction(payload);
    router.push(`/merchants/${merchant.id}`);
  }} />;
}
