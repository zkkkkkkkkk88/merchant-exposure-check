import { expect, it, vi } from "vitest";

import RootLayout from "@/app/layout";

const requestHeaders = vi.hoisted(() => ({ current: new Headers() }));
vi.mock("next/headers", () => ({ headers: vi.fn(() => Promise.resolve(requestHeaders.current)) }));

it("tolerates attributes injected into the html element by browser extensions", async () => {
  const tree = await RootLayout({ children: <main>内容</main> });
  expect(tree.props.suppressHydrationWarning).toBe(true);
});

it("passes the request access role to the document and provider", async () => {
  requestHeaders.current = new Headers({ "x-access-role": "demo" });
  const tree = await RootLayout({ children: <main>内容</main> });
  expect(tree.props.children.props["data-access-role"]).toBe("demo");
  expect(tree.props.children.props.children.props.role).toBe("demo");
});
