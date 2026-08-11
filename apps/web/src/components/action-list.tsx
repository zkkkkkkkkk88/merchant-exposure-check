import Link from "next/link";
import type { DashboardData } from "@/lib/contracts";
import { StatusBadge } from "./status-badge";

export function ActionList({ actions }: Pick<DashboardData, "actions">) {
  return (
    <aside className="actions-section" aria-labelledby="actions-title">
      <div className="section-heading"><div><p className="kicker">NEXT MOVES</p><h2 id="actions-title">高优先级行动</h2></div><span className="action-count">{actions.filter((item) => item.priority === "high").length}</span></div>
      <ol className="action-list">{actions.map((item, index) => <li key={item.id}><span className="action-index">{String(index + 1).padStart(2, "0")}</span><div><StatusBadge priority={item.priority} /><h3>{item.title}</h3><p>{item.evidenceCount} 条证据支持</p></div></li>)}</ol>
      <Link className="text-link" href="/reports">查看全部建议 <span>→</span></Link>
    </aside>
  );
}
