import type { DashboardData } from "@/lib/contracts";

const stages = [
  ["unrecognized", "未识别"],
  ["relevant", "信息相关"],
  ["mentioned", "被提及"],
  ["recommended", "进入推荐"],
] as const;

export function VisibilityStage({ stage }: { stage: DashboardData["metrics"]["visibilityStage"] }) {
  const current = stages.findIndex(([key]) => key === stage);
  return <section className="visibility-stage" aria-label="可见性成长阶段"><div><p className="kicker">VISIBILITY LADDER</p><h2>当前阶段 · {stages[current][1]}</h2></div><ol>{stages.map(([key, label], index) => <li className={index <= current ? "reached" : ""} aria-current={key === stage ? "step" : undefined} key={key}><span>{String(index + 1).padStart(2, "0")}</span>{label}</li>)}</ol></section>;
}
