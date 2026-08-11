import type { DashboardData } from "@/lib/contracts";

const point = (value: number, index: number, count: number) =>
  `${(index / Math.max(count - 1, 1)) * 100},${92 - value * 78}`;

export function ExposureTrend({ trend }: Pick<DashboardData, "trend">) {
  const target = trend.map((item, index) => point(item.target, index, trend.length)).join(" ");
  const benchmark = trend.map((item, index) => point(item.benchmark, index, trend.length)).join(" ");
  return (
    <section className="trend-section" aria-labelledby="trend-title">
      <div className="section-heading"><div><p className="kicker">READINESS OVER TIME</p><h2 id="trend-title">可见性准备度趋势</h2></div><div className="legend"><span className="target-key">本店</span><span className="benchmark-key">同类参考</span></div></div>
      <div className="chart-frame">
        <svg viewBox="0 0 100 100" role="img" aria-label="可见性准备度趋势折线图" preserveAspectRatio="none">
          <line x1="0" y1="25" x2="100" y2="25" /><line x1="0" y1="55" x2="100" y2="55" /><line x1="0" y1="85" x2="100" y2="85" />
          <polyline className="benchmark-line" points={benchmark} /><polyline className="target-line" points={target} />
        </svg>
        <div className="chart-labels">{trend.map((item) => <span key={item.label}>{item.label}<b>{Math.round(item.target * 100)}％</b></span>)}</div>
      </div>
    </section>
  );
}
