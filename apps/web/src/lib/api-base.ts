type ApiEnvironment = Record<string, string | undefined>;

export function resolveServerApiBaseUrl(env: ApiEnvironment = {}): string {
  return env.API_BASE_URL
    ?? env.NEXT_PUBLIC_API_BASE_URL
    ?? "http://127.0.0.1:8000";
}

export function resolvePublicApiBaseUrl(value?: string): string {
  return value ?? "/api";
}
