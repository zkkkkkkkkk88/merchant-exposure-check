import type { DashboardData } from "@/lib/contracts";

export function CompetitorTable({ competitors }: Pick<DashboardData, "competitors">) {
  return (
    <section className="competitor-section" aria-labelledby="competitor-title">
      <div className="section-heading"><div><p className="kicker">COMPARISON SET</p><h2 id="competitor-title">同类参照</h2></div></div>
      <div className="table-wrap"><table aria-label="同类商家对比"><thead><tr><th>商家</th><th>被提及</th><th>可追溯来源</th></tr></thead><tbody>{competitors.map((item) => <tr key={item.name}><th>{item.name}</th><td>{item.mentions}</td><td>{item.sourceCount}</td></tr>)}</tbody></table></div>
    </section>
  );
}
