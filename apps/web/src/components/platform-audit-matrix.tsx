import type { PlatformAuditRunData, PlatformAuditStatus } from "@/lib/contracts";

const labels: Record<PlatformAuditStatus, string> = {
  complete: "已检索到",
  incomplete: "信息不完整",
  conflict: "信息冲突",
  not_found: "未检索到",
  needs_review: "待人工核实",
};

export function PlatformAuditMatrix({ run }: { run: PlatformAuditRunData }) {
  const counts = run.platforms.reduce<Record<PlatformAuditStatus, number>>(
    (all, item) => ({ ...all, [item.status]: all[item.status] + 1 }),
    { complete: 0, incomplete: 0, conflict: 0, not_found: 0, needs_review: 0 },
  );
  return <>
    <section className="audit-summary" aria-label="平台查缺概览">
      {(Object.keys(labels) as PlatformAuditStatus[]).map((status) => <article key={status}><strong>{counts[status]}</strong><span>{labels[status]}</span></article>)}
    </section>
    <section className="workspace-card platform-audit-card">
      <header><div><p className="kicker">PUBLIC INFORMATION GAP</p><h2>渠道查缺矩阵</h2></div><span className={`run-status run-${run.status}`}>{run.status === "queued" ? "等待检索服务启动" : run.status === "running" ? "任务执行中" : "最近一轮"}</span></header>
      <p className="audit-disclaimer">只核实无需登录即可访问的公开页面。“未检索到”仅表示本轮没有找到可确认页面，不代表商家一定没有发布。</p>
      <div className="platform-audit-grid">
        {run.platforms.map((item) => <details key={item.id} className={`platform-audit-row audit-${item.status}`}>
          <summary><strong>{item.platform_name}</strong><span>{item.found && item.status !== "complete" ? `已检索到 · ${labels[item.status]}` : labels[item.status]}</span><small>{item.issues.join("；") || "已与商家资料核对"}</small></summary>
          <div className="platform-audit-detail">
            {item.evidence.length > 0 ? <ul>{item.evidence.map((evidence, index) => <li key={`${evidence.url}-${index}`}>{evidence.url ? <a href={evidence.url} rel="noreferrer" target="_blank">{evidence.title || evidence.url}</a> : evidence.title}</li>)}</ul> : <p>本轮没有可展示的公开链接，需要人工复核或稍后重试。</p>}
            <small>核实时间：{new Date(item.checked_at).toLocaleString("zh-CN")}</small>
          </div>
        </details>)}
      </div>
    </section>
  </>;
}
