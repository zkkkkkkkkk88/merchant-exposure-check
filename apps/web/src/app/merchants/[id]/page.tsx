import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { getMerchant } from "@/lib/api";

export default async function MerchantPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const merchant = await getMerchant(id);
  if (!merchant) return <AppShell><div className="state-page"><h1>商家不存在</h1><Link href="/merchants">返回商家列表</Link></div></AppShell>;
  const facts = [
    ["城市", merchant.city],
    ["区域", merchant.district],
    ["地址", merchant.address],
    ["价格", merchant.price_range],
    ["营业时间", merchant.opening_hours],
    ["代表产品", merchant.products.join("、") || null],
    ["公开优势", merchant.strengths.join("、") || null],
  ].filter((item): item is [string, string] => Boolean(item[1]));
  return (
    <AppShell>
      <div className="workspace-page">
        <header className="page-header">
          <div><p className="kicker">MERCHANT PROFILE</p><h1>{merchant.name}</h1><p>{merchant.branch_name ?? "全部门店"} · {merchant.industry}</p></div>
          <Link className="button primary" href={`/queries?merchant=${id}`}>查看并审核问题</Link>
        </header>
        <div className="profile-grid">
          <section>
            <h2>已确认资料</h2>
            {facts.length ? <dl className="fact-list">{facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl> : <p className="method-copy">尚未填写可确认的商家资料。</p>}
          </section>
          <section>
            <h2>公开来源</h2>
            {merchant.sources.length ? merchant.sources.map((source) => <a className="source-row" href={source.url} key={source.id}>{source.url}<span>{source.is_verified ? "已核验" : "待核验"}</span></a>) : <p className="method-copy">尚未记录公开来源。</p>}
            <p className="method-copy">页面只展示数据库中已保存的事实，不补写推测信息。</p>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
