import type { DashboardData } from "@/lib/contracts";

export function CategoryCoverage({ categories }: Pick<DashboardData, "categories">) {
  return (
    <section className="category-section" aria-labelledby="category-title">
      <div className="section-heading"><div><p className="kicker">QUERY COVERAGE</p><h2 id="category-title">问题类型覆盖</h2></div></div>
      <div className="coverage-list">{categories.map((item) => <div className="coverage-row" key={item.name}><span>{item.name}</span><div className="coverage-track"><i style={{ width: `${item.rate * 100}%` }} /></div><strong>{Math.round(item.rate * 100)}%</strong><small>{item.mentioned}/{item.total}</small></div>)}</div>
    </section>
  );
}
