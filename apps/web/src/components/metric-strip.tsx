import type { DashboardData } from "@/lib/contracts";

const percent = (value: number) => `${Math.round(value * 100)}%`;

export function MetricStrip({ metrics }: Pick<DashboardData, "metrics">) {
  const items = [
    ["可见性准备度", `${Math.round(metrics.readinessScore)}`, "综合得分 / 100"],
    ["商家画像完整度", percent(metrics.profileCompleteness), "已确认关键信息"],
    ["公开信息可验证度", percent(metrics.publicVerifiability), "可由来源交叉核验"],
    ["高意图问题命中", percent(metrics.highIntentHitRate), `${metrics.validQueryCount}/${metrics.totalQueryCount} 个有效问题`],
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
