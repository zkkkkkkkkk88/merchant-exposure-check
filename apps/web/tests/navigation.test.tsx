import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app-shell";

const navigation = vi.hoisted(() => ({
  pathname: "/merchants/m1",
  back: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => navigation.pathname,
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
});

it("provides a back control on child pages", () => {
  window.history.pushState({}, "", "/previous");
  render(<AppShell><p>内容</p></AppShell>);

  fireEvent.click(screen.getByRole("button", { name: "返回" }));

  expect(navigation.back).toHaveBeenCalledOnce();
});
