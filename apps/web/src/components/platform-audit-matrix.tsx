import type { PlatformAuditRunData, PlatformAuditStatus } from "@/lib/contracts";
import { adoptPlatformField } from "@/app/platform-audits/actions";

const labels: Record<PlatformAuditStatus, string> = {
  complete: "已检索到",
  incomplete: "信息不完整",
  conflict: "信息冲突",
  not_found: "未检索到",
  needs_review: "待人工核实",
};

const fieldLabels: Record<string, string> = {
  name: "正式名称",
  address: "地址",
  phone: "电话",
  opening_hours: "营业时间",
  products: "服务项目",
  credentials: "资质",
};

const hasValue = (value: unknown) => value !== null && value !== undefined && value !== "" && (!Array.isArray(value) || value.length > 0);
const displayValue = (value: unknown) => Array.isArray(value) ? value.join("、") : hasValue(value) ? String(value) : "当前未录入";
const sameValue = (left: unknown, right: unknown) => displayValue(left).replace(/\s/g, "") === displayValue(right).replace(/\s/g, "");

export function PlatformAuditMatrix({ merchantId, run }: { merchantId: string; run: PlatformAuditRunData }) {
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
        {run.platforms.map((item) => { const baseline = item.baseline_fields ?? {}; const evidenceUrl = item.evidence.find((evidence) => evidence.url)?.url; const canAdoptResult = ["completed", "partial"].includes(run.status) && ["complete", "incomplete"].includes(item.status) && Boolean(evidenceUrl); const changedFields = Object.keys(fieldLabels).filter((key) => hasValue(item.fields[key]) && !sameValue(baseline[key], item.fields[key])); return <details key={item.id} className={`platform-audit-row audit-${item.status}`}>
          <summary><strong>{item.platform_name}</strong><span>{item.found && item.status !== "complete" ? `已检索到 · ${labels[item.status]}` : labels[item.status]}</span><small>{item.issues.join("；") || "已与商家资料核对"}</small></summary>
          <div className="platform-audit-detail">
            <dl className="audit-evidence-meta"><div><dt>本次搜索词</dt><dd>{item.search_query || "本轮未保存搜索词"}</dd></div><div><dt>命中对象</dt><dd>{hasValue(item.fields.name) ? `命中名称：${displayValue(item.fields.name)}` : "没有可确认的命中名称"}</dd></div><div><dt>检索时间</dt><dd>{new Date(item.checked_at).toLocaleString("zh-CN")}</dd></div></dl>
            {item.evidence.length > 0 ? <ul>{item.evidence.map((evidence, index) => <li key={`${evidence.url}-${index}`}>{evidence.url ? <a href={evidence.url} rel="noreferrer" target="_blank">{evidence.title || evidence.url}</a> : evidence.title}</li>)}</ul> : <p>本轮没有可展示的公开链接，需要人工复核或稍后重试。</p>}
            {changedFields.length > 0 && <div className="audit-field-diffs">{changedFields.map((key) => <article key={key}><div><span>{fieldLabels[key]}</span><small>当前资料</small><p>{displayValue(baseline[key])}</p></div><div><small>{item.platform_name}发现</small><p>{displayValue(item.fields[key])}</p></div>{canAdoptResult ? <form action={adoptPlatformField}><input name="merchantId" type="hidden" value={merchantId} /><input name="resultId" type="hidden" value={item.id} /><input name="fieldKey" type="hidden" value={key} /><button className="button secondary" type="submit">采用{fieldLabels[key]}</button></form> : <small className="adoption-blocked">{item.status === "conflict" ? "信息冲突，需先人工核实" : !evidenceUrl ? "缺少公开来源，暂不能采用" : "任务完成后可采用"}</small>}</article>)}</div>}
          </div>
        </details>; })}
      </div>
    </section>
  </>;
}
