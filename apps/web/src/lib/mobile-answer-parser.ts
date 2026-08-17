export type MobileAnswerItem = { id: string; position: number };

export type MobileAnswerDraft = {
  itemId: string;
  mentionLevel: "none" | "supplementary" | "primary";
  competitors: string[];
  answerExcerpt: string;
  needsReview: boolean;
};

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

function entityCore(value: string): string {
  return value
    .replace(/[（(][^）)]*[）)]/gu, "")
    .replace(/[\s（）()·•,，。\-—_/]/g, "")
    .replace(/(?:澜沧拉祜族自治县|澜沧县|澜沧|普洱市|普洱|口腔医疗机构|口腔科|口腔诊所|口腔门诊部|口腔门诊|口腔|门诊部|门诊|诊所|医院|有限责任公司|有限公司)/gu, "");
}

function isSameEntity(candidate: string, merchantName: string): boolean {
  const candidateCore = entityCore(candidate);
  const merchantCore = entityCore(merchantName);
  return candidateCore.length >= 2 && (
    candidateCore === merchantCore || merchantCore.endsWith(candidateCore) || candidateCore.endsWith(merchantCore)
  );
}

function extractListedEntities(answer: string): Array<{ name: string; index: number }> {
  const entities: Array<{ name: string; index: number }> = [];
  const pattern = /^\s*(?:\d+\s*[.、．]|[-•])\s*([^：:\n]{2,60}?)(?:\s*[：:].*)?\s*$/gmu;
  for (const match of answer.matchAll(pattern)) {
    const name = match[1].trim().replace(/[。；;，,]$/u, "");
    if (/(?:医院|口腔科|口腔|门诊|诊所)/u.test(name)) entities.push({ name, index: match.index ?? 0 });
  }
  const inlinePattern = /(?:首推|推荐|看看|考虑)\s*([\u4e00-\u9fffA-Za-z·（）()]{2,30}(?:口腔(?:门诊部|门诊|诊所)?|医院|诊所))/gu;
  for (const match of answer.matchAll(inlinePattern)) {
    const name = match[1].trim();
    if (!entities.some((entity) => entity.name === name)) entities.push({ name, index: match.index ?? 0 });
  }
  entities.sort((left, right) => left.index - right.index);
  return entities;
}

export function parseMobileAnswers(rawText: string, items: MobileAnswerItem[], merchantName: string): MobileAnswerDraft[] {
  const blocks = splitBlocks(rawText, items.length);
  return items.map((item, index) => {
    const answer = blocks[index] ?? "";
    const listed = extractListedEntities(answer);
    const targetPosition = listed.findIndex((entity) => isSameEntity(entity.name, merchantName));
    const mentionedInList = targetPosition >= 0;
    const merchantCore = entityCore(merchantName);
    const mentionedInText = merchantCore.length >= 2 && answer.includes(merchantCore);
    const mentioned = mentionedInList || mentionedInText;
    const targetTextIndex = answer.indexOf(merchantCore);
    const targetPrefix = targetTextIndex >= 0
      ? answer.slice(Math.max(0, targetTextIndex - 15), targetTextIndex)
      : "";
    const targetSuffix = targetTextIndex >= 0
      ? answer.slice(targetTextIndex + merchantCore.length, targetTextIndex + merchantCore.length + 10)
      : "";
    const explicitlySupplementary = /补充|备选|作为|也可/.test(targetPrefix) || /^(?:口腔)?(?:门诊部|门诊|诊所|医院)?(?:可作为补充|是备选)/.test(targetSuffix);
    const competitors = [...new Set(listed
      .filter((entity) => !isSameEntity(entity.name, merchantName))
      .map((entity) => entity.name))];
    return {
      itemId: item.id,
      mentionLevel: mentioned ? (targetPosition > 0 || explicitlySupplementary ? "supplementary" : "primary") : "none",
      competitors,
      answerExcerpt: answer,
      needsReview: answer.length === 0,
    };
  });
}
