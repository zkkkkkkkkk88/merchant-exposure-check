import { render, screen } from "@testing-library/react";

import Home from "@/app/page";


it("introduces the merchant exposure workspace", () => {
  render(<Home />);

  expect(screen.getByRole("heading", { name: "商家曝光检测" })).toBeVisible();
  expect(screen.getByText("等待创建商家")).toBeVisible();
  expect(screen.getByText("证据可追溯的公开信息检测工作台")).toBeVisible();
});
