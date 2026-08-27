import type { NextRequest } from "next/server";

export function publicRequestUrl(request: NextRequest, pathname: string): URL {
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",", 1)[0]?.trim();
  const forwardedProto = request.headers.get("x-forwarded-proto")?.split(",", 1)[0]?.trim();
  if (forwardedHost && (forwardedProto === "http" || forwardedProto === "https")) {
    try {
      return new URL(pathname, `${forwardedProto}://${forwardedHost}`);
    } catch {}
  }
  return new URL(pathname, request.url);
}
