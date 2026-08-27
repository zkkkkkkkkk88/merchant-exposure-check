"use client";

import { createContext, useContext, type ReactNode } from "react";

import type { AccessRole } from "@/lib/access-role";

const AccessRoleContext = createContext<AccessRole>("admin");

export function AccessRoleProvider({ role, children }: { role: AccessRole; children: ReactNode }) {
  return <AccessRoleContext.Provider value={role}>{children}</AccessRoleContext.Provider>;
}

export function useAccessRole(): AccessRole {
  return useContext(AccessRoleContext);
}
