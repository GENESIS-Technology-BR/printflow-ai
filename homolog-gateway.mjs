import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";

const root = path.resolve("frontend/dist");
const upstream = "https://talvoa-supritech-homolog-api.onrender.com";
const mime = { ".html":"text/html; charset=utf-8", ".js":"text/javascript; charset=utf-8", ".css":"text/css; charset=utf-8", ".svg":"image/svg+xml", ".png":"image/png", ".ico":"image/x-icon", ".json":"application/json" };
const port = Number(process.env.PORT || 10000);

http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", "http://localhost");
    if (url.pathname === "/health") {
      res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      res.end(JSON.stringify({ status: "healthy", component: "gateway" }));
      return;
    }
    if (url.pathname.startsWith("/api/")) {
      const headers = new Headers();
      for (const [name, value] of Object.entries(req.headers)) {
        if (!value || ["host","connection","content-length","transfer-encoding","accept-encoding","origin","referer","cookie"].includes(name)) continue;
        headers.set(name, Array.isArray(value) ? value.join(", ") : value);
      }
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      const body = Buffer.concat(chunks);
      headers.set("origin", upstream);
      // Forward the session cookie explicitly to the API.
      if (req.headers.cookie) headers.set("cookie", req.headers.cookie);
      const response = await fetch(upstream + url.pathname + url.search, {
        method: req.method, headers, body: ["GET","HEAD"].includes(req.method) ? undefined : body,
        redirect: "manual", signal: AbortSignal.timeout(25000),
      });
      console.info(JSON.stringify({ method: req.method, path: url.pathname, upstreamStatus: response.status }));
      if ([502, 503, 504].includes(response.status)) {
        res.writeHead(503, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "Retry-After": "30" });
        res.end(JSON.stringify({ detail: "A homologação está despertando após um período de inatividade. Aguarde cerca de um minuto e tente novamente." }));
        return;
      }
      res.statusCode = response.status;
      if ([502, 503, 504].includes(response.status)) {
        res.setHeader("Retry-After", "30");
        res.setHeader("Cache-Control", "no-store");
      }
      for (const [name, value] of response.headers) {
        if (["content-length","content-encoding","transfer-encoding","connection","set-cookie","access-control-allow-origin","access-control-allow-credentials"].includes(name)) continue;
        res.setHeader(name, value);
      }
      const cookies = response.headers.getSetCookie();
      if (cookies.length) res.setHeader("Set-Cookie", cookies.map(cookie => cookie.replace(/;\s*Domain=[^;]*/ig, "")));
      res.end(Buffer.from(await response.arrayBuffer()));
      return;
    }
    const requested = path.resolve(root, "." + decodeURIComponent(url.pathname));
    if (!requested.startsWith(root + path.sep) && requested !== root) { res.writeHead(403); res.end(); return; }
    let file = requested;
    try { if (!(await stat(file)).isFile()) file = path.join(root, "index.html"); }
    catch { file = path.join(root, "index.html"); }
    const data = await readFile(file);
    res.setHeader("Content-Type", mime[path.extname(file)] || "application/octet-stream");
    res.setHeader("Cache-Control", file.endsWith("index.html") ? "no-store" : "public, max-age=3600");
    res.end(data);
  } catch (error) {
    console.error(JSON.stringify({ event: "gateway_upstream_failure", errorType: error?.name || "unknown" }));
    res.writeHead(503, {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      "Retry-After": "30",
    });
    res.end(JSON.stringify({ detail: "Serviço temporariamente indisponível. Aguarde alguns instantes e tente novamente." }));
  }
}).listen(port, "0.0.0.0");
