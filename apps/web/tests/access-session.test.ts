import { describe, expect, it } from "vitest";

import {
  createAccessSession,
  verifyAccessSession,
} from "@/lib/access-session";

const SECRET = "test-session-secret";
const NOW = 1_700_000_000_000;

describe("access sessions", () => {
  it("creates a deterministic signed admin session that verifies as admin", async () => {
    const session = await createAccessSession("admin", SECRET, NOW);

    expect(session).toBe(
      "eyJyb2xlIjoiYWRtaW4iLCJleHBpcmVzQXQiOjE3MDAwNDMyMDAwMDB9.3KNHwOCZZkEt6F27ZDEgs1oa-Oih9BaPcaLVpt47lVQ",
    );
    await expect(verifyAccessSession(session, SECRET, NOW)).resolves.toBe("admin");
  });

  it("verifies a demo session as demo", async () => {
    const session = await createAccessSession("demo", SECRET, NOW);

    await expect(verifyAccessSession(session, SECRET, NOW)).resolves.toBe("demo");
  });

  it.each(["payload", "signature"])(
    "rejects a session with a changed %s",
    async (part) => {
      const session = await createAccessSession("admin", SECRET, NOW);
      const [payload, signature] = session.split(".");
      const changed = part === "payload"
        ? `${payload.slice(0, -1)}A.${signature}`
        : `${payload}.${signature.slice(0, -1)}A`;

      await expect(verifyAccessSession(changed, SECRET, NOW)).resolves.toBeNull();
    },
  );

  it("rejects an expired session", async () => {
    const session = await createAccessSession("demo", SECRET, NOW);

    await expect(
      verifyAccessSession(session, SECRET, NOW + 12 * 60 * 60 * 1_000 + 1),
    ).resolves.toBeNull();
  });
});
