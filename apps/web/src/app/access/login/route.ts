import { type NextRequest, NextResponse } from "next/server";

import type { AccessRole } from "@/lib/access-role";
import { ACCESS_SESSION_COOKIE } from "@/lib/access-role";
import { verifyPassword } from "@/lib/access-password";
import {
  ACCESS_SESSION_MAX_AGE_SECONDS,
  createAccessSession,
} from "@/lib/access-session";
import { publicRequestUrl } from "@/lib/public-request-url";

type Credential = {
  role: AccessRole;
  username?: string;
  passwordHash?: string;
};

const DUMMY_PASSWORD_HASH = `scrypt$${"00".repeat(16)}$${"00".repeat(64)}`;

function invalidLogin(request: NextRequest): NextResponse {
  return NextResponse.redirect(publicRequestUrl(request, "/login?error=invalid"), 303);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  let username = "";
  let password = "";
  let validForm = false;
  try {
    const form = await request.formData();
    const submittedUsername = form.get("username");
    const submittedPassword = form.get("password");
    if (typeof submittedUsername === "string" && typeof submittedPassword === "string") {
      username = submittedUsername;
      password = submittedPassword;
      validForm = true;
    }
  } catch {}

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
    candidate.username && username === candidate.username
  ));
  const passwordMatches = verifyPassword(
    password,
    credential?.passwordHash ?? DUMMY_PASSWORD_HASH,
  );
  const secret = process.env.ACCESS_SESSION_SECRET;
  if (!validForm || !credential?.passwordHash || !passwordMatches || !secret) {
    return invalidLogin(request);
  }

  const session = await createAccessSession(credential.role, secret);
  const response = NextResponse.redirect(publicRequestUrl(request, "/"), 303);
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
