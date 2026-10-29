import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
const options = {
  stdio: "inherit",
  cwd: fileURLToPath(new URL("..", import.meta.url)),
};
const backend = spawn(process.execPath, ["server/index.mjs"], options);
const frontend = spawn(
  process.execPath,
  ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1"],
  options,
);
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  backend.kill("SIGTERM");
  frontend.kill("SIGTERM");
  process.exitCode = code;
}
backend.on("exit", (code) => stop(code ?? 0));
frontend.on("exit", (code) => stop(code ?? 0));
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
