"use client";

import { usePathname, useRouter } from "next/navigation";

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
  const pathname = usePathname();

  return (
    <label className="merchant-switch">
      <span>切换商家</span>
      <select
        aria-label="切换商家"
        value={merchantId}
        onChange={(event) => router.push(`${pathname}?merchant=${encodeURIComponent(event.target.value)}`)}
      >
        {!merchantId && <option value="">请选择商家</option>}
        {merchants.map((merchant) => (
          <option key={merchant.id} value={merchant.id}>
            {merchant.name}{merchant.branch_name ? ` · ${merchant.branch_name}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
