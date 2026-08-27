import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { getMerchants, getScanRuns } from "@/lib/api";

import { retryScanAction } from "./actions";

const statusLabels = {
  queued: "等待执行",
  running: "检测中",
  completed: "已完成",
  partial: "部分完成",
  failed: "执行失败",
};

export default async function ScansPage({
  searchParams = Promise.resolve({}),
}: {
  searchParams?: Promise<{ merchant?: string }>;
}) {
  const params = await searchParams;
  const merchantId = params.merchant ?? (await getMerchants())[0]?.id;
  const runs = merchantId ? await getScanRuns(merchantId) : [];
  return (
    <AppShell>
      <div className="workspace-page">
        <header className="page-header">
          <div>
            <p className="kicker">SCAN RUNS</p>
            <h1>检测记录</h1>
            <p>每次检测绑定固定问题版本，原始回答不会被覆盖。</p>
          </div>
          {merchantId && <Link className="button primary" href={`/queries?merchant=${merchantId}`}>审核问题</Link>}
        </header>
        {runs.length === 0 ? (
          <div className="state-page"><h2>暂无真实检测记录</h2><p>先创建商家并审核问题，再发起联网检测。</p></div>
        ) : (
          <div className="table-wrap">
            <table aria-label="检测记录" className="responsive-record-table">
              <thead><tr><th scope="col">执行时间</th><th scope="col">方式</th><th scope="col">状态</th><th scope="col">有效结果</th><th scope="col">操作</th></tr></thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <th data-label="执行时间" data-primary="true" scope="row">{new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(run.created_at))}</th>
                    <td data-label="方式">{run.adapter_name === "ark" ? "火山方舟联网" : run.adapter_name}</td>
                    <td data-label="状态">
                      <span>{statusLabels[run.status]}</span>
                      {run.error_summary && <small className="run-error-summary">{run.error_summary}</small>}
                    </td>
                    <td data-label="有效结果">{run.success_count} / {run.success_count + run.failure_count}</td>
                    <td className="run-actions" data-label="操作">
                      <Link className="text-link" href={`/scans/${run.id}?merchant=${merchantId}`}>查看 →</Link>
                      {(run.status === "completed" || run.status === "partial") && (
                        <Link className="text-link" href={`/reports/${run.id}?merchant=${merchantId}`}>报告</Link>
                      )}
                      {(run.status === "failed" || run.status === "partial") && (
                        <form action={retryScanAction} data-requires-admin="true">
                          <input name="scanRunId" type="hidden" value={run.id} />
                          <input name="merchantId" type="hidden" value={merchantId} />
                          <button className="text-button" data-requires-admin="true" type="submit">重新执行</button>
                        </form>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
