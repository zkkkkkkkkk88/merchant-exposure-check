import { type NextRequest, NextResponse } from "next/server";

import type { AccessRole } from "@/lib/access-role";
import { ACCESS_SESSION_COOKIE } from "@/lib/access-role";
import { verifyPassword } from "@/lib/access-password";
import {
  ACCESS_SESSION_MAX_AGE_SECONDS,
  createAccessSession,
} from "@/lib/access-session";

type Credential = {
  role: AccessRole;
  username?: string;
  passwordHash?: string;
};

function invalidLogin(request: NextRequest): NextResponse {
  return NextResponse.redirect(new URL("/login?error=invalid", request.url), 303);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  let username: string;
  let password: string;
  try {
    const form = await request.formData();
    const submittedUsername = form.get("username");
    const submittedPassword = form.get("password");
    if (typeof submittedUsername !== "string" || typeof submittedPassword !== "string") {
      return invalidLogin(request);
    }
    username = submittedUsername;
    password = submittedPassword;
  } catch {
    return invalidLogin(request);
  }

  const credentials: Credential[] = [
    {
      role: "admin",
      username: process.env.ACCESS_ADMIN_USERNAME,
      passwordHash: process.env.ACCESS_ADMIN_PASSWORD_HASH,
    },
    {
      role: "demo",
      username: process.env.ACCESS_DEMO_USERNAME,
      passwordHash: process.env.ACCESS_DEMO_PASSWORD_HASH,
    },
  ];
  const credential = credentials.find((candidate) => (
    candidate.username
    && candidate.passwordHash
    && username === candidate.username
    && verifyPassword(password, candidate.passwordHash)
  ));
  const secret = process.env.ACCESS_SESSION_SECRET;
  if (!credential || !secret) return invalidLogin(request);

  const session = await createAccessSession(credential.role, secret);
  const response = NextResponse.redirect(new URL("/", request.url), 303);
  response.cookies.set({
    name: ACCESS_SESSION_COOKIE,
    value: session,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: ACCESS_SESSION_MAX_AGE_SECONDS,
  });
  return response;
}
