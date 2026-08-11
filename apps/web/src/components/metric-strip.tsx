import type { DashboardData } from "@/lib/contracts";

const percent = (value: number) => `${Math.round(value * 100)}%`;

export function MetricStrip({ metrics }: Pick<DashboardData, "metrics">) {
  const items = [
    ["品牌出现率", percent(metrics.mentionRate), "有效回答中出现"],
    ["首位推荐率", percent(metrics.firstPositionRate), "明确排序回答中"],
    ["来源覆盖率", percent(metrics.sourceCoverageRate), "含可追溯来源"],
    ["有效问题", `${metrics.validQueryCount}/${metrics.totalQueryCount}`, "本次检测"],
  ];
  return (
    <section className="metric-strip" aria-label="核心指标">
      {items.map(([label, value, note]) => (
        <div className="metric" key={label}>
          <p>{label}</p><strong>{value}</strong><span>{note}</span>
        </div>
      ))}
    </section>
  );
}
