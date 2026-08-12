import type { DashboardData } from "@/lib/contracts";
import Link from "next/link";
import { StatusBadge } from "./status-badge";

export function ActionList({ actions, merchantId }: Pick<DashboardData, "actions"> & { merchantId: string }) {
  const preview = actions.slice(0, 3);
  return (
    <aside className="actions-section" aria-labelledby="actions-title">
      <div className="section-heading"><div><p className="kicker">NEXT MOVES</p><h2 id="actions-title">优先行动</h2></div><span className="action-count">{actions.length}</span></div>
      <ol className="action-list">{preview.map((item, index) => <li key={item.id}><span className="action-index">{String(index + 1).padStart(2, "0")}</span><div><StatusBadge priority={item.priority} /><h3>{item.title}</h3><p>第一步：{item.steps[0]}</p><p>{item.evidenceCount} 条证据支持</p></div></li>)}</ol>
      <Link className="text-link" href={`/actions?merchant=${encodeURIComponent(merchantId)}`}>查看完整行动方案 <span>→</span></Link>
    </aside>
  );
}
