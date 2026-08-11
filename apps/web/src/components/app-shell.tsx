"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { BackLink } from "./back-link";

const navigation = [
  ["总览", "/"],
  ["商家画像", "/merchants"],
  ["问题策略", "/queries"],
  ["检测", "/scans"],
  ["历史", "/history"],
] as const;

function fallbackFor(pathname: string): string {
  if (pathname.startsWith("/merchants/")) return "/merchants";
  if (pathname.startsWith("/reports/")) return "/scans";
  if (pathname.startsWith("/scans/")) return "/scans";
  return "/";
}

function isCurrent(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/scans") return pathname.startsWith("/scans") || pathname.startsWith("/reports");
  return pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  return (
    <div className="app-shell">
      <aside className="navigation-rail">
        <Link className="brand-mark" href="/" aria-label="见序首页">
          <span>见</span>
          <span className="brand-copy"><strong>见序</strong><small>Visibility Dossier</small></span>
        </Link>
        <nav aria-label="主导航">
          {navigation.map(([label, href], index) => {
            const current = isCurrent(pathname, href);
            return (
              <Link
                aria-current={current ? "page" : undefined}
                className={`nav-link${current ? " active" : ""}`}
                href={href}
                key={href}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="rail-note"><span className="live-dot" />商家可见性档案</div>
      </aside>
      <header className="mobile-header">
        <Link className="brand-mark" href="/"><span>见</span><strong>见序</strong></Link>
        <Link href="/merchants">商家画像</Link>
      </header>
      <main className="app-content">
        {pathname !== "/" && <div className="global-back"><BackLink fallbackHref={fallbackFor(pathname)} /></div>}
        {children}
      </main>
    </div>
  );
}
