import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

import { beforeEach, describe, expect, it, vi } from "vitest";

const timingSafeEqual = vi.hoisted(() => vi.fn((left: Buffer, right: Buffer) => (
  left.length === right.length && left.equals(right)
)));

vi.mock("node:crypto", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:crypto")>();
  return {
    ...actual,
    default: { ...actual, timingSafeEqual },
    timingSafeEqual,
  };
});

import { verifyPassword } from "@/lib/access-password";

const TEST_HASH = "scrypt$00112233445566778899aabbccddeeff$99f5251cf1506e7f2387aa6c3eea5395a235801b1834e4e0e75e6bdb8531c832bc4e491e4735a8b4f8e550f31d966c9e622e9372ebf3d834e7ba9aa41c3de332";

describe("access password verification", () => {
  beforeEach(() => {
    timingSafeEqual.mockClear();
  });

  it("accepts the checked-in demo password hash", () => {
    expect(verifyPassword("演示密码-123", TEST_HASH)).toBe(true);
  });

  it("rejects a different password", () => {
    expect(verifyPassword("错误密码", TEST_HASH)).toBe(false);
  });

  it("uses a timing-safe comparison for equal-length hashes", () => {
    verifyPassword("演示密码-123", TEST_HASH);

    expect(timingSafeEqual).toHaveBeenCalledOnce();
    const [derived, expected] = timingSafeEqual.mock.calls[0];
    expect(derived).toHaveLength(expected.length);
  });

  it("generates a verifiable scrypt hash from stdin without echoing the password", () => {
    const script = resolve(process.cwd(), "scripts/hash-access-password.mjs");
    const result = spawnSync(process.execPath, [script], {
      encoding: "utf8",
      input: "一次性测试密码\n",
    });

    expect(result.status).toBe(0);
    expect(result.stderr).toBe("");
    expect(result.stdout.trim()).toMatch(/^scrypt\$[0-9a-f]{32}\$[0-9a-f]{128}$/);
    expect(result.stdout).not.toContain("一次性测试密码");
    expect(verifyPassword("一次性测试密码", result.stdout.trim())).toBe(true);
  });
});
