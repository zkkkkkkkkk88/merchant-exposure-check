export type MobileAnswerItem = { id: string; position: number };

export type MobileAnswerDraft = {
  itemId: string;
  mentionLevel: "none" | "supplementary" | "primary";
  competitors: string[];
  answerExcerpt: string;
  needsReview: boolean;
};

const institutionPattern = /([\u4e00-\u9fffA-Za-z·]{2,30}(?:口腔(?:门诊部|诊所|医院)?|医院|诊所))/g;

function splitBlocks(rawText: string, count: number): string[] {
  const markers = [...rawText.matchAll(/(?:^|\n)\s*(?:Q|问题)\s*([1-9]\d*)\s*[：:.、-]?\s*/gi)];
  if (markers.length) {
    const blocks = Array.from({ length: count }, () => "");
    markers.forEach((marker, index) => {
      const position = Number(marker[1]) - 1;
      if (position < 0 || position >= count || marker.index === undefined) return;
      const start = marker.index + marker[0].length;
      const end = markers[index + 1]?.index ?? rawText.length;
      blocks[position] = rawText.slice(start, end).trim();
    });
    return blocks;
  }
  const separated = rawText.split(/\n\s*(?:-{3,}|={3,}|【?回答\s*[1-3]】?)\s*\n/i).map((item) => item.trim()).filter(Boolean);
  return Array.from({ length: count }, (_, index) => separated[index] ?? "");
}

export function parseMobileAnswers(rawText: string, items: MobileAnswerItem[], merchantName: string): MobileAnswerDraft[] {
  const blocks = splitBlocks(rawText, items.length);
  const merchantTokens = [merchantName, merchantName.replace(/(?:口腔)?(?:门诊部|诊所|医院)$/u, "")].filter((item) => item.length >= 2);
  return items.map((item, index) => {
    const answer = blocks[index] ?? "";
    const mentioned = merchantTokens.some((token) => answer.includes(token));
    const targetIndex = Math.min(...merchantTokens.map((token) => answer.indexOf(token)).filter((value) => value >= 0));
    const firstInstitution = answer.search(institutionPattern);
    const targetContext = Number.isFinite(targetIndex)
      ? answer.slice(Math.max(0, targetIndex - 12), targetIndex + merchantName.length + 12)
      : "";
    const explicitlyPrimary = /首推|优先|第一推荐/.test(targetContext);
    const explicitlySupplementary = /补充|备选|也可|作为/.test(targetContext);
    const supplementary = mentioned && !explicitlyPrimary && (
      explicitlySupplementary || (firstInstitution >= 0 && Number.isFinite(targetIndex) && targetIndex > firstInstitution)
    );
    const competitors = [...new Set((answer.match(institutionPattern) ?? []).map((candidate) => candidate.replace(/^(?:首推|推荐|也可以看看|可以看看|备选|补充|作为)/, "")))].filter(
      (candidate) => !merchantTokens.some((token) => candidate.includes(token) || token.includes(candidate)),
    );
    return {
      itemId: item.id,
      mentionLevel: mentioned ? (supplementary ? "supplementary" : "primary") : "none",
      competitors,
      answerExcerpt: answer.slice(0, 500),
      needsReview: answer.length === 0,
    };
  });
}
