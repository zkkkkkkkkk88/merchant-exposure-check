"use client";

import { useEffect, useState } from "react";
import { resolvePublicApiBaseUrl } from "@/lib/api-base";

type RuntimeStatus = {
  status: "ok" | "degraded";
  api: "ok";
  database: "ok" | "error";
  worker: "ok" | "offline";
  integrations: { doubao: boolean; amap: boolean; tencent_map: boolean };
};

const API_BASE_URL = resolvePublicApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL,
);

export function ServiceStatus({ compact = false }: { compact?: boolean }) {
  const [status, setStatus] = useState<RuntimeStatus | null>(null);
  const [unreachable, setUnreachable] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/system/status`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`status ${response.status}`);
        return response.json() as Promise<RuntimeStatus>;
      })
      .then(setStatus)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setUnreachable(true);
      });
    return () => controller.abort();
  }, []);

  if (compact) {
    const ready = status?.status === "ok";
    const label = unreachable
      ? "服务未连接"
      : !status
        ? "正在检查"
        : status.database === "error"
          ? "数据库异常"
          : status.worker === "offline"
            ? "后台未运行"
            : !status.integrations.doubao
              ? "豆包未配置"
              : "状态：可用";
    return <span className={`mobile-service-state ${ready ? "ready" : "warning"}`}>{label}</span>;
  }

  if (!status) {
    return <div className="service-status warning"><strong>{unreachable ? "服务未连接" : "正在检查服务"}</strong><small>{unreachable ? "请确认一键启动已完成" : "正在读取 API 与后台任务状态"}</small></div>;
  }

  return (
    <details className={`service-status ${status.status === "ok" ? "ready" : "warning"}`}>
      <summary><span className="live-dot" />{status.status === "ok" ? "系统可用" : "系统需要检查"}</summary>
      <ul>
        <li>{status.api === "ok" && status.database === "ok" ? "API 正常" : "API 或数据库异常"}</li>
        <li>{status.worker === "ok" ? "后台任务正常" : "后台任务未运行"}</li>
        <li>{status.integrations.doubao ? "豆包已配置" : "豆包未配置"}</li>
        <li>{status.integrations.amap ? "高德已配置" : "高德未配置"}</li>
        <li>{status.integrations.tencent_map ? "腾讯地图已配置" : "腾讯地图未配置"}</li>
      </ul>
    </details>
  );
}
