export type AccessRole = "admin" | "demo";

export const ACCESS_SESSION_COOKIE = "access_session";

export function isAccessRole(value: unknown): value is AccessRole {
  return value === "admin" || value === "demo";
}
