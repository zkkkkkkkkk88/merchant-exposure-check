"use client";

import { useRouter } from "next/navigation";

import { createMerchant } from "@/lib/api";
import { MerchantForm } from "./merchant-form";

export function MerchantCreatePanel() {
  const router = useRouter();
  return <MerchantForm onSubmit={async (payload) => {
    const merchant = await createMerchant(payload);
    router.push(`/merchants/${merchant.id}`);
  }} />;
}
