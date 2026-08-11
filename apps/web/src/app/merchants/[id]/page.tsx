import Link from "next/link";
import { AppShell } from "@/components/app-shell";

export default async function MerchantDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AppShell><div className="workspace-page"><header className="page-header"><div><p className="kicker">MERCHANT PROFILE</p><h1>O&apos;eat Gastronomy</h1><p>杭州万象城店 · 餐饮</p></div><Link className="button primary" href={`/queries?merchant=${id}`}>生成并审核问题</Link></header><div className="profile-grid"><section><h2>已确认资料</h2><dl className="fact-list"><div><dt>地址</dt><dd>杭州市上城区富春路 701 号</dd></div><div><dt>价格</dt><dd>¥300–500 / 人</dd></div><div><dt>营业时间</dt><dd>11:30–22:00</dd></div><div><dt>代表产品</dt><dd>季节套餐、手工甜点</dd></div></dl></section><section><h2>公开来源</h2><a className="source-row" href="https://example.com">门店公开页面 <span>已记录</span></a><p className="method-copy">资料完整度为已确认字段数，不是模型评分。</p></section></div></div></AppShell>;
}
