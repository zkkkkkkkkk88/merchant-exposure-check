import { headers } from "next/headers";

import { isAccessRole, type AccessRole } from "./access-role";

export class AccessAuthenticationError extends Error {
  constructor() {
    super("访问身份无效，请重新登录。");
    this.name = "AccessAuthenticationError";
  }
}

export class DemoReadOnlyError extends Error {
  constructor() {
    super("当前为演示权限，实际操作请联系管理员。");
    this.name = "DemoReadOnlyError";
  }
}

export async function getServerAccessRole(): Promise<AccessRole> {
  const role = (await headers()).get("x-access-role");
  if (isAccessRole(role)) return role;
  if (process.env.ACCESS_AUTH_REQUIRED !== "true") return "admin";
  throw new AccessAuthenticationError();
}

export async function requireServerAdmin(): Promise<void> {
  if (await getServerAccessRole() === "demo") throw new DemoReadOnlyError();
}

export async function trustedApiHeaders(init?: HeadersInit): Promise<Headers> {
  const result = new Headers(init);
  let role: AccessRole;
  try {
    role = await getServerAccessRole();
  } catch (error) {
    if (process.env.ACCESS_AUTH_REQUIRED === "true") throw error;
    role = "admin";
  }
  result.set("X-Access-Role", role);
  result.set("X-Internal-Auth", process.env.INTERNAL_API_SECRET ?? "");
  return result;
}
