"use client";

import { useRouter } from "next/navigation";

export function BackLink({ fallbackHref }: { fallbackHref: string }) {
  const router = useRouter();
  return (
    <button
      aria-label="返回"
      className="back-link"
      onClick={() => router.push(fallbackHref)}
      type="button"
    >
      <span aria-hidden="true">←</span> 返回
    </button>
  );
}
