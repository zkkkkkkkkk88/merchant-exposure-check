"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { getJourneyProgressAction } from "@/app/server-actions";
import type { JourneyProgressData } from "@/lib/contracts";

type JourneyKey = JourneyProgressData["steps"][number]["key"];

function currentJourneyKey(pathname: string, hash: string): JourneyKey | null {
  if (pathname === "/merchants" || pathname.startsWith("/merchants/")) return "profile";
  if (pathname.startsWith("/queries")) return "queries";
  if (pathname.startsWith("/platform-audits")) return "audit";
  if (pathname.startsWith("/mobile-checks")) {
    if (hash === "#improvement-playbook") return "action";
    if (hash === "#retest-comparison") return "retest";
    return "mobile";
  }
  return null;
}

export function JourneyProgress({ merchantId }: { merchantId: string }) {
  const [progress, setProgress] = useState<JourneyProgressData | null>(null);
  const [hash, setHash] = useState("");
  const pathname = usePathname() ?? "/";

  useEffect(() => {
    const updateHash = () => setHash(window.location.hash);
    updateHash();
    window.addEventListener("hashchange", updateHash);
    return () => window.removeEventListener("hashchange", updateHash);
  }, []);

  useEffect(() => {
    let active = true;
    getJourneyProgressAction(merchantId)
      .then((data) => {
        if (active) setProgress(data);
      })
      .catch(() => {
        if (active) setProgress(null);
      });
    return () => {
      active = false;
    };
  }, [merchantId]);

  if (!progress) return null;
  const currentKey = currentJourneyKey(pathname, hash);
  const nextStep = progress.steps.find((step) => step.key === progress.current_step)
    ?? progress.steps.find((step) => step.status !== "completed");

  return (
    <section className="journey-progress" aria-label="商家提升进度">
      <div className="journey-progress-summary">
        <strong>商家进度 {progress.completed_count}/{progress.total_count}</strong>
        <span>{nextStep ? `下一步：${nextStep.label}` : "六步证据已完成"}</span>
      </div>
      <ol>
        {progress.steps.map((step, index) => {
          const current = step.key === currentKey;
          return (
          <li className={`journey-step journey-${step.status}${current ? " journey-current" : ""}`} key={step.key}>
            <Link aria-current={current ? "step" : undefined} href={step.href}>
              <span>{index + 1}</span>
              <small>{step.label}</small>
            </Link>
          </li>
          );
        })}
      </ol>
    </section>
  );
}
