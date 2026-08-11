import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { QueryTable } from "@/components/query-table";
import { getMerchants, getQuerySets } from "@/lib/api";

const categories = new Set(["all", "geo", "category", "product", "price", "occasion", "need"]);

export default async function QueriesPage({ searchParams = Promise.resolve({}) }: { searchParams?: Promise<{ merchant?: string; category?: string }> }) {
  const params = await searchParams;
  const merchantId = params.merchant ?? (await getMerchants())[0]?.id;
  const selectedCategory = categories.has(params.category ?? "all")
    ? (params.category ?? "all") as "all" | "geo" | "category" | "product" | "price" | "occasion" | "need"
    : "all";
  const querySets = merchantId ? await getQuerySets(merchantId) : [];
  const latest = querySets.at(-1);
  const queries = latest?.queries.map((query) => ({ id: query.id, text: query.text, category: query.category, reason: query.reason, priority: query.priority, reviewStatus: query.review_status, isEnabled: query.is_enabled, intentType: query.intent_type ?? "recommendation" })) ?? [];
  return (
    <AppShell>
      <div className="workspace-page wide-page">
        <header className="page-header">
          <div><p className="kicker">QUERY LIBRARY{latest ? ` / V${latest.version}` : ""}</p><h1>问题库</h1><p>这里只显示数据库中真实生成并保存的问题。</p></div>
          {merchantId && <Link className="button primary" href={`/scans?merchant=${merchantId}`}>查看检测记录</Link>}
        </header>
        {merchantId && latest && queries.length ? (
          <QueryTable
            initialQueries={queries}
            merchantId={merchantId}
            querySetId={latest.id}
            selectedCategory={selectedCategory}
          />
        ) : <div className="state-page"><h2>暂无问题</h2><p>请先为商家生成问题库。</p></div>}
      </div>
    </AppShell>
  );
}
