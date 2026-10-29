import { createServer } from "node:http";
import { readFile, writeFile, mkdir, stat } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { officialHistory, mergeDraws, officialUrl } from "./provider.ts";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const port = Number(process.env.PORT || 3001);
const host = process.env.HOST || "127.0.0.1";
const cacheDir = path.resolve(root, ".cache");
let snapshot = null;
try {
  const cached = JSON.parse(
    await readFile(path.join(cacheDir, "history.json"), "utf8"),
  );
  if (Array.isArray(cached.draws) && cached.draws.length) snapshot = cached;
} catch {}
const tasks = new Map();
function json(res, status, body) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  res.end(JSON.stringify(body));
}
const server = createServer(async (req, res) => {
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Referrer-Policy", "same-origin");
  if (req.method !== "GET") {
    json(res, 405, { error: "仅支持GET请求" });
    return;
  }
  let url;
  try {
    const target = req.url || "/";
    if (!target.startsWith("/") || target.startsWith("//"))
      throw new Error("Invalid target");
    url = new URL(target, "http://localhost");
  } catch {
    json(res, 400, { error: "无效请求地址" });
    return;
  }
  if (url.pathname === "/api/health") {
    json(res, 200, { ok: true, service: "pl5" });
    return;
  }
  if (url.pathname === "/api/history") {
    const pages = Number(url.searchParams.get("pages") || 2);
    if (!Number.isInteger(pages) || pages < 1 || pages > 20) {
      json(res, 400, { error: "pages须为1–20的整数" });
      return;
    }
    try {
      let task = tasks.get(pages);
      if (!task) {
        task = officialHistory(pages)
          .then(async (draws) => {
            const combined = mergeDraws([...(snapshot?.draws || []), ...draws]);
            const data = {
              draws: combined,
              source: "中国体育彩票官方历史接口",
              sourceUrl: officialUrl,
              updatedAt: new Date().toISOString(),
              version: createHash("sha256")
                .update(JSON.stringify(combined))
                .digest("hex")
                .slice(0, 16),
              stale: false,
            };
            await mkdir(cacheDir, { recursive: true });
            await writeFile(
              path.join(cacheDir, "history.json"),
              JSON.stringify(data),
            );
            snapshot = data;
            return data;
          })
          .finally(() => tasks.delete(pages));
        tasks.set(pages, task);
      }
      json(res, 200, await task);
    } catch (error) {
      if (snapshot)
        json(res, 200, {
          ...snapshot,
          stale: true,
          warning:
            "更新失败，正在使用上次成功获取的缓存：" +
            (error instanceof Error ? error.message : "网络错误"),
        });
      else
        json(res, 502, {
          error:
            "历史数据更新失败：" +
            (error instanceof Error ? error.message : "网络错误"),
        });
    }
    return;
  }
  try {
    let pathname = decodeURIComponent(url.pathname);
    if (pathname.includes("\0") || pathname.split("/").includes("..")) {
      json(res, 400, { error: "无效路径" });
      return;
    }
    if (["/", "/workbench", "/history", "/plans", "/help"].includes(pathname))
      pathname = "/index.html";
    const dist = path.resolve(root, "dist"),
      target = path.resolve(dist, "." + pathname);
    if (!target.startsWith(dist + path.sep)) {
      json(res, 404, { error: "Not found" });
      return;
    }
    if (!(await stat(target)).isFile()) throw new Error("not file");
    const ext = path.extname(target);
    const types = {
      ".html": "text/html; charset=utf-8",
      ".js": "text/javascript; charset=utf-8",
      ".css": "text/css; charset=utf-8",
      ".svg": "image/svg+xml",
      ".json": "application/json; charset=utf-8",
      ".png": "image/png",
    };
    res.writeHead(200, {
      "Content-Type": types[ext] || "application/octet-stream",
      "Cache-Control":
        ext === ".html" ? "no-cache" : "public, max-age=31536000, immutable",
    });
    res.end(await readFile(target));
  } catch {
    json(res, 404, { error: "资源不存在，请先运行 pnpm build" });
  }
});
server.listen(port, host, () =>
  console.log(`PL5 server: http://${host}:${port}`),
);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => server.close(() => process.exit(0)));
