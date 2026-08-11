import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { ProfileEditor } from "@/components/profile-editor";
import { getMerchant, getMerchantProfile } from "@/lib/api";

export default async function MerchantPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [merchant, profile] = await Promise.all([getMerchant(id), getMerchantProfile(id)]);
  if (!merchant) return <AppShell><div className="state-page"><h1>商家不存在</h1><Link href="/merchants">返回商家列表</Link></div></AppShell>;
  if (!profile) return <AppShell><div className="state-page"><h1>无法读取商家画像</h1></div></AppShell>;
  return (
    <AppShell>
      <div className="workspace-page">
        <header className="page-header">
          <div><p className="kicker">MERCHANT PROFILE</p><h1>{merchant.name}</h1><p>{merchant.branch_name ?? "全部门店"} · {merchant.industry}</p></div>
          <Link className="button primary" href={`/queries?merchant=${id}`}>查看并审核问题</Link>
        </header>
        <ProfileEditor initialProfile={profile} merchantId={id} />
      </div>
    </AppShell>
  );
}
