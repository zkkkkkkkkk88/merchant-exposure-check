export type Priority = "high" | "medium" | "low";

export interface DashboardData {
  merchant: { id: string; name: string; branchName?: string };
  lastRunAt: string;
  metrics: {
    mentionRate: number;
    firstPositionRate: number;
    sourceCoverageRate: number;
    validQueryCount: number;
    totalQueryCount: number;
  };
  trend: Array<{ label: string; target: number; benchmark: number }>;
  categories: Array<{ name: string; rate: number; mentioned: number; total: number }>;
  competitors: Array<{
    name: string;
    mentions: number;
    firstPositions: number;
    sourceCount: number;
  }>;
  actions: Array<{
    id: string;
    title: string;
    priority: Priority;
    evidenceCount: number;
  }>;
}
