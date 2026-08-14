from __future__ import annotations

import re
from collections import Counter

from app.merchants.models import Merchant
from app.mobile_checks.models import MobileCheckResult, MobileCheckRound, MobileRoundSource


LEVEL_LABELS = {"none": "未提及", "supplementary": "补充提及", "primary": "首批推荐"}
LEVEL_RANK = {"none": 0, "supplementary": 1, "primary": 2}


def _core(value: str) -> str:
    text = re.sub(r"[\s（）()·•,，。\-—_/]", "", value.casefold())
    for token in ("澜沧拉祜族自治县", "澜沧县", "澜沧", "口腔科", "口腔诊所", "口腔门诊部", "口腔门诊", "口腔", "门诊部", "门诊", "诊所"):
        text = text.replace(token, "")
    return text


def _same_entity(left: str, right: str) -> bool:
    left_core, right_core = _core(left), _core(right)
    return bool(left_core and right_core and (left_core == right_core or left_core in right_core or right_core in left_core))


def _entries(answer: str | None) -> list[tuple[int, str, str]]:
    if not answer:
        return []
    pattern = re.compile(
        r"(?m)^\s*(\d{1,2})\s*[.、．]\s*([^：:\n]{2,60}?)(?:\s*[：:]\s*([^\n]+))?\s*$"
    )
    matches = list(pattern.finditer(answer))
    entries: list[tuple[int, str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(answer)
        continuation = answer[match.end():end].strip()
        parts = [part.strip() for part in (match.group(3) or "", continuation) if part.strip()]
        entries.append((int(match.group(1)), match.group(2).strip(), "；".join(parts)))
    return entries


def _target_position(result: MobileCheckResult, merchant_name: str) -> int | None:
    for position, name, _ in _entries(result.answer_excerpt):
        if _same_entity(name, merchant_name):
            return position
    return None


def _concise_reason(description: str) -> str:
    description = re.split(
        r"[。；;]\s*(?:乡镇\s*[-—：:]\s*)?[^。；;\n]{1,30}口腔(?:门诊部|门诊|诊所)\s*[：:]",
        description,
        maxsplit=1,
    )[0]
    cleaned = re.sub(r"\s+", "", description).strip("。；;，,")
    return cleaned[:54] + ("…" if len(cleaned) > 54 else "")


def _confirmed_results(round_record: MobileCheckRound) -> list[MobileCheckResult]:
    return sorted(
        (result for result in round_record.results if result.is_confirmed),
        key=lambda result: result.validation_item.position,
    )


def _rates(round_record: MobileCheckRound) -> tuple[float, float]:
    results = _confirmed_results(round_record)
    total = len(results)
    if not total:
        return 0.0, 0.0
    return (
        sum(item.mention_level != "none" for item in results) / total,
        sum(item.mention_level == "primary" for item in results) / total,
    )


def _comparison(latest: MobileCheckRound, previous: MobileCheckRound | None) -> dict | None:
    if previous is None:
        return None
    current_results = _confirmed_results(latest)
    previous_results = _confirmed_results(previous)
    current_by_text = {re.sub(r"\s+", "", item.validation_item.query.text): item for item in current_results}
    previous_by_text = {re.sub(r"\s+", "", item.validation_item.query.text): item for item in previous_results}
    if not current_by_text or set(current_by_text) != set(previous_by_text):
        return None
    before_mention, before_primary = _rates(previous)
    after_mention, after_primary = _rates(latest)
    questions = []
    for text, current in current_by_text.items():
        old = previous_by_text[text]
        delta = LEVEL_RANK[current.mention_level] - LEVEL_RANK[old.mention_level]
        questions.append({
            "text": current.validation_item.query.text,
            "before": old.mention_level,
            "after": current.mention_level,
            "change": "improved" if delta > 0 else "declined" if delta < 0 else "unchanged",
        })
    return {
        "previousRoundId": str(previous.id),
        "currentRoundId": str(latest.id),
        "mentionRateBefore": before_mention,
        "mentionRateAfter": after_mention,
        "primaryRateBefore": before_primary,
        "primaryRateAfter": after_primary,
        "questions": questions,
    }


def _competitor_reasons(results: list[MobileCheckResult], sources: list[MobileRoundSource], exclude_public_oral: bool = False) -> list[dict]:
    appearances: list[dict] = []
    appearance_order = 0
    for result in results:
        question_position = result.validation_item.position
        for _, name, description in _entries(result.answer_excerpt):
            if exclude_public_oral and _is_public_oral_entity(name):
                continue
            matched = next((item for item in appearances if _same_entity(item["name"], name)), None)
            if matched is None:
                matched = {"name": name, "positions": set(), "descriptions": [], "order": appearance_order}
                appearance_order += 1
                appearances.append(matched)
            matched["positions"].add(question_position)
            if description:
                matched["descriptions"].append((question_position, description))
    ranked = sorted(
        (item for item in appearances if len(item["positions"]) >= 2),
        key=lambda item: (-len(item["positions"]), item["order"]),
    )[:3]
    output = []
    for appearance in ranked:
        competitor = appearance["name"]
        reasons: list[dict] = []
        seen: set[str] = set()
        for position, description in appearance["descriptions"]:
            reason = _concise_reason(description)
            if reason and reason not in seen:
                reasons.append({"text": reason, "questionPositions": [position], "confidence": "answer_only"})
                seen.add(reason)
        for source in sources:
            if not source.is_confirmed or not _same_entity(source.entity_name, competitor):
                continue
            for fact in source.facts:
                reason = _concise_reason(fact)
                if reason and reason not in seen:
                    reasons.append({"text": reason, "questionPositions": [], "confidence": "confirmed"})
                    seen.add(reason)
        if not reasons:
            reasons.append({"text": "答案列出了该机构，但没有给出可核验的推荐理由", "questionPositions": [], "confidence": "needs_verification"})
        output.append({"name": competitor, "questionCount": len(appearance["positions"]), "reasons": reasons[:3]})
    return output


def _is_public_oral_entity(name: str) -> bool:
    return any(marker in name for marker in ("人民医院", "中医医院", "妇幼保健院", "卫生院", "公立医院"))


def _actions(merchant: Merchant, results: list[MobileCheckResult], competitor_reasons: list[dict], sources: list[MobileRoundSource]) -> list[dict]:
    actions: list[dict] = []
    shorthand_results = []
    for result in results:
        for _, entry_name, _ in _entries(result.answer_excerpt):
            if _same_entity(entry_name, merchant.name) and entry_name != merchant.name:
                shorthand_results.append((result.validation_item.position, entry_name))
    if shorthand_results:
        position, shorthand = shorthand_results[0]
        actions.append({
            "key": "name_consistency",
            "title": "统一机构正式名称与常用简称",
            "why": f"Q{position} 中豆包使用“{shorthand}”提及目标商家，和正式名称“{merchant.name}”不完全一致，容易分散机构实体信息。",
            "steps": ["确定一个对外正式名称和一个常用简称", "统一官网、地图、工商展示页和短视频账号简介中的名称", "在机构介绍首段同时写明正式名称与简称"],
            "materials": ["营业执照或登记名称", "现有地图、公众号、抖音等账号清单"],
            "publishTargets": [
                {"priority": 1, "channel": "高德地图、百度地图、腾讯地图", "content": "统一机构正式名称、常用简称、地址、电话和营业时间"},
                {"priority": 2, "channel": "微信公众号、视频号、抖音企业主页", "content": "在机构简介首段同时写明正式名称和常用简称"},
                {"priority": 3, "channel": "工商登记或医疗机构执业公示", "content": "核对并保留主体名称与资质证明链接，不制作宣传性表述"},
            ],
            "linkEntryHint": "发布后把公开链接粘贴到下一轮的“独立来源审计结果”，用于核对名称是否一致。",
            "examples": [f"{merchant.name}（常用简称：{shorthand}）"],
            "completionCriteria": "主要公开页面的正式名称一致，简称均能明确指向同一机构。",
            "confidence": "confirmed",
        })
    missing = [result for result in results if result.mention_level == "none"]
    if missing:
        missing_labels = "、".join(f"Q{item.validation_item.position}“{item.validation_item.query.text}”" for item in missing)
        actions.append({
            "key": "missing_scenarios",
            "title": "补齐口碑与稳定经营的可验证资料",
            "why": f"{missing_labels} 均未提及目标商家，说明这些推荐场景缺少足够明确、可核验的公开信息。",
            "steps": ["整理真实的医生、消毒、服务流程和经营信息", "为每项信息绑定可公开核验的页面或凭证", "把同一组事实同步到机构介绍、地图商户页和短视频主页"],
            "materials": ["医生及资质材料", "消毒与就诊流程", "真实评价与问题处理记录"],
            "publishTargets": [
                {"priority": 1, "channel": "微信公众号文章或机构官网介绍页", "content": "完整发布医生、资质、消毒、就诊流程和经营信息，并附可核验材料"},
                {"priority": 2, "channel": "视频号、抖音企业主页", "content": "把已核实流程拆成短视频或图文，并在主页保持机构正式名称一致"},
                {"priority": 3, "channel": "高德地图、百度地图、腾讯地图商户详情", "content": "补充诊疗项目、门店照片、营业时间及完整机构介绍"},
            ],
            "linkEntryHint": "发布后把文章、主页或地图详情链接粘贴到下一轮的“独立来源审计结果”，不要只上传截图。",
            "examples": [f"{merchant.name}就诊信息：医生、消毒与服务流程（仅发布已核实内容）"],
            "completionCriteria": "至少形成一页完整机构介绍，并能为每项核心事实提供公开来源。",
            "confidence": "needs_verification",
        })
    supplementary = [result for result in results if result.mention_level == "supplementary"]
    target_sources = [source for source in sources if source.is_confirmed and _same_entity(source.entity_name, merchant.name)]
    if supplementary or not target_sources:
        competitor_examples = []
        for competitor in competitor_reasons[:2]:
            usable = next((reason for reason in competitor["reasons"] if reason["confidence"] != "needs_verification"), None)
            if usable:
                competitor_examples.append(f"{competitor['name']}：{usable['text']}")
        why = "当前只在补充推荐中出现，尚未进入首批推荐。" if supplementary else "当前没有已确认的目标商家公开来源。"
        actions.append({
            "key": "evidence_depth",
            "title": "补齐关键服务事实，争取进入首批推荐",
            "why": why + (" 对比机构已有具体描述，目标商家需要用同等清晰度提供自己的可核验事实。" if competitor_examples else " 先建立稳定的公开事实来源，再进行下一轮同题复测。"),
            "steps": ["从诊疗项目、医生资质、设备和就诊便利性中选择已核实的差异点", "每个差异点写成一条具体事实并附来源", "完成后使用原三题重新测试，观察补充提及是否变为首批推荐"],
            "materials": ["诊疗项目清单", "医生资质或设备凭证", "对应公开页面链接"],
            "publishTargets": [
                {"priority": 1, "channel": "机构官网或微信公众号专题页", "content": "按诊疗项目逐条发布已核实的医生、设备、流程和适用人群，并附凭证"},
                {"priority": 2, "channel": "高德地图、百度地图、腾讯地图商户详情", "content": "同步真实诊疗项目、设备和就诊便利信息"},
                {"priority": 3, "channel": "视频号、抖音企业主页", "content": "用短视频展示已核实的项目流程或设备，不照抄竞品卖点"},
            ],
            "linkEntryHint": "每发布一项就保留对应公开链接，并粘贴到下一轮的“独立来源审计结果”后再同题复测。",
            "examples": competitor_examples[:2],
            "completionCriteria": "至少有 3 条核心事实可公开核验，并完成一次同题复测。",
            "confidence": "answer_only" if competitor_examples else "needs_verification",
        })
    return actions[:3]


def build_recommendation_playbook(
    merchant: Merchant,
    latest: MobileCheckRound,
    previous: MobileCheckRound | None,
    sources: list[MobileRoundSource],
) -> dict:
    results = _confirmed_results(latest)
    mentioned = [result for result in results if result.mention_level != "none"]
    primary = [result for result in results if result.mention_level == "primary"]
    questions = [{
        "position": result.validation_item.position,
        "text": result.validation_item.query.text,
        "mentionLevel": result.mention_level,
        "mentionLabel": LEVEL_LABELS[result.mention_level],
        "targetPosition": _target_position(result, merchant.name),
    } for result in results]
    if not results:
        summary = "本轮没有已确认的题目结果，暂时无法生成提升诊断。"
    elif not mentioned:
        summary = f"本轮 {len(results)} 题均未提及目标商家，应先补齐名称一致性和可核验的公开资料。"
    elif not primary:
        summary = f"本轮 {len(results)} 题中有 {len(mentioned)} 题补充提及、没有首批推荐；当前重点是把零散提及变成稳定的首批推荐。"
    else:
        summary = f"本轮 {len(results)} 题中有 {len(mentioned)} 题提及、{len(primary)} 题首批推荐；下一步应巩固已命中场景并补齐缺失场景。"
    oral_scope = "口腔" in merchant.industry
    if oral_scope:
        sources = [source for source in sources if source.entity_name == merchant.name or not _is_public_oral_entity(source.entity_name)]
    competitor_reasons = _competitor_reasons(results, sources, exclude_public_oral=oral_scope)
    return {
        "diagnosis": {"summary": summary, "mentionedCount": len(mentioned), "totalCount": len(results), "questions": questions},
        "competitorReasons": competitor_reasons,
        "actions": _actions(merchant, results, competitor_reasons, sources),
        "comparison": _comparison(latest, previous),
        "disclaimer": "以上建议仅依据本轮豆包回答和已确认来源生成，不保证平台排序；涉及机构能力、医保、设备或资历的信息必须核实后再发布。",
    }
