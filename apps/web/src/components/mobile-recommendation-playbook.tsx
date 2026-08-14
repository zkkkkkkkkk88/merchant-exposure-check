import type { MobileWorkspaceData } from "@/lib/contracts";

const percent = (value: number) => `${Math.round(value * 100)}%`;
const confidenceLabel = { confirmed: "来源已确认", answer_only: "来自豆包回答", needs_verification: "待商家核实" } as const;
const levelLabel = { none: "未提及", supplementary: "补充提及", primary: "首批推荐" } as const;

export function MobileRecommendationPlaybook({ data }: { data: MobileWorkspaceData["recommendationPlaybook"] }) {
  if (!data) return null;
  return <section className="workspace-card recommendation-playbook" id="improvement-playbook">
    <header><div><p className="kicker">IMPROVEMENT PLAYBOOK</p><h2>推荐率提升方案</h2></div><span>{data.actions.length} 项优先行动</span></header>

    <div className="playbook-diagnosis">
      <h3>这轮结果说明什么</h3>
      <p>{data.diagnosis.summary}</p>
      <div className="question-outcomes">{data.diagnosis.questions.map((question) => <article key={question.position}>
        <strong>Q{question.position} · {question.mentionLabel}{question.targetPosition ? ` · 第 ${question.targetPosition} 位` : ""}</strong>
        <span>{question.text}</span>
      </article>)}</div>
    </div>

    {data.competitorReasons.length > 0 && <div className="playbook-block">
      <h3>豆包为什么提到这些竞品</h3>
      <p className="section-note">只展示答案或已确认来源里实际出现的理由，不代表平台官方排序规则。</p>
      <div className="competitor-reason-grid">{data.competitorReasons.map((competitor) => <article key={competitor.name}>
        <h4>{competitor.name}</h4>
        <p className="competitor-frequency">在本轮 {data.diagnosis.totalCount} 道题中的 {competitor.questionCount} 道出现</p>
        <ul>{competitor.reasons.map((reason, index) => <li key={`${reason.text}-${index}`}><span>{reason.text}</span><em>{confidenceLabel[reason.confidence]}</em></li>)}</ul>
      </article>)}</div>
    </div>}

    <div className="playbook-block">
      <h3>商家现在具体做什么</h3>
      <div className="priority-action-list">{data.actions.map((action, index) => <article key={action.key}>
        <header><span>0{index + 1}</span><div><h4>{action.title}</h4><p>{action.why}</p></div><em>{confidenceLabel[action.confidence]}</em></header>
        <div className="priority-action-body"><div><h5>执行步骤</h5><ol>{action.steps.map((step) => <li key={step}>{step}</li>)}</ol></div><div><h5>需要准备</h5><ul>{action.materials.map((material) => <li key={material}>{material}</li>)}</ul></div></div>
        <div className="publish-targets"><h5>优先发布渠道</h5><ol>{action.publishTargets.map((target) => <li key={`${target.priority}-${target.channel}`}><span>{target.priority}</span><div><strong>{target.channel}</strong><p>{target.content}</p></div></li>)}</ol><p className="link-entry-hint">{action.linkEntryHint}</p></div>
        {action.examples.length > 0 && <p className="action-example"><strong>证据示例：</strong>{action.examples.join("；")}</p>}
        <p className="completion-criteria"><strong>完成标准：</strong>{action.completionCriteria}</p>
      </article>)}</div>
    </div>

    <div className="playbook-block retest-comparison" id="retest-comparison">
      <h3>完成后如何判断有没有提升</h3>
      {data.comparison ? <><div className="comparison-metrics"><span>提及率 <strong>{percent(data.comparison.mentionRateBefore)} → {percent(data.comparison.mentionRateAfter)}</strong></span><span>首批推荐率 <strong>{percent(data.comparison.primaryRateBefore)} → {percent(data.comparison.primaryRateAfter)}</strong></span></div><ul>{data.comparison.questions.map((question) => <li key={question.text}><span>{question.text}</span><strong>{levelLabel[question.before]} → {levelLabel[question.after]}</strong></li>)}</ul></> : <p>目前没有可直接比较的同题上一轮。完成行动后，仍用这 3 道题、3 个独立对话复测，系统会自动显示前后变化。</p>}
    </div>
    <p className="playbook-disclaimer">{data.disclaimer}</p>
  </section>;
}
