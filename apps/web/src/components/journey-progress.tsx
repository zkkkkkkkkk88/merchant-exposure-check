"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getJourneyProgress } from "@/lib/api";
import type { JourneyProgressData } from "@/lib/contracts";

export function JourneyProgress({ merchantId }: { merchantId: string }) {
  const [progress, setProgress] = useState<JourneyProgressData | null>(null);

  useEffect(() => {
    let active = true;
    if (typeof getJourneyProgress !== "function") return () => {
      active = false;
    };
    getJourneyProgress(merchantId)
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
  const nextStep = progress.steps.find((step) => step.key === progress.current_step)
    ?? progress.steps.find((step) => step.status !== "completed");

  return (
    <section className="journey-progress" aria-label="商家提升进度">
      <div className="journey-progress-summary">
        <strong>商家进度 {progress.completed_count}/{progress.total_count}</strong>
        <span>{nextStep ? `下一步：${nextStep.label}` : "六步证据已完成"}</span>
      </div>
      <ol>
        {progress.steps.map((step, index) => (
          <li className={`journey-step journey-${step.status}`} key={step.key}>
            <Link href={step.href}>
              <span>{index + 1}</span>
              <small>{step.label}</small>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}
