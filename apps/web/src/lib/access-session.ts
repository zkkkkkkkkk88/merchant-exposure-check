import { isAccessRole, type AccessRole } from "@/lib/access-role";

type AccessSessionPayload = {
  role: AccessRole;
  expiresAt: number;
};

export const ACCESS_SESSION_MAX_AGE_SECONDS = 12 * 60 * 60;

const encoder = new TextEncoder();

function toBase64Url(value: Uint8Array): string {
  return btoa(String.fromCharCode(...value))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}

function fromBase64Url(value: string): Uint8Array<ArrayBuffer> {
  const base64 = value.replaceAll("-", "+").replaceAll("_", "/");
  const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

export async function createAccessSession(
  role: AccessRole,
  secret: string,
  now = Date.now(),
): Promise<string> {
  const payload: AccessSessionPayload = {
    role,
    expiresAt: now + ACCESS_SESSION_MAX_AGE_SECONDS * 1_000,
  };
  const encodedPayload = toBase64Url(encoder.encode(JSON.stringify(payload)));
  const signature = await crypto.subtle.sign(
    "HMAC",
    await hmacKey(secret),
    encoder.encode(encodedPayload),
  );

  return `${encodedPayload}.${toBase64Url(new Uint8Array(signature))}`;
}

export async function verifyAccessSession(
  value: string,
  secret: string,
  now = Date.now(),
): Promise<AccessRole | null> {
  const parts = value.split(".");
  if (parts.length !== 2 || !parts[0] || !parts[1] || !secret) return null;

  const [encodedPayload, encodedSignature] = parts;

  try {
    const validSignature = await crypto.subtle.verify(
      "HMAC",
      await hmacKey(secret),
      fromBase64Url(encodedSignature),
      encoder.encode(encodedPayload),
    );
    if (!validSignature) return null;

    const payload = JSON.parse(
      new TextDecoder().decode(fromBase64Url(encodedPayload)),
    ) as Partial<AccessSessionPayload>;
    if (
      !isAccessRole(payload.role)
      || typeof payload.expiresAt !== "number"
      || !Number.isFinite(payload.expiresAt)
      || payload.expiresAt <= now
    ) {
      return null;
    }

    return payload.role;
  } catch {
    return null;
  }
}
