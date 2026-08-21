import { describe, expect, it } from "vitest";

import { resolvePublicApiBaseUrl, resolveServerApiBaseUrl } from "@/lib/api-base";

describe("API base URL selection", () => {
  it("prefers the private server API address", () => {
    expect(resolveServerApiBaseUrl({
      API_BASE_URL: "http://api:8000",
      NEXT_PUBLIC_API_BASE_URL: "https://public.invalid/api",
    })).toBe("http://api:8000");
  });

  it("preserves the existing local development fallback", () => {
    expect(resolveServerApiBaseUrl({})).toBe("http://127.0.0.1:8000");
  });

  it("uses the same-origin API route in the browser by default", () => {
    expect(resolvePublicApiBaseUrl()).toBe("/api");
    expect(resolvePublicApiBaseUrl("http://127.0.0.1:8000")).toBe(
      "http://127.0.0.1:8000",
    );
  });
});
