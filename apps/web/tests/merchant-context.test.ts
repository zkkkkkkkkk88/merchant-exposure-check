import { describe, expect, it } from "vitest";

import {
  merchantContextRedirect,
  pathWithMerchant,
} from "@/lib/merchant-context";

describe("merchant context", () => {
  it("restores the selected merchant on a scoped page and preserves filters", () => {
    expect(merchantContextRedirect(
      new URL("http://localhost/platform-audits?view=missing"),
      "merchant-1",
    )?.toString()).toBe(
      "http://localhost/platform-audits?view=missing&merchant=merchant-1",
    );
  });

  it("does not redirect public pages, explicit merchant URLs, or missing context", () => {
    expect(merchantContextRedirect(new URL("http://localhost/merchants"), "merchant-1")).toBeNull();
    expect(merchantContextRedirect(new URL("http://localhost/mobile-checks?merchant=merchant-2"), "merchant-1")).toBeNull();
    expect(merchantContextRedirect(new URL("http://localhost/delivery-report"), undefined)).toBeNull();
  });

  it("changes only the merchant parameter when switching merchants", () => {
    expect(pathWithMerchant("/queries", "category=geo&merchant=old", "new merchant")).toBe(
      "/queries?category=geo&merchant=new+merchant",
    );
  });
});
