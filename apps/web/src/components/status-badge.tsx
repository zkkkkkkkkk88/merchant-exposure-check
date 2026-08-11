import type { Priority } from "@/lib/contracts";

const labels: Record<Priority, string> = {
  high: "优先",
  medium: "关注",
  low: "观察",
};

export function StatusBadge({ priority }: { priority: Priority }) {
  return <span className={`status-badge status-${priority}`}>{labels[priority]}</span>;
}
