import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { ProfileEditor } from "@/components/profile-editor";
import {
  generateQuerySet,
  parseMerchantProfile,
  replaceMerchantProfile,
} from "@/lib/api";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  parseMerchantProfile: vi.fn(),
  replaceMerchantProfile: vi.fn(),
  generateQuerySet: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(parseMerchantProfile).mockResolvedValue({
    merchant_id: "m1",
    facts: [
      { field_key: "location.city", value: "杭州", confirmation_status: "pending", confidence: 0.99, source_urls: [] },
      { field_key: "category.precise", value: "西餐厅", confirmation_status: "pending", confidence: 0.95, source_urls: [] },
      { field_key: "price.display", value: "双人餐 300–450 元", confirmation_status: "pending", confidence: 0.96, source_urls: [] },
      { field_key: "service.baby_chair", value: true, confirmation_status: "pending", confidence: 0.9, source_urls: [] },
    ],
  });
  vi.mocked(replaceMerchantProfile).mockImplementation(async (_id, facts) => ({ merchant_id: "m1", facts }));
  vi.mocked(generateQuerySet).mockResolvedValue({ id: "set2" });
});

it("parses pasted merchant text and requires confirmation before query generation", async () => {
  render(<ProfileEditor initialProfile={{ merchant_id: "m1", facts: [] }} merchantId="m1" />);

  fireEvent.change(screen.getByLabelText("粘贴商家公开资料"), {
    target: { value: "O'eat 是杭州万象城西餐厅，双人餐300到450元，提供宝宝椅。" },
  });
  fireEvent.click(screen.getByRole("button", { name: "识别资料" }));

  expect(await screen.findByDisplayValue("西餐厅")).toBeVisible();
  expect(screen.getByDisplayValue("双人餐 300–450 元")).toBeVisible();
  expect(screen.getByRole("button", { name: "保存并生成精准问题" })).toBeDisabled();

  fireEvent.click(screen.getByRole("checkbox", { name: "确认 城市" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "确认 精准品类" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "确认 价格区间" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "确认 宝宝椅" }));
  fireEvent.click(screen.getByRole("button", { name: "保存并生成精准问题" }));

  await waitFor(() => expect(replaceMerchantProfile).toHaveBeenCalled());
  expect(generateQuerySet).toHaveBeenCalledWith("m1", 12);
  expect(push).toHaveBeenCalledWith("/queries?merchant=m1");
});

