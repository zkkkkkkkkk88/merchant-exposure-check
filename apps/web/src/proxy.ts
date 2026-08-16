import { type NextRequest, NextResponse } from "next/server";

import {
  MERCHANT_CONTEXT_COOKIE,
  merchantContextRedirect,
} from "@/lib/merchant-context";

export function proxy(request: NextRequest) {
  const merchantId = request.cookies.get(MERCHANT_CONTEXT_COOKIE)?.value;
  const redirectUrl = merchantContextRedirect(request.nextUrl, merchantId);
  return redirectUrl ? NextResponse.redirect(redirectUrl) : NextResponse.next();
}

export const config = {
  matcher: [
    "/platform-audits",
    "/queries",
    "/mobile-checks",
    "/scans/:path*",
    "/history",
    "/delivery-report",
    "/actions",
    "/competitors",
  ],
};
