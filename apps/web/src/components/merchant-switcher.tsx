"use client";

import { useRouter } from "next/navigation";

type MerchantOption = {
  id: string;
  name: string;
  branch_name: string | null;
};

export function MerchantSwitcher({
  merchants,
  merchantId,
}: {
  merchants: MerchantOption[];
  merchantId: string;
}) {
  const router = useRouter();

  return (
    <label className="merchant-switch">
      <span>切换商家</span>
      <select
        aria-label="切换商家"
        value={merchantId}
        onChange={(event) => router.push(`/?merchant=${encodeURIComponent(event.target.value)}`)}
      >
        {merchants.map((merchant) => (
          <option key={merchant.id} value={merchant.id}>
            {merchant.name}{merchant.branch_name ? ` · ${merchant.branch_name}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
