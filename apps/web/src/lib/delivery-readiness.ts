export interface DeliveryReadinessInput {
  confirmedFactCount: number;
  approvedQuestionCount: number;
  confirmedAnswerCount: number;
  primaryCount: number;
  platformAuditRecorded: boolean;
  comparableRetest: boolean;
}

export interface DeliveryReadinessItem {
  key: "profile" | "queries" | "mobile" | "primary" | "audit" | "retest";
  label: string;
  complete: boolean;
  blocking: boolean;
  detail: string;
}

export interface DeliveryReadiness {
  accepted: boolean;
  items: DeliveryReadinessItem[];
  blockingReasons: string[];
}

export function buildDeliveryReadiness(input: DeliveryReadinessInput): DeliveryReadiness {
  const items: DeliveryReadinessItem[] = [
    {
      key: "profile",
      label: "商家核心资料已确认",
      complete: input.confirmedFactCount > 0,
      blocking: false,
      detail: `${input.confirmedFactCount} 项已确认资料`,
    },
    {
      key: "queries",
      label: "至少3道问题已审核启用",
      complete: input.approvedQuestionCount >= 3,
      blocking: false,
      detail: `${input.approvedQuestionCount} 道可用问题`,
    },
    {
      key: "mobile",
      label: "3个独立对话均已确认",
      complete: input.confirmedAnswerCount === 3,
      blocking: true,
      detail: `${input.confirmedAnswerCount}/3 道已确认`,
    },
    {
      key: "primary",
      label: "目标商家至少获得1次首批推荐",
      complete: input.primaryCount >= 1,
      blocking: true,
      detail: `${input.primaryCount} 次首批推荐`,
    },
    {
      key: "audit",
      label: "已有公开平台查缺记录",
      complete: input.platformAuditRecorded,
      blocking: false,
      detail: input.platformAuditRecorded ? "已有查缺证据" : "尚未完成平台查缺",
    },
    {
      key: "retest",
      label: "已有可比较的同题复测",
      complete: input.comparableRetest,
      blocking: false,
      detail: input.comparableRetest ? "前后两轮可直接比较" : "建议优化后使用原3题复测",
    },
  ];
  const blockingReasons: string[] = [];
  if (input.confirmedAnswerCount !== 3) {
    blockingReasons.push("手机实测需要确认完整的3道回答");
  }
  if (input.primaryCount < 1) {
    blockingReasons.push("目标商家尚未获得至少1次首批推荐");
  }
  return { accepted: blockingReasons.length === 0, items, blockingReasons };
}
