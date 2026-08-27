import { type NextRequest, NextResponse } from "next/server";

import { ACCESS_SESSION_COOKIE } from "@/lib/access-role";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const response = NextResponse.redirect(new URL("/login", request.url), 303);
  response.cookies.delete(ACCESS_SESSION_COOKIE);
  return response;
}
