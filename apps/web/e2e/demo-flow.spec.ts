import { expect, test } from "@playwright/test";

test("operator can inspect a completed evidence report", async ({ page, request }) => {
  const merchants = await (await request.get("http://127.0.0.1:8000/merchants")).json();
  const merchant = merchants.find((item: { name: string }) => item.name === "O'eat Gastronomy");
  const runs = await (
    await request.get(`http://127.0.0.1:8000/scan-runs/merchant/${merchant.id}/runs`)
  ).json();

  await page.goto(`/?merchant=${merchant.id}`);
  await expect(page.getByRole("heading", { name: "O'eat Gastronomy" })).toBeVisible();
  await expect(page.getByText("品牌出现率")).toBeVisible();
  await expect(
    page.getByText("品牌出现率").locator("..").getByText("40%", { exact: true }),
  ).toBeVisible();

  await page.goto(`/scans/${runs[0].id}`);
  await page.getByRole("button", { name: "查看原始证据" }).first().click();
  await expect(page.getByRole("complementary", { name: "原始证据" })).toBeVisible();

  await page.goto(`/reports/${runs[0].id}`);
  await expect(page.getByText(/不承诺控制豆包内部排名/)).toBeVisible();
});
