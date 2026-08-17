import { AppShell } from "@/components/app-shell";
import { MerchantSwitcher } from "@/components/merchant-switcher";
import { PrintReportButton } from "@/components/print-report-button";
import { SourceGapTable } from "@/components/source-gap-table";
import {
  getJourneyProgress,
  getLatestPlatformAudit,
  getMerchant,
  getMerchantProfile,
  getMerchants,
  getMobileWorkspace,
  getQuerySets,
} from "@/lib/api";
import { profileFieldLabel } from "@/lib/profile-field-labels";
import { buildDeliveryReadiness, deliveryVisibilityLevel } from "@/lib/delivery-readiness";

const percent = (value: number) => `${Math.round(value * 100)}%`;

export default async function DeliveryReportPage({
  searchParams = Promise.resolve({}),
}: {
  searchParams?: Promise<{ merchant?: string }>;
}) {
  const { merchant: merchantId } = await searchParams;
  const merchants = await getMerchants();
  if (!merchantId) {
    return (
      <AppShell><div className="state-page"><h1>请先选择目标商家</h1><p>交付报告只汇总已选择商家的真实检测证据。</p>{merchants.length > 0 && <MerchantSwitcher merchants={merchants} merchantId="" />}</div></AppShell>
    );
  }
  if (!merchants.some((item) => item.id === merchantId)) {
    return <AppShell><div className="state-page"><h1>目标商家不存在</h1><MerchantSwitcher merchants={merchants} merchantId="" /></div></AppShell>;
  }

  const [merchant, profile, querySets, workspace, audit, journey] = await Promise.all([
    getMerchant(merchantId),
    getMerchantProfile(merchantId),
    getQuerySets(merchantId),
    getMobileWorkspace(merchantId),
    getLatestPlatformAudit(merchantId),
    getJourneyProgress(merchantId),
  ]);
  if (!merchant) return <AppShell><div className="state-page"><h1>商家资料暂不可用</h1></div></AppShell>;

  const metrics = workspace?.metrics;
  const firstBatchAchieved = (metrics?.primaryCount ?? 0) > 0;
  const confirmedFacts = profile?.facts.filter((fact) => fact.confirmation_status === "confirmed") ?? [];
  const latestQueries = querySets[0]?.queries ?? [];
  const selectedQueries = latestQueries.filter((query) => query.review_status === "approved" && query.is_enabled);
  const repeatedCompetitors = (workspace?.recommendationPlaybook?.competitorReasons ?? [])
    .filter((item) => item.questionCount >= 2);
  const platformGaps = (audit?.platforms ?? []).filter((item) => item.status !== "complete");
  const playbook = workspace?.recommendationPlaybook;
  const readiness = buildDeliveryReadiness({
    confirmedFactCount: confirmedFacts.length,
    approvedQuestionCount: selectedQueries.length,
    confirmedAnswerCount: metrics?.confirmedCount ?? 0,
    mentionCount: metrics?.mentionCount ?? 0,
    primaryCount: metrics?.primaryCount ?? 0,
    platformAuditRecorded: Boolean(audit && audit.platforms.length > 0),
    comparableRetest: Boolean(playbook?.comparison),
  });
  const visibilityLevel = deliveryVisibilityLevel({
    confirmedAnswerCount: metrics?.confirmedCount ?? 0,
    mentionCount: metrics?.mentionCount ?? 0,
    primaryCount: metrics?.primaryCount ?? 0,
  });

  return (
    <AppShell>
      <article className="delivery-report">
        <header className="delivery-report-header">
          <div>
            <p className="kicker">DELIVERY REPORT</p>
            <h1>手机版豆包商家可见性交付报告</h1>
            <p>{merchant.name}{merchant.branch_name ? ` · ${merchant.branch_name}` : ""} · 基于已确认的手机实测与公开页面查缺</p>
          </div>
          <div className="report-actions">
            <MerchantSwitcher merchants={merchants} merchantId={merchantId} />
            <PrintReportButton
              disabled={!readiness.accepted}
              disabledReason={readiness.blockingReasons.join("；")}
            />
          </div>
        </header>

        <section className={`report-readiness ${readiness.accepted ? "accepted" : "blocked"}`} aria-label="交付验收清单">
          <header>
            <div>
              <p className="kicker">DELIVERY GATE</p>
              <h2>{readiness.accepted ? "核心检测已完成" : "核心检测尚未完成"}</h2>
            </div>
            <strong>{readiness.accepted ? "可交付" : `${readiness.blockingReasons.length} 项阻塞`}</strong>
          </header>
          <ul>
            {readiness.items.map((item) => (
              <li className={item.complete ? "complete" : item.blocking ? "blocking" : "supporting"} key={item.key}>
                <span aria-hidden="true">{item.complete ? "✓" : item.blocking ? "!" : "·"}</span>
                <div><strong>{item.label}</strong><small>{item.detail}</small></div>
              </li>
            ))}
          </ul>
          {!readiness.accepted && <p>完成 3 个独立对话并确认回答后，即可打印交付报告。</p>}
          {readiness.accepted && !firstBatchAchieved && <p>首批推荐属于进阶成果，不影响本次检测报告交付。</p>}
        </section>

        <section className="report-conclusion" aria-label="交付结论">
          <div><span>可见性等级</span><strong>{visibilityLevel}</strong></div>
          <div><span>目标商家被提及</span><strong>{metrics ? `${metrics.mentionCount}/${metrics.confirmedCount}` : "暂无实测"}</strong></div>
          <div><span>首批推荐</span><strong>{metrics ? `${metrics.primaryCount}/${metrics.confirmedCount}` : "暂无实测"}</strong></div>
          <div><span>六步证据进度</span><strong>{journey ? `${journey.completed_count}/${journey.total_count}` : "暂无"}</strong></div>
        </section>

        <section className="delivery-report-section">
          <header><span>01</span><div><h2>商家与检测范围</h2><p>只展示已确认资料，不用缺失字段推断结论。</p></div></header>
          <div className="report-two-column">
            <dl className="report-facts">
              <div><dt>商家</dt><dd>{merchant.name}</dd></div>
              <div><dt>地区</dt><dd>{[merchant.city, merchant.district].filter(Boolean).join(" · ")}</dd></div>
              <div><dt>行业</dt><dd>{merchant.industry}</dd></div>
              <div><dt>本轮候选题</dt><dd>{latestQueries.length} 道，已选择 {selectedQueries.length} 道</dd></div>
            </dl>
            <dl className="report-facts">
              {confirmedFacts.length > 0 ? confirmedFacts.slice(0, 8).map((fact) => (
                <div key={fact.field_key}><dt>{profileFieldLabel(fact.field_key)}</dt><dd>{Array.isArray(fact.value) ? fact.value.join("、") : String(fact.value)}</dd></div>
              )) : <div><dt>已确认资料</dt><dd>暂无</dd></div>}
            </dl>
          </div>
        </section>

        <section className="delivery-report-section">
          <header><span>02</span><div><h2>3 个独立对话结果摘要</h2><p>正文只保留问题、提及状态和推荐位次，完整原话可在网页附录中核验。</p></div></header>
          <div className="report-answer-list report-answer-summary-list">
            {(workspace?.latestRoundAnswers ?? []).length > 0 ? workspace?.latestRoundAnswers?.map((answer) => (
              <article key={answer.position}>
                <header><strong>Q{answer.position} · {answer.question}</strong><span>{answer.mentionLabel}{answer.targetPosition ? ` · 第 ${answer.targetPosition} 位` : ""}</span></header>
              </article>
            )) : <p className="report-empty">暂无已确认的手机实测答案。</p>}
          </div>
        </section>

        <section className="delivery-report-section">
          <header><span>03</span><div><h2>重复出现的同行与推荐理由</h2><p>仅列出在至少2个问题答案中出现的同行，避免偶然提及造成误导。</p></div></header>
          <div className="report-card-grid">
            {repeatedCompetitors.length > 0 ? repeatedCompetitors.map((competitor) => (
              <article className="report-card" key={competitor.name}>
                <h3>{competitor.name}</h3><p className="report-frequency">出现于 {competitor.questionCount} 个问题</p>
                <ul>{competitor.reasons.length > 0 ? competitor.reasons.map((reason) => <li key={reason.text}>{reason.text}</li>) : <li>答案提及该同行，但没有提取到明确理由。</li>}</ul>
              </article>
            )) : <p className="report-empty">暂无在2个及以上答案中重复出现的同行。</p>}
          </div>
        </section>

        <section className="delivery-report-section">
          <header><span>04</span><div><h2>公开平台与来源查缺</h2><p>“未检索到”只表示本轮没有确认页面，不等于商家一定没有发布。</p></div></header>
          <div className="report-platform-list">
            {platformGaps.length > 0 ? platformGaps.map((platform) => (
              <article key={platform.platform_key}><strong>{platform.platform_name}</strong><span>{platform.status}</span><p>{platform.issues.join("；") || "本轮需要人工核实"}</p></article>
            )) : <p className="report-empty">暂无平台缺口记录。</p>}
          </div>
          {workspace && workspace.sourceGaps.length > 0 && <SourceGapTable data={workspace} />}
        </section>

        <section className="delivery-report-section" id="improvement-playbook">
          <header><span>05</span><div><h2>下一步执行清单</h2><p>项目负责指出该补什么、发布到哪里；商家负责核实并在自己的账号中发布。</p></div></header>
          <div className="report-action-list">
            {(playbook?.actions ?? []).length > 0 ? playbook?.actions.map((action, index) => (
              <article key={action.key}>
                <span>{String(index + 1).padStart(2, "0")}</span><div><h3>{action.title}</h3><p>{action.why}</p><ol>{action.steps.map((step) => <li key={step}>{step}</li>)}</ol><strong>完成标准：{action.completionCriteria}</strong></div>
              </article>
            )) : <p className="report-empty">完成一轮手机实测后，系统会生成针对性的执行清单。</p>}
          </div>
        </section>

        <section className="delivery-report-section" id="retest-comparison">
          <header><span>06</span><div><h2>同题复测前后对比</h2><p>只有使用相同问题完成两轮实测，才显示趋势。</p></div></header>
          {playbook?.comparison ? <div className="report-comparison"><strong>{percent(playbook.comparison.mentionRateBefore)} → {percent(playbook.comparison.mentionRateAfter)}</strong><span>提及率</span><strong>{percent(playbook.comparison.primaryRateBefore)} → {percent(playbook.comparison.primaryRateAfter)}</strong><span>首批推荐率</span></div> : <p className="report-empty">尚未形成可比较的同题复测。</p>}
        </section>

        <section className="delivery-report-section report-answer-appendix" aria-label="原始回答附录">
          <header><span>附</span><div><h2>原始回答附录</h2><p>仅供网页核验豆包原话，打印或另存为 PDF 时不包含本附录。</p></div></header>
          <div className="report-answer-disclosures">
            {(workspace?.latestRoundAnswers ?? []).length > 0 ? workspace?.latestRoundAnswers?.map((answer) => (
              <details key={answer.position}>
                <summary>Q{answer.position} · {answer.question} · {answer.mentionLabel}{answer.targetPosition ? ` · 第 ${answer.targetPosition} 位` : ""}</summary>
                <p>{answer.answer || "本题没有保存答案文本。"}</p>
              </details>
            )) : <p className="report-empty">暂无已确认的手机实测答案。</p>}
          </div>
        </section>

        <footer className="delivery-report-footer">
          <strong>结论边界</strong>
          <p>{playbook?.disclaimer ?? "本报告记录实测结果与公开资料，不代表豆包官方排序规则，也不承诺未来每次回答都会推荐目标商家。"}</p>
        </footer>
      </article>
    </AppShell>
  );
}
