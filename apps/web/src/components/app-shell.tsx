"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type ReactNode } from "react";

import { persistMerchantContext } from "@/lib/merchant-context";

import { DemoMutationGuard } from "./demo-mutation-guard";
import { useAccessRole } from "./access-role-provider";
import { BackLink } from "./back-link";
import { ServiceStatus } from "./service-status";
import { JourneyProgress } from "./journey-progress";
import { MobileMerchantLabel } from "./mobile-merchant-label";

const navigation = [
  ["总览", "/"],
  ["商家画像", "/merchants"],
  ["平台查缺", "/platform-audits"],
  ["问题策略", "/queries"],
  ["手机实测", "/mobile-checks"],
  ["检测", "/scans"],
  ["历史", "/history"],
  ["交付报告", "/delivery-report"],
] as const;

const mobilePrimaryNavigation = [
  ["首页", "/"],
  ["画像", "/merchants"],
  ["检测", "/scans"],
  ["报告", "/delivery-report"],
] as const;

const mobileMoreNavigation = [
  ["平台查缺", "/platform-audits"],
  ["问题策略", "/queries"],
  ["手机实测", "/mobile-checks"],
  ["历史", "/history"],
  ["方法说明", "/methodology"],
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
  const role = useAccessRole();
  const [menuOpen, setMenuOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [phoneNavigation, setPhoneNavigation] = useState(false);
  const pathname = usePathname() ?? "/";
  const searchParams = useSearchParams();
  const profileMerchant = pathname.match(/^\/merchants\/([^/]+)$/)?.[1];
  const merchantId = profileMerchant ?? searchParams?.get("merchant");
  useEffect(() => {
    if (merchantId) persistMerchantContext(merchantId);
  }, [merchantId]);
  useEffect(() => {
    if (!moreOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMoreOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [moreOpen]);
  useEffect(() => {
    const media = window.matchMedia?.("(max-width: 720px)");
    if (!media) return;
    const update = () => setPhoneNavigation(media.matches);
    update();
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, []);
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
        {role === "demo" && <span className="access-role-badge"><strong>演示模式</strong><small>演示模式不可操作</small></span>}
        <ServiceStatus />
      </aside>
      <header className="mobile-header">
        <Link className="brand-mark" href={withMerchant("/")}><span>见</span><strong>见序</strong></Link>
        <MobileMerchantLabel merchantId={merchantId} />
        <div className="mobile-header-actions">
          {role === "demo" && <span className="access-role-badge"><strong>演示模式</strong><small>演示模式不可操作</small></span>}
          <ServiceStatus compact />
          <button
            aria-controls="mobile-navigation"
            aria-expanded={menuOpen}
            aria-label={menuOpen ? "关闭导航" : "打开导航"}
            className="mobile-menu-button"
            onClick={() => setMenuOpen((value) => !value)}
            type="button"
          >
            <span aria-hidden="true">{menuOpen ? "×" : "☰"}</span>
          </button>
        </div>
      </header>
      <nav
        aria-label="手机版主导航"
        className="mobile-navigation"
        hidden={!menuOpen}
        id="mobile-navigation"
      >
        {navigation.map(([label, href], index) => {
          const current = isCurrent(pathname, href);
          return (
            <Link
              aria-current={current ? "page" : undefined}
              className={current ? "active" : ""}
              href={withMerchant(href)}
              key={href}
              onClick={() => setMenuOpen(false)}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              {label}
            </Link>
          );
        })}
      </nav>
      <nav aria-hidden={!phoneNavigation} aria-label="手机版底部导航" className="mobile-bottom-navigation">
        {mobilePrimaryNavigation.map(([label, href]) => {
          const current = isCurrent(pathname, href);
          return <Link aria-current={current ? "page" : undefined} className={current ? "active" : ""} href={withMerchant(href)} key={href}>{label}</Link>;
        })}
        <button aria-controls="mobile-more-sheet" aria-expanded={moreOpen} className={moreOpen ? "active" : ""} onClick={() => setMoreOpen((open) => !open)} type="button">更多</button>
      </nav>
      <div aria-labelledby="mobile-more-title" aria-modal="true" className="mobile-more-sheet" hidden={!moreOpen} id="mobile-more-sheet" role="dialog">
        <button aria-label="关闭更多菜单" className="mobile-more-backdrop" onClick={() => setMoreOpen(false)} type="button" />
        <div className="mobile-more-panel">
          <header><h2 id="mobile-more-title">更多</h2><button aria-label="关闭更多菜单" className="mobile-more-close" onClick={() => setMoreOpen(false)} type="button">×</button></header>
          <nav aria-label="更多导航">
            {mobileMoreNavigation.map(([label, href]) => {
              const current = isCurrent(pathname, href);
              return <Link aria-current={current ? "page" : undefined} href={withMerchant(href)} key={href} onClick={() => setMoreOpen(false)}>{label}</Link>;
            })}
          </nav>
        </div>
      </div>
      <main className="app-content">
        {pathname !== "/" && <div className="global-back"><BackLink fallbackHref={fallbackFor(pathname)} /></div>}
        {merchantId && <JourneyProgress merchantId={merchantId} />}
        {children}
      </main>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<DemoMutationGuard><div className="app-shell"><main className="app-content">{children}</main></div></DemoMutationGuard>}>
      <DemoMutationGuard><ShellContent>{children}</ShellContent></DemoMutationGuard>
    </Suspense>
  );
}
