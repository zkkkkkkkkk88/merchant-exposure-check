import Link from "next/link";

import { ActionList } from "@/components/action-list";
import { AppShell } from "@/components/app-shell";
import { CategoryCoverage } from "@/components/category-coverage";
import { CompetitorTable } from "@/components/competitor-table";
import { ExposureTrend } from "@/components/exposure-trend";
import { MetricStrip } from "@/components/metric-strip";
import { ApiError, getDashboard } from "@/lib/api";
import type { DashboardData } from "@/lib/contracts";

const demo: DashboardData = {
  merchant: { id: "demo", name: "O'eat Gastronomy", branchName: "杭州万象城店" },
  lastRunAt: "2026-08-11T09:30:00+08:00",
  metrics: { mentionRate: 0.4, firstPositionRate: 0.25, sourceCoverageRate: 0.6, validQueryCount: 18, totalQueryCount: 20 },
  trend: [{ label: "07/14", target: 0.22, benchmark: 0.38 }, { label: "07/28", target: 0.31, benchmark: 0.41 }, { label: "08/11", target: 0.4, benchmark: 0.43 }],
  categories: [{ name: "场景", rate: 0.5, mentioned: 3, total: 6 }, { name: "品类", rate: 0.33, mentioned: 2, total: 6 }, { name: "地理", rate: 0.25, mentioned: 1, total: 4 }, { name: "价格", rate: 0.25, mentioned: 1, total: 4 }],
  competitors: [{ name: "湖滨28餐厅", mentions: 9, firstPositions: 4, sourceCount: 6 }, { name: "金沙厅", mentions: 7, firstPositions: 3, sourceCount: 5 }, { name: "桂语山房", mentions: 6, firstPositions: 2, sourceCount: 4 }],
  actions: [{ id: "a1", title: "补齐营业时间与价格区间", priority: "high", evidenceCount: 4 }, { id: "a2", title: "建立可检索的独立媒体来源", priority: "high", evidenceCount: 3 }, { id: "a3", title: "强化约会场景的事实描述", priority: "medium", evidenceCount: 2 }],
};

export default async function DashboardPage({ searchParams = Promise.resolve({}) }: { searchParams?: Promise<{ merchant?: string }> }) {
  const { merchant } = await searchParams;
  let data: DashboardData | null = demo;
  let error: string | null = null;
  if (merchant) {
    try { data = await getDashboard(merchant); } catch (reason) { error = reason instanceof ApiError ? reason.message : "暂时无法读取检测数据。"; }
  }
  if (error) return <AppShell><div className="state-page"><p className="kicker">DATA UNAVAILABLE</p><h1>数据读取失败</h1><p>{error}</p><Link className="button primary" href={merchant ? `/?merchant=${merchant}` : "/"}>重新加载</Link></div></AppShell>;
  if (!data) return <AppShell><div className="state-page"><p className="kicker">START HERE</p><h1>创建第一个商家后开始检测</h1><Link className="button primary" href="/merchants/new">创建商家</Link></div></AppShell>;
  return <AppShell><div className="dashboard"><header className="dashboard-header"><div><p className="kicker">MERCHANT EXPOSURE / OVERVIEW</p><h1>{data.merchant.name}</h1><p className="merchant-meta">{data.merchant.branchName ?? "全部门店"} · 最近检测 {new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(data.lastRunAt))}</p></div><div className="header-actions"><Link className="merchant-switch" href="/merchants">切换商家 <span>⌄</span></Link><Link className="button primary" href={`/scans?merchant=${data.merchant.id}`}>发起新检测</Link></div></header><MetricStrip metrics={data.metrics} /><div className="dashboard-grid primary-grid"><ExposureTrend trend={data.trend} /><ActionList actions={data.actions} /></div><div className="dashboard-grid secondary-grid"><CategoryCoverage categories={data.categories} /><CompetitorTable competitors={data.competitors} /></div><footer className="method-note"><strong>方法说明</strong><p>结果来自已审核问题的公开联网回答，出现率只描述本次检测样本，不代表平台内部排名。每条结论均应回到原始回答与来源核验。</p><Link href="/methodology">查看口径</Link></footer></div></AppShell>;
}
