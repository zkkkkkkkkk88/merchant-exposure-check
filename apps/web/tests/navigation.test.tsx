import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

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
  navigation.back.mockReset();
  navigation.push.mockReset();
});

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
