"use client";

import { useEffect, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function MobileMerchantLabel({ merchantId }: { merchantId: string | null }) {
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    if (!merchantId) {
      setName(null);
      return;
    }
    const controller = new AbortController();
    setName(null);
    fetch(`${API_BASE_URL}/merchants/${encodeURIComponent(merchantId)}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`merchant ${response.status}`);
        return response.json() as Promise<{ name?: string }>;
      })
      .then((merchant) => setName(merchant.name || "当前商家"))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setName("当前商家");
      });
    return () => controller.abort();
  }, [merchantId]);

  return <span aria-label="当前商家" className="mobile-merchant-label">{name ?? "当前商家"}</span>;
}
