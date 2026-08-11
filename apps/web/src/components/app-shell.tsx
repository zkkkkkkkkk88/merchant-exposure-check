import Link from "next/link";
import type { ReactNode } from "react";

const navigation = [
  ["总览", "/"],
  ["商家", "/merchants"],
  ["问题库", "/queries"],
  ["检测记录", "/scans"],
  ["历史对比", "/history"],
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="navigation-rail">
        <Link className="brand-mark" href="/" aria-label="曝光志首页">
          <span>曝</span>
          <strong>曝光志</strong>
        </Link>
        <nav aria-label="主导航">
          {navigation.map(([label, href], index) => (
            <Link className={index === 0 ? "nav-link active" : "nav-link"} href={href} key={href}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              {label}
            </Link>
          ))}
        </nav>
        <div className="rail-note">
          <span className="live-dot" />
          公开信息检测
        </div>
      </aside>
      <header className="mobile-header">
        <Link className="brand-mark" href="/"><span>曝</span><strong>曝光志</strong></Link>
        <Link href="/merchants">商家</Link>
      </header>
      <main className="app-content">{children}</main>
    </div>
  );
}
