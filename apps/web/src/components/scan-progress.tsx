"use client";

const labels = {
  queued: "等待执行",
  running: "检测中",
  completed: "已完成",
  partial: "部分完成",
  failed: "执行失败",
} as const;

export function ScanProgress({
  status,
  successCount,
  failureCount,
  totalCount,
}: {
  status: keyof typeof labels;
  successCount: number;
  failureCount: number;
  totalCount: number;
}) {
  const progress = totalCount
    ? Math.round(((successCount + failureCount) / totalCount) * 100)
    : 0;
  return (
    <section className="scan-progress" aria-label="检测进度">
      <div>
        <span className={`run-status run-${status}`}>{labels[status]}</span>
        <strong>{successCount} / {totalCount}</strong>
        <p>{failureCount ? `${failureCount} 条失败，本次结果已保存` : "检测记录会持续保存"}</p>
      </div>
      <div className="progress-track" aria-label={`${progress}%`}>
        <i style={{ width: `${progress}%` }} />
      </div>
    </section>
  );
}
