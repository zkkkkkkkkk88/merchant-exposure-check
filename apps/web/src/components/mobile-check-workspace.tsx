"use client";

import { createMobileValidationSet, saveMobileRound } from "@/app/mobile-checks/actions";
import type { MobileValidationSetData, MobileWorkspaceData } from "@/lib/contracts";
import { SourceGapTable } from "./source-gap-table";

const percent = (value: number) => `${Math.round(value * 100)}%`;

export function MobileCheckWorkspace({ merchantId, validationSet, workspace }: { merchantId: string; validationSet: MobileValidationSetData | null; workspace: MobileWorkspaceData }) {
  return <div className="mobile-check-layout">
    {workspace.metrics && <section className="mobile-metrics" aria-label="手机版实测指标"><article><span>提及率</span><strong>{percent(workspace.metrics.mentionRate)}</strong></article><article><span>首批推荐率</span><strong>{percent(workspace.metrics.primaryRate)}</strong></article><article><span>场景覆盖率</span><strong>{percent(workspace.metrics.categoryCoverageRate)}</strong></article><article><span>信息准确率</span><strong>{percent(workspace.metrics.informationAccuracyRate)}</strong></article></section>}
    <section className="workspace-card"><header><div><p className="kicker">SAMPLE SET</p><h2>代表性手机验证题</h2></div><span>{validationSet?.items.length ?? 0} 道</span></header>{validationSet ? <ol className="mobile-question-list">{validationSet.items.map((item) => <li key={item.id}><span>{item.query.intent_type === "verification" ? "品牌验证" : item.query.category}</span>{item.query.text}</li>)}</ol> : <div className="empty-panel"><p>还没有手机验证题集。请先审核并启用问题，再创建固定抽样题集。</p><form action={createMobileValidationSet}><input name="merchantId" type="hidden" value={merchantId} /><button className="button primary" type="submit">创建手机验证题集</button></form></div>}</section>
    {validationSet && <form className="workspace-card mobile-entry" action={saveMobileRound}>
      <input name="merchantId" type="hidden" value={merchantId} /><input name="validationSetId" type="hidden" value={validationSet.id} /><input name="itemIds" type="hidden" value={validationSet.items.map((item) => item.id).join(",")} /><input name="sourceRoundId" type="hidden" value={workspace.sourceRoundId ?? ""} />
      <header><div><p className="kicker">BATCH ENTRY</p><h2>一次录入本轮结果</h2></div></header>
      <label>测试位置<input name="location" placeholder="例如：澜沧县" /></label><label className="check-row"><input defaultChecked name="webSearch" type="checkbox" />已开启联网搜索</label>
      <label>批量粘贴问答<textarea name="rawQaText" rows={10} placeholder="把多道问题和回答一次粘贴到这里，不需要逐题上传截图。" /></label>
      <fieldset><legend>逐题快速确认</legend>{validationSet.items.map((item) => <div className="quick-confirm" key={item.id}><p>{item.position}. {item.query.text}</p><select aria-label={`${item.query.text} 提及层级`} name={`mention-${item.id}`} defaultValue="none"><option value="none">未提及</option><option value="supplementary">补充提及</option><option value="primary">首批推荐</option></select><input aria-label={`${item.query.text} 竞品`} name={`competitors-${item.id}`} placeholder="竞品名称，用顿号分隔" /><label className="check-row"><input name={`accurate-${item.id}`} type="checkbox" />信息准确</label></div>)}</fieldset>
      <label>合并来源清单<textarea name="sources" rows={6} placeholder="一行一个来源：机构｜来源类型｜标题｜事实｜网址（可省略）" /></label>{workspace.sourceRoundId && <label className="check-row"><input name="inheritSources" type="checkbox" />本轮来源无变化，沿用上一轮</label>}
      <label>可选来源截图<input accept="image/jpeg,image/png,image/webp" multiple name="evidence" type="file" /><small>截图是可选证据，不需要每题上传；第一版不做 OCR。</small></label><button className="button primary" type="submit">保存并确认本轮</button>
    </form>}
    <section className="workspace-card source-gap-section"><header><div><p className="kicker">SOURCE GAP</p><h2>目标商家与竞品来源差距</h2></div></header><SourceGapTable data={workspace} /></section>
  </div>;
}
