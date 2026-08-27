import { type NextRequest, NextResponse } from "next/server";

import { ACCESS_SESSION_COOKIE, type AccessRole } from "@/lib/access-role";
import { verifyAccessSession } from "@/lib/access-session";
import {
  MERCHANT_CONTEXT_COOKIE,
  merchantContextRedirect,
} from "@/lib/merchant-context";

type AccessDecision =
  | { action: "public" }
  | { action: "login" }
  | { action: "allow"; role: AccessRole };

function isPublicAccessRequest(
  pathname: string,
  method: string,
  hasServerAction: boolean,
): boolean {
  if (hasServerAction) return false;
  if (pathname === "/login" || pathname === "/login/") {
    return method === "GET" || method === "HEAD";
  }
  return pathname === "/access/login"
    || pathname.startsWith("/_next/static/")
    || pathname === "/_next/image"
    || pathname === "/favicon.ico";
}

export function accessDecisionForPath(
  pathname: string,
  authRequired: boolean,
  sessionRole: AccessRole | null,
  method = "GET",
  hasServerAction = false,
): AccessDecision {
  if (isPublicAccessRequest(pathname, method, hasServerAction)) return { action: "public" };
  if (!authRequired) return { action: "allow", role: "admin" };
  if (!sessionRole) return { action: "login" };
  return { action: "allow", role: sessionRole };
}

function continueWithRole(request: NextRequest, role?: AccessRole): NextResponse {
  const requestHeaders = new Headers(request.headers);
  requestHeaders.delete("x-access-role");
  if (role) requestHeaders.set("x-access-role", role);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const authRequired = process.env.ACCESS_AUTH_REQUIRED === "true";
  const hasServerAction = request.headers.has("next-action");
  if (isPublicAccessRequest(pathname, request.method, hasServerAction)) {
    return continueWithRole(request);
  }

  let role: AccessRole | null = null;
  if (authRequired) {
    const session = request.cookies.get(ACCESS_SESSION_COOKIE)?.value;
    const secret = process.env.ACCESS_SESSION_SECRET;
    if (session && secret) role = await verifyAccessSession(session, secret);
  }

  const decision = accessDecisionForPath(
    pathname,
    authRequired,
    role,
    request.method,
    hasServerAction,
  );
  if (decision.action === "login") {
    return NextResponse.redirect(new URL("/login", request.url), 303);
  }

  const merchantId = request.cookies.get(MERCHANT_CONTEXT_COOKIE)?.value;
  const redirectUrl = merchantContextRedirect(request.nextUrl, merchantId);
  if (redirectUrl) return NextResponse.redirect(redirectUrl);

  return continueWithRole(request, decision.action === "allow" ? decision.role : undefined);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
