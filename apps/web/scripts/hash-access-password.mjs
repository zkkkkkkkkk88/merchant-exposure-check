import { randomBytes, scryptSync } from "node:crypto";

async function readPassword() {
  if (!process.stdin.isTTY) {
    let password = "";
    process.stdin.setEncoding("utf8");
    for await (const chunk of process.stdin) password += chunk;
    return password.replace(/\r?\n$/, "");
  }

  return new Promise((resolve, reject) => {
    let password = "";
    const restore = () => {
      process.stdin.setRawMode(false);
      process.stdin.pause();
    };

    process.stderr.write("Password: ");
    process.stdin.setEncoding("utf8");
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.on("data", (chunk) => {
      if (chunk === "\u0003") {
        restore();
        reject(new Error("Password entry cancelled"));
        return;
      }
      if (chunk === "\r" || chunk === "\n") {
        restore();
        process.stderr.write("\n");
        resolve(password);
        return;
      }
      if (chunk === "\u0008" || chunk === "\u007f") {
        password = Array.from(password).slice(0, -1).join("");
        return;
      }
      password += chunk;
    });
  });
}

const password = await readPassword();
const salt = randomBytes(16);
const hash = scryptSync(password, salt, 64);
process.stdout.write(`scrypt$${salt.toString("hex")}$${hash.toString("hex")}\n`);
