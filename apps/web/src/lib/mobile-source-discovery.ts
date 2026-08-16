import type { MobileAnswerDraft } from "./mobile-answer-parser";

export type CompetitorOccurrenceData = {
  name: string;
  occurrence_count: number;
};

function entityCore(value: string): string {
  return value
    .normalize("NFKC")
    .replace(/[\s（）()·]/g, "")
    .replace(/(?:口腔医疗机构|口腔门诊部|口腔门诊|门诊部|诊所|医院|口腔)$/u, "")
    .toLocaleLowerCase("zh-CN");
}

export function countRecurringCompetitors(
  drafts: MobileAnswerDraft[],
  merchantName: string,
): CompetitorOccurrenceData[] {
  const targetCore = entityCore(merchantName);
  const counts = new Map<string, { name: string; count: number; first: number }>();
  let sequence = 0;
  for (const answer of drafts) {
    const seenInAnswer = new Set<string>();
    for (const rawName of answer.competitors) {
      const name = rawName.trim();
      const core = entityCore(name);
      if (!core || core === targetCore || seenInAnswer.has(core)) continue;
      seenInAnswer.add(core);
      const current = counts.get(core);
      if (current) current.count += 1;
      else counts.set(core, { name, count: 1, first: sequence++ });
    }
  }
  return [...counts.values()]
    .filter((item) => item.count >= 2)
    .sort((left, right) => right.count - left.count || left.first - right.first)
    .slice(0, 3)
    .map((item) => ({ name: item.name, occurrence_count: item.count }));
}
