"use client";

import { useMemo, useState } from "react";
import { createMobileValidationSet, saveMobileRound } from "@/app/mobile-checks/actions";
import type { MobileValidationSetData, MobileWorkspaceData } from "@/lib/contracts";
import { parseMobileAnswers } from "@/lib/mobile-answer-parser";
import { SourceGapTable } from "./source-gap-table";

const percent = (value: number) => `${Math.round(value * 100)}%`;

export function MobileCheckWorkspace({ merchantId, merchantName, validationSet, workspace }: { merchantId: string; merchantName: string; validationSet: MobileValidationSetData | null; workspace: MobileWorkspaceData }) {
  const [rawText, setRawText] = useState("");
  const [parsed, setParsed] = useState(false);
  const drafts = useMemo(() => validationSet ? parseMobileAnswers(rawText, validationSet.items, merchantName) : [], [rawText, validationSet, merchantName]);
  const copyQuestions = async () => {
    if (!validationSet) return;
    await navigator.clipboard.writeText(validationSet.items.map((item) => `Q${item.position}：${item.query.text}`).join("\n\n"));
  };

  return <div className="mobile-check-layout">
    {workspace.metrics && <section className="mobile-metrics" aria-label="手机版实测指标"><article><span>提及率</span><strong>{percent(workspace.metrics.mentionRate)}</strong></article><article><span>首批推荐率</span><strong>{percent(workspace.metrics.primaryRate)}</strong></article><article><span>场景覆盖率</span><strong>{percent(workspace.metrics.categoryCoverageRate)}</strong></article><article><span>信息准确率</span><strong>{percent(workspace.metrics.informationAccuracyRate)}</strong></article></section>}
    <section className="workspace-card"><header><div><p className="kicker">THREE DIALOGS</p><h2>3个独立豆包对话</h2></div><span>{validationSet?.items.length ?? 0} 道</span></header>
      {validationSet ? <><p className="workflow-note">请分别开启3个新对话，每个对话只问一道，避免上下文影响推荐结果。</p><ol className="mobile-question-list">{validationSet.items.map((item) => <li key={item.id}><span>Q{item.position}</span>{item.query.text}</li>)}</ol><button className="button secondary" type="button" onClick={copyQuestions}>一键复制全部问题</button></> : <div className="empty-panel"><p>最新版题库需要至少3道已审核并启用的推荐问题。</p><form action={createMobileValidationSet}><input name="merchantId" type="hidden" value={merchantId} /><button className="button primary" type="submit">创建3题验证集</button></form></div>}
    </section>
    {validationSet && <form className="workspace-card mobile-entry" action={saveMobileRound}>
      <input name="merchantId" type="hidden" value={merchantId} /><input name="validationSetId" type="hidden" value={validationSet.id} /><input name="itemIds" type="hidden" value={validationSet.items.map((item) => item.id).join(",")} /><input name="sourceRoundId" type="hidden" value={workspace.sourceRoundId ?? ""} />
      <header><div><p className="kicker">ONE PASTE</p><h2>一次粘贴并统一确认</h2></div></header>
      <label>测试位置<input name="location" placeholder="例如：澜沧拉祜族自治县" /></label><label className="check-row"><input defaultChecked name="webSearch" type="checkbox" />已开启联网搜索</label>
      <label>集中粘贴3份回答<textarea aria-label="集中粘贴3份回答" name="rawQaText" rows={12} value={rawText} onChange={(event) => { setRawText(event.target.value); setParsed(false); }} placeholder={'请按下面格式粘贴：\nQ1：第一份完整回答\n\nQ2：第二份完整回答\n\nQ3：第三份完整回答'} /></label>
      <button className="button secondary" type="button" onClick={() => setParsed(true)}>识别三份回答</button>
      {parsed && <fieldset><legend>自动识别结果（只需核对异常项）</legend>{validationSet.items.map((item, index) => { const draft = drafts[index]; return <div className={`quick-confirm${draft.needsReview ? " needs-review" : ""}`} key={item.id}><div><p>{item.position}. {item.query.text}</p>{draft.needsReview && <small>未识别到这一份回答，请检查Q编号。</small>}</div><select aria-label={`${item.query.text} 提及层级`} name={`mention-${item.id}`} defaultValue={draft.mentionLevel}><option value="none">未提及</option><option value="supplementary">补充提及</option><option value="primary">首批推荐</option></select><input aria-label={`${item.query.text} 竞品`} name={`competitors-${item.id}`} defaultValue={draft.competitors.join("、")} placeholder="自动识别的竞品，可修改" /><input name={`excerpt-${item.id}`} type="hidden" value={draft.answerExcerpt} /><label className="check-row"><input name={`accurate-${item.id}`} type="checkbox" />信息准确</label></div>; })}</fieldset>}
      <label>独立来源审计结果<textarea name="sources" rows={6} placeholder="一次粘贴来源：机构｜来源类型｜标题｜事实｜网址（可省略）" /></label>{workspace.sourceRoundId && <label className="check-row"><input name="inheritSources" type="checkbox" />本轮来源无变化，沿用上一轮</label>}
      <label>可选来源截图<input accept="image/jpeg,image/png,image/webp" multiple name="evidence" type="file" /><small>截图仅作可选证据，不需要每题上传。</small></label><button className="button primary" disabled={!parsed || drafts.some((draft) => draft.needsReview)} type="submit">统一保存并确认本轮</button>
    </form>}
    <section className="workspace-card source-gap-section"><header><div><p className="kicker">SOURCE GAP</p><h2>目标商家与竞品来源差距</h2></div></header><SourceGapTable data={workspace} /></section>
  </div>;
}
