import type { DashboardData } from "@/lib/contracts";
import Link from "next/link";

export function CompetitorTable({ competitors, merchantId }: Pick<DashboardData, "competitors"> & { merchantId: string }) {
  const preview = competitors.slice(0, 3);
  return (
    <section className="competitor-section" aria-labelledby="competitor-title">
      <div className="section-heading"><div><p className="kicker">COMPARISON SET</p><h2 id="competitor-title">同类参照</h2></div></div>
      <div className="table-wrap"><table aria-label="同类商家对比" className="responsive-record-table"><thead><tr><th scope="col">商家</th><th scope="col">适用场景</th><th scope="col">覆盖问题</th><th scope="col">参照级别</th><th scope="col">已确认来源</th></tr></thead><tbody>{preview.map((item) => <tr key={item.name}><th data-label="商家" data-primary="true" scope="row"><strong>{item.name}</strong></th><td data-label="适用场景">{item.contexts.join(" / ")}</td><td data-label="覆盖问题">{item.mentions}</td><td data-label="参照级别">{item.comparisonLevel === "core" ? "核心参照" : "候选参照"}</td><td data-label="已确认来源">{item.sourceCount || "待核验"}</td></tr>)}</tbody></table></div>
      <Link className="text-link" href={`/competitors?merchant=${encodeURIComponent(merchantId)}`}>查看全部同类参照 <span>→</span></Link>
    </section>
  );
}
