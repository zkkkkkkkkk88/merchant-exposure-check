import { render, screen } from "@testing-library/react";

import Home from "@/app/page";


it("introduces the merchant exposure workspace", async () => {
  render(await Home({}));

  expect(screen.getByRole("heading", { name: "O'eat Gastronomy" })).toBeVisible();
  expect(screen.getByText("曝光趋势")).toBeVisible();
  expect(screen.getByText("方法说明")).toBeVisible();
});
