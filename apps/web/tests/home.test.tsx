import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import Home from "@/app/page";
import { getMerchants } from "@/lib/api";

vi.mock("@/lib/api", () => ({ getMerchants: vi.fn(), getDashboard: vi.fn() }));


it("introduces the merchant exposure workspace", async () => {
  vi.mocked(getMerchants).mockResolvedValue([]);
  render(await Home({}));

  expect(screen.getByRole("heading", { name: "创建第一个商家后开始检测" })).toBeVisible();
  expect(screen.getByRole("link", { name: "创建商家" })).toBeVisible();
});
