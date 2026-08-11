import Link from "next/link";
import { AppShell } from "@/components/app-shell";

const merchants = [{ id: "demo", name: "O'eat Gastronomy", branch: "杭州万象城店", city: "杭州", industry: "餐饮", completeness: 6 }];
export default function MerchantsPage() {
  return <AppShell><div className="workspace-page"><header className="page-header"><div><p className="kicker">MERCHANT DIRECTORY</p><h1>商家</h1><p>集中维护用于检测的事实资料与公开来源。</p></div><Link className="button primary" href="/merchants/new">新建商家</Link></header><div className="record-list">{merchants.map((merchant) => <Link className="record-row" href={`/merchants/${merchant.id}`} key={merchant.id}><div><strong>{merchant.name}</strong><span>{merchant.branch}</span></div><span>{merchant.city} · {merchant.industry}</span><span>资料 {merchant.completeness}/8</span><b>→</b></Link>)}</div></div></AppShell>;
}
