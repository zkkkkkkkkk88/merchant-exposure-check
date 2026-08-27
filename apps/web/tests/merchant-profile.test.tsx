import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { ProfileEditor } from "@/components/profile-editor";
import {
  parseProfileAction,
  saveProfileAction,
  saveProfileAndGenerateAction,
} from "@/app/merchants/[id]/actions";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh: vi.fn() }),
}));

vi.mock("@/app/merchants/[id]/actions", () => ({
  parseProfileAction: vi.fn(),
  saveProfileAction: vi.fn(),
  saveProfileAndGenerateAction: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(parseProfileAction).mockResolvedValue({
    ok: true,
    data: {
      merchant_id: "m1",
      facts: [
        { field_key: "location.city", value: "杭州", confirmation_status: "pending", confidence: 0.99, source_urls: [] },
        { field_key: "category.precise", value: "西餐厅", confirmation_status: "pending", confidence: 0.95, source_urls: [] },
        { field_key: "price.display", value: "双人餐 300–450 元", confirmation_status: "pending", confidence: 0.96, source_urls: [] },
        { field_key: "service.baby_chair", value: true, confirmation_status: "pending", confidence: 0.9, source_urls: [] },
      ],
    },
  });
  vi.mocked(saveProfileAction).mockImplementation(async (_id, facts) => ({
    ok: true,
    data: { merchant_id: "m1", facts },
  }));
  vi.mocked(saveProfileAndGenerateAction).mockResolvedValue({ ok: true, data: { id: "set2" } });
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

  fireEvent.click(screen.getByRole("checkbox", { name: "确认 省份 / 城市" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "确认 精准品类" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "确认 价格区间" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "确认 宝宝椅" }));
  fireEvent.click(screen.getByRole("button", { name: "保存并生成精准问题" }));

  await waitFor(() => expect(saveProfileAndGenerateAction).toHaveBeenCalledWith("m1", expect.any(Array)));
  expect(push).toHaveBeenCalledWith("/queries?merchant=m1");
});

it("adds an editable precise category when an imported merchant only has a legacy industry", () => {
  render(<ProfileEditor initialProfile={{
    merchant_id: "m1",
    facts: [
      { field_key: "location.city", value: "云南", confirmation_status: "pending", confidence: 1, source_urls: [] },
      { field_key: "category.legacy", value: "口腔医疗机构", confirmation_status: "pending", confidence: 1, source_urls: [] },
    ],
  }} merchantId="m1" />);

  expect(screen.getByRole("checkbox", { name: "确认 精准品类" })).toBeEnabled();
  expect(screen.getByRole("textbox", { name: "编辑 精准品类" })).toHaveValue("口腔医疗机构");
  expect(screen.getByText("请确认城市和精准品类后再生成问题。")).toBeVisible();
});

it("saves edited profile facts without generating a new query set", async () => {
  render(<ProfileEditor initialProfile={{
    merchant_id: "m1",
    facts: [
      { field_key: "location.city", value: "云南", confirmation_status: "confirmed", confidence: 1, source_urls: [] },
      { field_key: "category.precise", value: "口腔医疗机构", confirmation_status: "confirmed", confidence: 1, source_urls: [] },
    ],
  }} merchantId="m1" />);

  fireEvent.change(screen.getByRole("textbox", { name: "编辑 精准品类" }), {
    target: { value: "口腔门诊" },
  });
  fireEvent.click(screen.getByRole("button", { name: "仅保存修改" }));

  await waitFor(() => expect(saveProfileAction).toHaveBeenCalledWith(
    "m1",
    expect.arrayContaining([expect.objectContaining({ field_key: "category.precise", value: "口腔门诊" })]),
  ));
  expect(saveProfileAndGenerateAction).not.toHaveBeenCalled();
  expect(await screen.findByText("商家画像已保存。" )).toBeVisible();
});
