"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { useAccessRole } from "./access-role-provider";

const DEMO_MESSAGE = "当前为演示权限，实际操作请联系管理员。";

export function DemoMutationGuard({ children }: { children: ReactNode }) {
  const role = useAccessRole();
  const containerRef = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const updateControls = () => container.querySelectorAll<HTMLElement>('[data-requires-admin="true"]').forEach((control) => {
      if (role === "demo") control.setAttribute("aria-disabled", "true");
      else control.removeAttribute("aria-disabled");
    });
    updateControls();
    const observer = new MutationObserver(updateControls);
    observer.observe(container, { childList: true, subtree: true });

    if (role !== "demo") return () => observer.disconnect();
    const block = (event: Event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const marker = '[data-requires-admin="true"]';
      const submitter = event.type === "submit" ? (event as SubmitEvent).submitter : null;
      const locked = submitter instanceof HTMLElement && submitter.matches(marker)
        ? submitter
        : target.closest<HTMLElement>(marker)
          ?? (event.type === "submit" ? target.querySelector<HTMLElement>(marker) : null);
      if (!locked || !container.contains(locked)) return;
      event.preventDefault();
      event.stopPropagation();
      locked.focus();
      setMessage(DEMO_MESSAGE);
    };
    container.addEventListener("click", block, true);
    container.addEventListener("submit", block, true);
    return () => {
      observer.disconnect();
      container.removeEventListener("click", block, true);
      container.removeEventListener("submit", block, true);
    };
  }, [role]);

  return (
    <div className="demo-mutation-guard" data-role={role} ref={containerRef}>
      {children}
      {message && (
        <div aria-live="polite" className="demo-mutation-status" role="status">
          <span>{message}</span>
          <button aria-label="关闭提示" onClick={() => setMessage("")} type="button">关闭</button>
        </div>
      )}
    </div>
  );
}
