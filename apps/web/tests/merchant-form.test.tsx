import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { MerchantForm } from "@/components/merchant-form";

it("validates and submits merchant data matching the API contract", async () => {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  render(<MerchantForm onSubmit={onSubmit} />);

  fireEvent.click(screen.getByRole("button", { name: "保存并生成问题" }));
  expect(await screen.findByText("请填写商家名称、城市和行业")).toBeVisible();

  fireEvent.change(screen.getByLabelText("商家名称"), { target: { value: "O'eat Gastronomy" } });
  fireEvent.change(screen.getByLabelText("城市"), { target: { value: "杭州" } });
  fireEvent.change(screen.getByLabelText("行业"), { target: { value: "餐饮" } });
  fireEvent.change(screen.getByLabelText("公开来源 1（选填）"), { target: { value: "not-a-url" } });
  fireEvent.click(screen.getByRole("button", { name: "保存并生成问题" }));
  expect(await screen.findByText("请输入完整的公开来源网址")).toBeVisible();

  fireEvent.change(screen.getByLabelText("公开来源 1（选填）"), { target: { value: "https://example.com/store" } });
  fireEvent.change(screen.getByLabelText("代表产品"), { target: { value: "季节套餐, 手工甜点" } });
  fireEvent.click(screen.getByRole("button", { name: "保存并生成问题" }));

  await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
    name: "O'eat Gastronomy",
    city: "杭州",
    industry: "餐饮",
    products: ["季节套餐", "手工甜点"],
    sources: [{ kind: "other", url: "https://example.com/store", is_verified: false }],
  }));
});

it("makes clear that the public source can be left empty", () => {
  render(<MerchantForm onSubmit={vi.fn()} />);

  expect(screen.getByRole("textbox", { name: "公开来源 1（选填）" })).toBeVisible();
  expect(screen.getByText(/没有可复制链接时可以留空/)).toBeVisible();
});

it("shows a safe server error", async () => {
  const onSubmit = vi.fn().mockRejectedValue(new Error("保存失败，请稍后重试"));
  render(<MerchantForm onSubmit={onSubmit} />);
  fireEvent.change(screen.getByLabelText("商家名称"), { target: { value: "测试店" } });
  fireEvent.change(screen.getByLabelText("城市"), { target: { value: "杭州" } });
  fireEvent.change(screen.getByLabelText("行业"), { target: { value: "餐饮" } });
  fireEvent.click(screen.getByRole("button", { name: "保存并生成问题" }));
  expect(await screen.findByText("保存失败，请稍后重试")).toBeVisible();
});
