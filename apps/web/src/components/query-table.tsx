"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { createScanAction, updateQueryAction } from "@/app/queries/actions";

type ReviewStatus = "pending" | "approved" | "rejected";
type Category = "all" | "geo" | "category" | "product" | "price" | "occasion" | "need";
type SaveStatus = { state: "saving" | "saved" | "error"; message: string };

export interface QueryRow {
  id: string;
  text: string;
  category: string;
  reason: string;
  priority: number;
  reviewStatus: ReviewStatus;
  isEnabled: boolean;
  intentType?: "recommendation" | "verification";
}

const categories: Array<[Category, string]> = [
  ["all", "全部"],
  ["geo", "地域"],
  ["category", "品类"],
  ["product", "产品"],
  ["price", "价格"],
  ["occasion", "场景"],
  ["need", "需求"],
];

interface QueryTableProps {
  initialQueries: QueryRow[];
  merchantId: string;
  querySetId: string;
  selectedCategory: Category;
}

export function QueryTable({
  initialQueries,
  merchantId,
  querySetId,
  selectedCategory,
}: QueryTableProps) {
  const router = useRouter();
  const [queries, setQueries] = useState(initialQueries);
  const [saveStatus, setSaveStatus] = useState<Record<string, SaveStatus>>({});
  const [batchError, setBatchError] = useState("");
  const [scanError, setScanError] = useState("");
  const [creating, setCreating] = useState(false);
  const savedText = useRef(new Map(initialQueries.map((query) => [query.id, query.text])));

  useEffect(() => {
    setQueries(initialQueries);
    savedText.current = new Map(initialQueries.map((query) => [query.id, query.text]));
  }, [initialQueries]);

  const eligible = queries.filter(
    (item) => item.reviewStatus === "approved" && item.isEnabled,
  ).length;
  const visibleQueries = queries.filter(
    (item) => selectedCategory === "all" || item.category === selectedCategory,
  );

  function replaceQuery(id: string, next: QueryRow) {
    setQueries((items) => items.map((item) => item.id === id ? next : item));
  }

  async function persist(
    id: string,
    changes: Parameters<typeof updateQueryAction>[1],
    optimistic: Partial<QueryRow>,
    rollback?: QueryRow,
  ) {
    const previous = rollback ?? queries.find((item) => item.id === id);
    if (!previous) return false;
    const next = { ...previous, ...optimistic };
    replaceQuery(id, next);
    setSaveStatus((items) => ({ ...items, [id]: { state: "saving", message: "保存中…" } }));

    const result = await updateQueryAction(id, changes);
    if (!result.ok) {
      replaceQuery(id, previous);
      setSaveStatus((items) => ({ ...items, [id]: { state: "error", message: result.error } }));
      return false;
    }

    if (changes.text !== undefined) savedText.current.set(id, changes.text);
    setSaveStatus((items) => ({ ...items, [id]: { state: "saved", message: "已保存" } }));
    return true;
  }

  async function handleTextBlur(id: string) {
    const current = queries.find((item) => item.id === id);
    if (!current) return;
    const previousText = savedText.current.get(id) ?? current.text;
    if (current.text === previousText) return;
    await persist(
      id,
      { text: current.text },
      { text: current.text },
      { ...current, text: previousText },
    );
  }

  async function handleBatchApprove() {
    const pending = queries.filter((item) => item.reviewStatus === "pending");
    if (!pending.length) return;
    setBatchError("");
    const results = await Promise.all(pending.map(async (item) => ({
      item,
      result: await updateQueryAction(item.id, { reviewStatus: "approved", isEnabled: true }),
    })));
    const successful = new Set(results.filter(({ result }) => result.ok).map(({ item }) => item.id));
    setQueries((items) => items.map((item) => successful.has(item.id)
      ? { ...item, reviewStatus: "approved", isEnabled: true }
      : item));
    setSaveStatus((items) => ({
      ...items,
      ...Object.fromEntries(results.map(({ item, result }) => [
        item.id,
        result.ok
          ? { state: "saved", message: "已保存" }
          : { state: "error", message: result.error },
      ])),
    }));
    const failed = results.length - successful.size;
    if (failed) setBatchError(`${failed} 条问题保存失败，请重试。`);
  }

  async function handleCreateScan() {
    if (!eligible || creating) return;
    setCreating(true);
    setScanError("");
    const result = await createScanAction(merchantId, querySetId);
    if (result.ok) {
      router.push(`/scans/${result.data.id}`);
      return;
    }
    setCreating(false);
    setScanError(result.error);
  }

  return (
    <div className="query-workspace">
      <div className="query-toolbar">
        <nav className="category-tabs" aria-label="问题分类">
          {categories.map(([value, label]) => {
            const count = value === "all"
              ? queries.length
              : queries.filter((item) => item.category === value).length;
            const params = new URLSearchParams({ merchant: merchantId });
            if (value !== "all") params.set("category", value);
            return (
              <Link
                aria-current={selectedCategory === value ? "page" : undefined}
                href={`/queries?${params.toString()}`}
                key={value}
              >
                {label} {count}
              </Link>
            );
          })}
        </nav>
        <button className="text-button" onClick={handleBatchApprove} type="button">
          批量批准待审核
        </button>
      </div>

      <div className="scan-launcher">
        <div>
          <p className="scan-count">可用于检测 {eligible} 条</p>
          {!eligible && <span>请先批准并启用至少一个问题。</span>}
          {batchError && <span className="inline-error" role="alert">{batchError}</span>}
          {scanError && <span className="inline-error" role="alert">{scanError}</span>}
        </div>
        <button
          className="button primary"
          disabled={!eligible || creating}
          onClick={handleCreateScan}
          type="button"
        >
          {creating ? "正在创建任务…" : `开始后台检测（${eligible} 条）`}
        </button>
      </div>

      <div className="table-wrap">
        <table aria-label="待审核问题库">
          <thead>
            <tr><th>问题</th><th>检测类型</th><th>分类</th><th>生成理由</th><th>优先级</th><th>状态</th><th>操作</th></tr>
          </thead>
          <tbody>
            {visibleQueries.map((item) => {
              const status = saveStatus[item.id];
              const isSaving = status?.state === "saving";
              return (
                <tr className={!item.isEnabled || item.reviewStatus === "rejected" ? "excluded-row" : ""} key={item.id}>
                  <th>
                    <input
                      aria-label={`编辑问题 ${item.id}`}
                      disabled={isSaving}
                      value={item.text}
                      onBlur={() => handleTextBlur(item.id)}
                      onChange={(event) => replaceQuery(item.id, { ...item, text: event.target.value })}
                    />
                  </th>
                  <td><span className={`intent-label intent-${item.intentType ?? "recommendation"}`}>{item.intentType === "verification" ? "信息验证" : "推荐检测"}</span></td>
                  <td>{categories.find(([value]) => value === item.category)?.[1]}</td>
                  <td>{item.reason}</td>
                  <td>{item.priority}</td>
                  <td>{item.reviewStatus === "approved" ? "已批准" : item.reviewStatus === "rejected" ? "已拒绝" : "待审核"}</td>
                  <td>
                    {item.reviewStatus === "pending" ? (
                      <>
                        <button
                          className="row-action"
                          disabled={isSaving}
                          onClick={() => persist(item.id, { reviewStatus: "approved", isEnabled: true }, { reviewStatus: "approved", isEnabled: true })}
                          type="button"
                        >批准并用于检测</button>
                        <button
                          className="row-action muted"
                          disabled={isSaving}
                          onClick={() => persist(item.id, { reviewStatus: "rejected", isEnabled: false }, { reviewStatus: "rejected", isEnabled: false })}
                          type="button"
                        >拒绝</button>
                      </>
                    ) : (
                      <label className="toggle-label">
                        <input
                          aria-label={`用于检测 ${item.id}`}
                          type="checkbox"
                          checked={item.reviewStatus === "approved" && item.isEnabled}
                          disabled={isSaving}
                          onChange={(event) => event.target.checked
                            ? persist(item.id, { reviewStatus: "approved", isEnabled: true }, { reviewStatus: "approved", isEnabled: true })
                            : persist(item.id, { isEnabled: false }, { isEnabled: false })}
                        />用于检测
                      </label>
                    )}
                    {status && (
                      <small
                        className={`save-state save-${status.state}`}
                        role={status.state === "error" ? "alert" : "status"}
                      >
                        {status.message}
                      </small>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
