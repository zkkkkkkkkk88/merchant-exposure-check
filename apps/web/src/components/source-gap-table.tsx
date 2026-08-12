import type { MobileWorkspaceData } from "@/lib/contracts";

export function SourceGapTable({ data }: { data: MobileWorkspaceData }) {
  if (!data.sourceGaps.length) return <div className="empty-panel"><p>确认一轮手机实测来源后，这里会生成对比。</p></div>;
  return <div className="source-gap-wrap"><table className="source-gap-table"><thead><tr><th>来源或事实</th>{data.entities.map((entity) => <th key={entity}>{entity}</th>)}</tr></thead><tbody>{data.sourceGaps.map((row) => <tr className={row.highlight ? "source-gap-highlight" : ""} key={row.key}><th>{row.label}{row.highlight && <small>目标商家明显缺口</small>}</th>{data.entities.map((entity) => { const cell = row.cells[entity]; return <td key={entity}>{cell?.status === "present" ? <><strong>有</strong>{cell.evidence.map((evidence) => <span key={evidence}>{evidence}</span>)}</> : cell?.status === "needs_review" ? <em>待核对</em> : <em>当前手机实测未发现</em>}</td>; })}</tr>)}</tbody></table><p className="method-note">“未发现”仅表示本轮经确认的手机版豆包来源中没有出现，不代表互联网上绝对不存在。</p></div>;
}
