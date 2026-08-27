import type { MobileWorkspaceData } from "@/lib/contracts";

export function SourceGapTable({ data }: { data: MobileWorkspaceData }) {
  if (!data.sourceGaps.length) {
    return <div className="empty-panel">
      <p>本轮还没有录入来源审计，因此不显示“未发现”矩阵。</p>
      <p>给少量代表性来源即可，例如：工商登记、机构介绍、招聘页或抖音公开内容。</p>
    </div>;
  }
  return <div className="source-gap-wrap">
    <table className="source-gap-table responsive-record-table"><thead><tr><th scope="col">来源或事实</th>{data.entities.map((entity) => <th key={entity} scope="col">{entity}</th>)}</tr></thead><tbody>{data.sourceGaps.map((row) => <tr className={row.highlight ? "source-gap-highlight" : ""} key={row.key}><th data-primary="true" scope="row">{row.label}{row.highlight && <small>目标商家明显缺口</small>}</th>{data.entities.map((entity) => { const cell = row.cells[entity]; return <td data-label={entity} key={entity}>{cell?.status === "present" ? <><strong>有</strong>{cell.evidence.map((evidence) => <span key={evidence}>{evidence}</span>)}</> : cell?.status === "needs_review" ? <em>待核对</em> : <em>本轮来源未发现</em>}</td>; })}</tr>)}</tbody></table>
    <p className="method-note">只展示最多3家竞品和5条有代表性的来源差距。“未发现”仅表示本轮已确认来源中没有出现。</p>
  </div>;
}
