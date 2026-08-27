import type { Metadata } from "next";
import { headers } from "next/headers";
import type { ReactNode } from "react";

import { AccessRoleProvider } from "@/components/access-role-provider";
import { isAccessRole } from "@/lib/access-role";

import "../styles/globals.css";

export const metadata: Metadata = {
  title: "见序 · Visibility Dossier",
  description: "证据可追溯的公开信息检测工作台",
};

export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const requestHeaders = await headers();
  const headerRole = requestHeaders.get("x-access-role");
  const role = isAccessRole(headerRole) ? headerRole : "admin";
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body data-access-role={role}>
        <AccessRoleProvider role={role}>{children}</AccessRoleProvider>
      </body>
    </html>
  );
}
