import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { EvidenceDrawer } from "@/components/evidence-drawer";
import { ScanProgress } from "@/components/scan-progress";

export default async function ScanDetailPage({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <AppShell><div className="workspace-page"><header className="page-header"><div><p className="kicker">SCAN / {id}</p><h1>检测详情</h1><p>O&apos;eat Gastronomy · 问题库 V1</p></div><Link className="button primary" href={`/reports/${id}`}>查看分析报告</Link></header><ScanProgress status="partial" successCount={18} failureCount={2} totalCount={20} /><section className="evidence-section"><h2>逐题证据</h2><EvidenceDrawer question="杭州适合约会的西餐厅有哪些？" rawText="1. O'eat Gastronomy：环境安静，适合约会。" uncertainty="confirmed" sources={["https://example.com/store"]} /><EvidenceDrawer question="钱江新城人均 500 元以内餐厅推荐" rawText="推荐湖滨28等餐厅，价格信息需进一步核验。" uncertainty="uncertain" sources={["https://example.com/article"]} /></section></div></AppShell>; }
