import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import LoginPage from "@/app/login/page";

it("presents a focused split-screen brand and login experience", async () => {
  render(await LoginPage({ searchParams: Promise.resolve({}) }));

  expect(screen.getByRole("complementary", { name: "见序品牌" })).toBeVisible();
  expect(screen.getByText("理解商家在 AI 推荐中的呈现方式")).toBeVisible();
  expect(screen.getByRole("heading", { name: "进入见序工作台" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "管理员" })).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "演示访客" })).not.toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "用户名" })).toBeVisible();
  expect(screen.getByLabelText("密码")).toBeVisible();
  expect(screen.getByRole("button", { name: "登录" })).toBeVisible();
});
