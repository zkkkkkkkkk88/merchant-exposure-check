import { describe, expect, it } from "vitest";

import nextConfig from "../next.config";

describe("Next.js upload configuration", () => {
  it("allows optional evidence screenshots larger than the framework default", () => {
    expect(nextConfig.experimental?.serverActions?.bodySizeLimit).toBe("10mb");
  });

  it("emits a standalone production server for the runtime image", () => {
    expect(nextConfig.output).toBe("standalone");
  });
});
