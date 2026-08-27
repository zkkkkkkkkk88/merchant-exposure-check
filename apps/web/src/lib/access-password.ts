import crypto from "node:crypto";

const HEX = /^(?:[0-9a-f]{2})+$/i;

export function verifyPassword(password: string, encodedHash: string): boolean {
  const [algorithm, saltHex, hashHex, extra] = encodedHash.split("$");
  if (
    algorithm !== "scrypt"
    || !saltHex
    || !hashHex
    || extra !== undefined
    || !HEX.test(saltHex)
    || !HEX.test(hashHex)
  ) {
    return false;
  }

  try {
    const salt = Buffer.from(saltHex, "hex");
    const expected = Buffer.from(hashHex, "hex");
    const derived = crypto.scryptSync(password, salt, expected.length);
    return derived.length === expected.length && crypto.timingSafeEqual(derived, expected);
  } catch {
    return false;
  }
}
