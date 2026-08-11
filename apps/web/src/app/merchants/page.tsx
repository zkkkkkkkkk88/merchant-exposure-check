import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { getMerchants } from "@/lib/api";

export default async function MerchantsPage() {
  const merchants = await getMerchants();
  return (
    <AppShell>
      <div className="workspace-page">
        <header className="page-header">
          <div>
            <p className="kicker">MERCHANT DIRECTORY</p>
            <h1>商家</h1>
            <p>集中维护用于检测的事实资料与公开来源。</p>
          </div>
          <Link className="button primary" href="/merchants/new">新建商家</Link>
        </header>
        {merchants.length === 0 ? (
          <div className="state-page">
            <h2>还没有商家资料</h2>
            <p>创建商家后，系统才会生成问题并执行真实检测。</p>
          </div>
        ) : (
          <div className="record-list">
            {merchants.map((merchant) => (
              <Link className="record-row" href={`/merchants/${merchant.id}`} key={merchant.id}>
                <div>
                  <strong>{merchant.name}</strong>
                  <span>{merchant.branch_name ?? "全部门店"}</span>
                </div>
                <span>查看已确认资料</span>
                <b>→</b>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
