type Deltas = { readinessScore: number; profileCompleteness: number; publicVerifiability: number; highIntentHitRate: number; competitorGapClosure: number };

export function HistoryComparison({ leftLabel, rightLabel, deltas }: { leftLabel: string; rightLabel: string; deltas: Deltas }) {
  const rows = [["可见性准备度", deltas.readinessScore, false], ["商家画像完整度", deltas.profileCompleteness, true], ["公开信息可验证度", deltas.publicVerifiability, true], ["高意图问题命中", deltas.highIntentHitRate, true], ["竞品差距收窄", deltas.competitorGapClosure, true]] as const;
  const format = (value: number, ratio: boolean) => `${value >= 0 ? "+" : ""}${Math.round(value * (ratio ? 100 : 1))}${ratio ? " 个百分点" : " 分"}`;
  return <section className="history-comparison" aria-labelledby="history-title"><div className="section-heading"><div><p className="kicker">PERIOD COMPARISON</p><h2 id="history-title">成长指标变化</h2></div></div><div className="comparison-head"><span>{leftLabel}</span><span>→</span><span>{rightLabel}</span></div><dl>{rows.map(([label, value, ratio]) => <div key={label}><dt>{label}</dt><dd className={value >= 0 ? "delta-up" : "delta-down"}>{format(value, ratio)}</dd></div>)}</dl><p className="method-copy">差值只描述两次真实检测之间的变化，不推断平台内部排序。</p></section>;
}
