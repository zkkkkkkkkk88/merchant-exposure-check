import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app-shell";

const navigation = vi.hoisted(() => ({
  pathname: "/merchants/m1",
  merchant: "merchant-2",
  back: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
  useSearchParams: () => new URLSearchParams({ merchant: navigation.merchant }),
  useRouter: () => ({ back: navigation.back, push: navigation.push }),
}));

beforeEach(() => {
  navigation.pathname = "/merchants/m1";
  window.history.replaceState({}, "", "/");
  navigation.back.mockReset();
  navigation.push.mockReset();
  vi.stubGlobal("fetch", vi.fn().mockImplementation((input: string | URL | Request) => {
    const url = String(input);
    const payload = url.includes("journey-progress")
      ? {
          merchant_id: "m1",
          completed_count: 2,
          total_count: 6,
          current_step: "audit",
          steps: [
            { key: "profile", label: "商家画像", status: "completed", href: "/merchants/m1" },
            { key: "queries", label: "问题策略", status: "completed", href: "/queries?merchant=m1" },
            { key: "audit", label: "平台查缺", status: "ready", href: "/platform-audits?merchant=m1" },
            { key: "mobile", label: "手机实测", status: "pending", href: "/mobile-checks?merchant=m1" },
            { key: "action", label: "执行优化", status: "pending", href: "/mobile-checks?merchant=m1#improvement-playbook" },
            { key: "retest", label: "同题复测", status: "pending", href: "/mobile-checks?merchant=m1#retest-comparison" },
          ],
        }
      : {
          status: "ok",
          api: "ok",
          database: "ok",
          worker: "ok",
          integrations: { doubao: true, amap: true, tencent_map: false },
        };
    return Promise.resolve(new Response(JSON.stringify(payload), { status: 200 }));
  }));
});

afterEach(() => vi.unstubAllGlobals());

it("marks the current navigation section instead of always highlighting overview", () => {
  render(<AppShell><p>内容</p></AppShell>);

  expect(screen.getByRole("link", { name: "02商家画像" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: /总览/ })).not.toHaveAttribute("aria-current");
  expect(screen.getAllByText("见序")[0]).toBeVisible();
  expect(screen.getByText("Visibility Dossier")).toBeVisible();
  expect(screen.getByRole("link", { name: /总览/ })).toHaveAttribute("href", "/?merchant=m1");
  expect(screen.getAllByRole("link", { name: /商家画像/ })).toSatisfy((links: HTMLElement[]) =>
    links.every((link) => link.getAttribute("href") === "/merchants/m1"),
  );
  expect(screen.getByRole("link", { name: /问题策略/ })).toHaveAttribute("href", "/queries?merchant=m1");
  expect(screen.getByRole("link", { name: /检测/ })).toHaveAttribute("href", "/scans?merchant=m1");
  expect(screen.getByRole("link", { name: /历史/ })).toHaveAttribute("href", "/history?merchant=m1");
});

it("keeps the selected merchant when opening merchant profile from another page", () => {
  navigation.pathname = "/";
  render(<AppShell><p>内容</p></AppShell>);

  expect(screen.getAllByRole("link", { name: /商家画像/ })).toSatisfy((links: HTMLElement[]) =>
    links.every((link) => link.getAttribute("href") === "/merchants/merchant-2"),
  );
});

it("provides a back control on child pages", () => {
  window.history.pushState({}, "", "/previous");
  render(<AppShell><p>内容</p></AppShell>);

  fireEvent.click(screen.getByRole("button", { name: "返回" }));

  expect(navigation.push).toHaveBeenCalledWith("/merchants");
  expect(navigation.back).not.toHaveBeenCalled();
});

it("shows whether the API, worker and required integrations are ready", async () => {
  render(<AppShell><p>内容</p></AppShell>);

  await waitFor(() => expect(screen.getByText("系统可用")).toBeVisible());
  fireEvent.click(screen.getByText("系统可用"));
  expect(screen.getByText("API 正常")).toBeVisible();
  expect(screen.getByText("后台任务正常")).toBeVisible();
  expect(screen.getByText("豆包已配置")).toBeVisible();
  expect(screen.getByText("高德已配置")).toBeVisible();
  expect(screen.getByText("腾讯地图未配置")).toBeVisible();
});

it("shows merchant journey progress and exposes the full navigation on mobile", async () => {
  navigation.pathname = "/mobile-checks";
  navigation.merchant = "m1";
  render(<AppShell><p>内容</p></AppShell>);

  await waitFor(() => expect(screen.getByText("商家进度 2/6")).toBeVisible());
  expect(screen.getByText("下一步：平台查缺")).toBeVisible();

  const menuButton = screen.getByRole("button", { name: "打开导航" });
  expect(menuButton).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(menuButton);
  expect(menuButton).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("navigation", { name: "手机版主导航" })).toBeVisible();
  expect(screen.getAllByRole("link", { name: /交付报告/ }).at(-1)).toHaveAttribute(
    "href",
    "/delivery-report?merchant=m1",
  );
});

it("marks the journey step that matches the current page", async () => {
  navigation.pathname = "/platform-audits";
  navigation.merchant = "m1";
  render(<AppShell><p>内容</p></AppShell>);

  const progress = await screen.findByLabelText("商家提升进度");
  const audit = within(progress).getByRole("link", { name: /平台查缺/ });
  const mobile = within(progress).getByRole("link", { name: /手机实测/ });

  expect(audit).toHaveAttribute("aria-current", "step");
  expect(audit.closest("li")).toHaveClass("journey-current");
  expect(mobile).not.toHaveAttribute("aria-current");
});

it("uses the mobile-check hash to distinguish action from retest", async () => {
  navigation.pathname = "/mobile-checks";
  navigation.merchant = "m1";
  window.history.replaceState({}, "", "/mobile-checks?merchant=m1#improvement-playbook");
  render(<AppShell><p>内容</p></AppShell>);

  const progress = await screen.findByLabelText("商家提升进度");
  expect(within(progress).getByRole("link", { name: /执行优化/ })).toHaveAttribute("aria-current", "step");
  expect(within(progress).getByRole("link", { name: /手机实测/ })).not.toHaveAttribute("aria-current");
  expect(within(progress).getByRole("link", { name: /同题复测/ })).not.toHaveAttribute("aria-current");

  window.history.replaceState({}, "", "/mobile-checks?merchant=m1#retest-comparison");
  fireEvent(window, new HashChangeEvent("hashchange"));
  expect(within(progress).getByRole("link", { name: /同题复测/ })).toHaveAttribute("aria-current", "step");
  expect(within(progress).getByRole("link", { name: /执行优化/ })).not.toHaveAttribute("aria-current");
});
