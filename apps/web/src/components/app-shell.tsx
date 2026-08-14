"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, type ReactNode } from "react";

import { BackLink } from "./back-link";
import { ServiceStatus } from "./service-status";

const navigation = [
  ["总览", "/"],
  ["商家画像", "/merchants"],
  ["平台查缺", "/platform-audits"],
  ["问题策略", "/queries"],
  ["手机实测", "/mobile-checks"],
  ["检测", "/scans"],
  ["历史", "/history"],
] as const;

function fallbackFor(pathname: string): string {
  if (pathname === "/competitors" || pathname === "/actions") return "/";
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

function ShellContent({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const searchParams = useSearchParams();
  const profileMerchant = pathname.match(/^\/merchants\/([^/]+)$/)?.[1];
  const merchantId = profileMerchant ?? searchParams?.get("merchant");
  const withMerchant = (href: string) => {
    if (!merchantId) return href;
    if (href === "/merchants") return `/merchants/${encodeURIComponent(merchantId)}`;
    return `${href}${href.includes("?") ? "&" : "?"}merchant=${encodeURIComponent(merchantId)}`;
  };
  return (
    <div className="app-shell">
      <aside className="navigation-rail">
        <Link className="brand-mark" href={withMerchant("/")} aria-label="见序首页">
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
                href={withMerchant(href)}
                key={href}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                {label}
              </Link>
            );
          })}
        </nav>
        <ServiceStatus />
      </aside>
      <header className="mobile-header">
        <Link className="brand-mark" href={withMerchant("/")}><span>见</span><strong>见序</strong></Link>
        <div className="mobile-header-actions"><ServiceStatus compact /><Link href={withMerchant("/merchants")}>商家画像</Link></div>
      </header>
      <main className="app-content">
        {pathname !== "/" && <div className="global-back"><BackLink fallbackHref={fallbackFor(pathname)} /></div>}
        {children}
      </main>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<div className="app-shell"><main className="app-content">{children}</main></div>}>
      <ShellContent>{children}</ShellContent>
    </Suspense>
  );
}
