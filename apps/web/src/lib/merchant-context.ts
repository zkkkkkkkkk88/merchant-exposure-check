export const MERCHANT_CONTEXT_COOKIE = "merchant_context";

const scopedRoutes = [
  "/platform-audits",
  "/queries",
  "/mobile-checks",
  "/scans",
  "/history",
  "/delivery-report",
  "/actions",
  "/competitors",
];

export function merchantScopedPath(pathname: string): boolean {
  return scopedRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

export function merchantContextRedirect(url: URL, merchantId?: string): URL | null {
  if (!merchantId || !merchantScopedPath(url.pathname) || url.searchParams.has("merchant")) {
    return null;
  }
  const redirectUrl = new URL(url);
  redirectUrl.searchParams.set("merchant", merchantId);
  return redirectUrl;
}

export function pathWithMerchant(pathname: string, search: string, merchantId: string): string {
  const params = new URLSearchParams(search);
  params.set("merchant", merchantId);
  const query = params.toString();
  return `${pathname}${query ? `?${query}` : ""}`;
}

export function persistMerchantContext(merchantId: string): void {
  if (typeof document === "undefined" || !merchantId) return;
  document.cookie = `${MERCHANT_CONTEXT_COOKIE}=${encodeURIComponent(merchantId)}; Path=/; Max-Age=31536000; SameSite=Lax`;
}
