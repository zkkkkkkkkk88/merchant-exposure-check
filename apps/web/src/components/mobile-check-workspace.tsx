"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { createMobileValidationSet, saveMobileRound, selectMobileValidationQuestions } from "@/app/mobile-checks/actions";
import type { MobileValidationSetData, MobileWorkspaceData, QueryData } from "@/lib/contracts";
import { parseMobileAnswers } from "@/lib/mobile-answer-parser";
import { SourceGapTable } from "./source-gap-table";
import { MobileRecommendationPlaybook } from "./mobile-recommendation-playbook";
import { LatestMobileRoundAnswers } from "./latest-mobile-round-answers";

const percent = (value: number) => `${Math.round(value * 100)}%`;

export function MobileCheckWorkspace({ candidates, merchantId, merchantName, validationSet, workspace }: { candidates: QueryData[]; merchantId: string; merchantName: string; validationSet: MobileValidationSetData | null; workspace: MobileWorkspaceData }) {
  const [rawText, setRawText] = useState("");
  const [parsed, setParsed] = useState(false);
  const [entryOpen, setEntryOpen] = useState(!workspace.latestRoundId);
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [selectedQuestions, setSelectedQuestions] = useState<string[]>(() => {
    const candidateIds = new Set(candidates.map((query) => query.id));
    return validationSet?.items.map((item) => item.query_id).filter((queryId) => candidateIds.has(queryId)) ?? [];
  });
  const drafts = useMemo(() => validationSet ? parseMobileAnswers(rawText, validationSet.items, merchantName) : [], [rawText, validationSet, merchantName]);
  const copyQuestions = async () => {
    if (!validationSet) return;
    await navigator.clipboard.writeText(validationSet.items.map((item) => `Q${item.position}：${item.query.text}`).join("\n\n"));
  };

  return <div className="mobile-check-layout">
    {workspace.metrics && <section className="previous-results"><header><div><p className="kicker">PREVIOUS RESULT</p><h2>上一轮有效结果</h2></div><span>已确认 {workspace.metrics.confirmedCount} 道</span></header><div className="mobile-metrics" aria-label="手机版实测指标"><article><span>提及率</span><strong>{percent(workspace.metrics.mentionRate)}</strong></article><article><span>首批推荐率</span><strong>{percent(workspace.metrics.primaryRate)}</strong></article><article><span>场景覆盖率</span><strong>{percent(workspace.metrics.categoryCoverageRate)}</strong></article><article><span>信息准确率</span><strong>{percent(workspace.metrics.informationAccuracyRate)}</strong></article></div></section>}
    <nav className="mobile-stepper" aria-label="本轮手机实测步骤"><span className={validationSet ? "done" : "active"}>1 选择3题</span><span className={entryOpen ? "active" : workspace.latestRoundId ? "done" : ""}>2 录入回答</span><span className={parsed ? "active" : workspace.latestRoundId ? "done" : ""}>3 核对异常</span><span className={workspace.latestRoundId && !entryOpen ? "active" : ""}>4 查看建议</span></nav>
    {(!workspace.latestRoundId || entryOpen) && <section className="workspace-card"><header><div><p className="kicker">THREE DIALOGS</p><h2>本轮3个独立豆包对话</h2></div><span>{validationSet?.items.length ?? 0} 道</span></header>
      {validationSet ? <><p className="workflow-note">请分别开启3个新对话，每个对话只问一道，避免上下文影响推荐结果。</p><p className="sample-count">候选题库 {candidates.length} 道 · 本轮抽样 {validationSet.items.length} 道</p><ol className="mobile-question-list">{validationSet.items.map((item) => <li key={item.id}><span>Q{item.position}</span>{item.query.text}</li>)}</ol><div className="mobile-question-actions"><button className="button secondary" type="button" onClick={copyQuestions}>一键复制全部问题</button><button className="text-button" type="button" onClick={() => setSelectorOpen((open) => !open)}>更换本轮3题</button></div></> : <div className="empty-panel"><p>最新版题库需要至少3道已审核并启用的推荐问题。</p><form action={createMobileValidationSet}><input name="merchantId" type="hidden" value={merchantId} /><button className="button primary" type="submit">创建3题验证集</button></form></div>}
      {selectorOpen && <form action={selectMobileValidationQuestions} className="mobile-question-selector"><input name="merchantId" type="hidden" value={merchantId} /><h3>从候选题库选择3题</h3><p>完整检测仍使用全部已启用问题；这里只决定下一轮手机人工实测的3题。</p><div>{candidates.map((query) => <label key={query.id}><input checked={selectedQuestions.includes(query.id)} name="queryIds" type="checkbox" value={query.id} onChange={(event) => setSelectedQuestions((items) => event.target.checked ? [...items, query.id].slice(-3) : items.filter((id) => id !== query.id))} />{query.text}</label>)}</div><button className="button primary" disabled={selectedQuestions.length !== 3} type="submit">保存这3题</button></form>}
    </section>}
    {workspace.latestRoundId && !entryOpen && <section className="workspace-card round-complete">
      <div><p className="kicker">ROUND COMPLETE</p><h2>上一轮已保存成功</h2><p>结果已经计入上方指标。需要重新测试时，再开始新一轮。</p><LatestMobileRoundAnswers answers={workspace.latestRoundAnswers} /></div>
      <button className="button primary" type="button" onClick={() => setEntryOpen(true)}>开始新一轮</button>
    </section>}
    {validationSet && entryOpen && <form className="workspace-card mobile-entry" action={saveMobileRound}>
      <input name="merchantId" type="hidden" value={merchantId} /><input name="validationSetId" type="hidden" value={validationSet.id} /><input name="itemIds" type="hidden" value={validationSet.items.map((item) => item.id).join(",")} /><input name="sourceRoundId" type="hidden" value={workspace.sourceRoundId ?? ""} />
      <header><div><p className="kicker">ONE PASTE</p><h2>一次粘贴并统一确认</h2></div></header>
      <label>测试位置<input name="location" placeholder="例如：澜沧拉祜族自治县" /></label><label className="check-row"><input defaultChecked name="webSearch" type="checkbox" />已开启联网搜索</label>
      <label>集中粘贴3份回答<textarea aria-label="集中粘贴3份回答" name="rawQaText" rows={12} value={rawText} onChange={(event) => { setRawText(event.target.value); setParsed(false); }} placeholder={'请按下面格式粘贴：\nQ1：第一份完整回答\n\nQ2：第二份完整回答\n\nQ3：第三份完整回答'} /></label>
      {parsed && <fieldset><legend>自动识别结果（只需核对异常项）</legend>{validationSet.items.map((item, index) => { const draft = drafts[index]; return <div className={`quick-confirm${draft.needsReview ? " needs-review" : ""}`} key={item.id}><div><p>{item.position}. {item.query.text}</p>{draft.needsReview && <small>未识别到这一份回答，请检查Q编号。</small>}</div><select aria-label={`${item.query.text} 提及层级`} name={`mention-${item.id}`} defaultValue={draft.mentionLevel}><option value="none">未提及</option><option value="supplementary">补充提及</option><option value="primary">首批推荐</option></select><input aria-label={`${item.query.text} 竞品`} name={`competitors-${item.id}`} defaultValue={draft.competitors.join("、")} placeholder="自动识别的竞品，可修改" /><input name={`excerpt-${item.id}`} type="hidden" value={draft.answerExcerpt} /><label className="check-row"><input name={`accurate-${item.id}`} type="checkbox" />信息准确</label></div>; })}</fieldset>}
      <label>独立来源审计结果<textarea name="sources" rows={6} placeholder="一次粘贴来源：机构｜来源类型｜标题｜事实｜网址（可省略）" /></label>{workspace.sourceRoundId && <label className="check-row"><input name="inheritSources" type="checkbox" />本轮来源无变化，沿用上一轮</label>}
      <label>可选来源截图<input accept="image/jpeg,image/png,image/webp" multiple name="evidence" type="file" /><small>截图仅作可选证据，不需要每题上传。</small></label>
      {parsed && drafts.some((draft) => draft.needsReview) && <p className="form-guidance">有回答没有识别到。检查Q1、Q2、Q3编号后，点击“重新识别回答”。</p>}
      <button className="button primary" type={parsed && !drafts.some((draft) => draft.needsReview) ? "submit" : "button"} onClick={parsed && !drafts.some((draft) => draft.needsReview) ? undefined : () => setParsed(true)}>{parsed && !drafts.some((draft) => draft.needsReview) ? "统一保存并确认本轮" : parsed ? "重新识别回答" : "识别回答并继续"}</button>
    </form>}
    <MobileRecommendationPlaybook data={workspace.recommendationPlaybook} />
    <section className="workspace-card source-gap-section"><header><div><p className="kicker">EVIDENCE & PLATFORM GAP</p><h2>证据与平台查缺</h2></div><Link className="text-link" href={`/platform-audits?merchant=${encodeURIComponent(merchantId)}`}>查看公开平台查缺 →</Link></header>{workspace.sourceGaps.length > 0 ? <><h3>目标商家与竞品来源差距</h3><SourceGapTable data={workspace} /></> : <div className="compact-empty"><p>本轮还没有独立来源对比。可先运行公开平台查缺，找出哪些渠道缺信息或存在冲突。</p></div>}</section>
  </div>;
}
