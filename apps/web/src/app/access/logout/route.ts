import { type NextRequest, NextResponse } from "next/server";

import { ACCESS_SESSION_COOKIE } from "@/lib/access-role";
import { publicRequestUrl } from "@/lib/public-request-url";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const response = NextResponse.redirect(publicRequestUrl(request, "/login"), 303);
  response.cookies.delete(ACCESS_SESSION_COOKIE);
  return response;
}
