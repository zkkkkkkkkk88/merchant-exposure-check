"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { pathWithMerchant, persistMerchantContext } from "@/lib/merchant-context";

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
  const searchParams = useSearchParams();

  return (
    <label className="merchant-switch">
      <span>切换商家</span>
      <select
        aria-label="切换商家"
        value={merchantId}
        onChange={(event) => {
          const merchantId = event.target.value;
          persistMerchantContext(merchantId);
          router.push(pathWithMerchant(pathname, searchParams?.toString() ?? "", merchantId));
        }}
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
