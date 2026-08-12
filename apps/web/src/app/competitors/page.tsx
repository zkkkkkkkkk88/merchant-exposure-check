import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { getDashboard } from "@/lib/api";

export default async function CompetitorsPage({ searchParams = Promise.resolve({}) }: { searchParams?: Promise<{ merchant?: string }> }) {
  const merchantId = (await searchParams).merchant;
  const data = merchantId ? await getDashboard(merchantId) : null;
  if (!merchantId || !data) return <AppShell><div className="state-page"><h1>暂无同类参照</h1><p>请先选择商家并完成一次真实检测。</p><Link className="text-link" href="/">返回总览</Link></div></AppShell>;
  return <AppShell><div className="workspace-page wide-page"><header className="page-header"><div><p className="kicker">COMPARISON SET</p><h1>同类参照</h1><p>{data.merchant.name} · 来自最近一次真实检测</p></div><Link className="button secondary" href={`/?merchant=${merchantId}`}>返回总览</Link></header>{data.competitors.length ? <div className="insight-grid">{data.competitors.map((item) => <article className="competitor-card" key={item.name}><div className="card-meta"><span>{item.comparisonLevel === "core" ? "核心参照" : "候选参照"}</span><b>{item.mentions} 个问题提及</b></div><h2>{item.name}</h2><p className="context-line">{item.contexts.join(" / ")} · {item.sourceCount ? `${item.sourceCount} 个已识别来源` : "来源待核验"}</p><details><summary>查看问题与推荐依据</summary><h3>被提及的问题</h3><ul>{item.questions.map((question) => <li key={question}>{question}</li>)}</ul><h3>回答中的推荐依据</h3>{item.reasons.length ? <ul>{item.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul> : <p>当前回答没有提供可结构化的推荐依据。</p>}</details></article>)}</div> : <div className="state-page"><h2>本次没有形成可用参照</h2><p>当前真实回答没有识别到同类商家，建议扩大问题类型后再次检测。</p></div>}</div></AppShell>;
}
