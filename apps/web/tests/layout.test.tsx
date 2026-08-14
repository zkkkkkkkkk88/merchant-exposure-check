import { expect, it } from "vitest";

import RootLayout from "@/app/layout";

it("tolerates attributes injected into the html element by browser extensions", () => {
  const tree = RootLayout({ children: <main>内容</main> });
  expect(tree.props.suppressHydrationWarning).toBe(true);
});
