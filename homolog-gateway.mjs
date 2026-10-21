import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";

const root = path.resolve("frontend/dist");
const upstream = "https://talvoa-supritech-homolog-api.onrender.com";
const mime = { ".html":"text/html; charset=utf-8", ".js":"text/javascript; charset=utf-8", ".css":"text/css; charset=utf-8", ".svg":"image/svg+xml", ".png":"image/png", ".ico":"image/x-icon", ".json":"application/json" };
const port = Number(process.env.PORT || 10000);

// Start warming the sleeping Free-tier API as soon as the portal HTML is requested.
// Throttled and non-blocking: never forwards cookies, credentials, or user data.
let lastWarmupAt = 0;
let warmupRunning = false;
function warmUpApi() {
  if (warmupRunning || Date.now() - lastWarmupAt < 45000) return;
  lastWarmupAt = Date.now();
  warmupRunning = true;
  void (async () => {
    try {
      for (let attempt = 1; attempt <= 12; attempt++) {
        try {
          const response = await fetch(upstream + "/health", {
            headers: { Accept: "application/json" },
            signal: AbortSignal.timeout(12000),
          });
          if (response.ok) {
            console.info(JSON.stringify({ event: "api_warmup_ready", attempt }));
            return;
          }
          if (![502, 503, 504].includes(response.status)) {
            console.warn(JSON.stringify({ event: "api_warmup_unexpected_status", status: response.status }));
            return;
          }
        } catch (error) {
          console.warn(JSON.stringify({ event: "api_warmup_attempt_failed", attempt, errorType: error?.name || "unknown" }));
        }
        if (attempt < 12) await new Promise(resolve => setTimeout(resolve, 5000));
      }
      console.warn(JSON.stringify({ event: "api_warmup_timeout" }));
    } catch (error) {
      console.warn(JSON.stringify({ event: "api_warmup_transport_error", errorType: error?.name || "unknown" }));
    } finally {
      warmupRunning = false;
    }
  })();
}

http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", "http://localhost");
    if (url.pathname === "/health") {
      res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      res.end(JSON.stringify({ status: "healthy", component: "gateway" }));
      return;
    }
    if (url.pathname === "/health/upstream") {
      // Explicit, on-demand warm-up. Render Free may need ~60 seconds to wake.
      const started = Date.now();
      let upstreamStatus = null;
      let attempts = 0;
      while (Date.now() - started < 75000 && attempts < 12) {
        attempts++;
        try {
          const response = await fetch(upstream + "/health", {
            signal: AbortSignal.timeout(12000),
            headers: { "Accept": "application/json" },
          });
          upstreamStatus = response.status;
          if (response.ok) {
            res.writeHead(200, { "Content-Type": "application/json", "Cache-Control": "no-store" });
            res.end(JSON.stringify({ status: "healthy", component: "homolog-api", upstream_status: 200, attempts, elapsed_ms: Date.now() - started }));
            return;
          }
          if (![502, 504].includes(response.status)) break;
        } catch (error) {
          console.warn(JSON.stringify({ event: "health_attempt_failed", attempt: attempts, errorType: error?.name || "unknown" }));
        }
        if (Date.now() - started < 65000) await new Promise(resolve => setTimeout(resolve, 5000));
      }
      console.warn(JSON.stringify({ event: "homolog_api_unavailable", upstreamStatus, attempts, elapsedMs: Date.now() - started }));
      res.writeHead(503, { "Content-Type": "application/json", "Cache-Control": "no-store", "Retry-After": "30" });
      res.end(JSON.stringify({ status: "unavailable", component: "homolog-api", upstream_status: upstreamStatus, attempts, elapsed_ms: Date.now() - started }));
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
      const upstreamStarted = Date.now();
      let response;
      try {
        response = await fetch(upstream + url.pathname + url.search, {
        method: req.method, headers, body: ["GET","HEAD"].includes(req.method) ? undefined : body,
        redirect: "manual", signal: AbortSignal.timeout(25000),
        });
      } catch (error) {
        console.warn(JSON.stringify({ event: "proxy_transport_failure", method: req.method, path: url.pathname, elapsedMs: Date.now() - upstreamStarted, errorType: error?.name || "unknown", causeCode: error?.cause?.code || null }));
        throw error;
      }
      console.info(JSON.stringify({ event: "proxy_upstream_response", method: req.method, path: url.pathname, upstreamStatus: response.status, elapsedMs: Date.now() - upstreamStarted }));
      // Retry transient upstream errors for safe reads only.
      // Never replay credential-bearing POST requests.
      if (req.method === "GET" && [502, 503, 504].includes(response.status)) {
        for (let attempt = 1; attempt <= 2; attempt++) {
          await new Promise(resolve => setTimeout(resolve, 2000 * attempt));
          try {
            response = await fetch(upstream + url.pathname + url.search, {
              method: "GET", headers, redirect: "manual",
              signal: AbortSignal.timeout(12000),
            });
            console.info(JSON.stringify({ event: "proxy_safe_retry", path: url.pathname, attempt, upstreamStatus: response.status }));
            if (![502, 503, 504].includes(response.status)) break;
          } catch (error) {
            console.warn(JSON.stringify({ event: "proxy_safe_retry_failed", path: url.pathname, attempt, errorType: error?.name || "unknown" }));
          }
        }
      }
      if ([502, 503, 504].includes(response.status)) {
        res.writeHead(503, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "Retry-After": "30" });
        res.end(JSON.stringify({ detail: "A homologação está despertando após um período de inatividade. Aguarde cerca de um minuto e tente novamente." }));
        return;
      }
      res.statusCode = response.status;
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
    if (file.endsWith("index.html")) warmUpApi();
    const data = await readFile(file);
    res.setHeader("Content-Type", mime[path.extname(file)] || "application/octet-stream");
    // HTML must not be cached; fingerprinted assets may be cached immutably.
    const basename = path.basename(file);
    const isHashedAsset = /\.[a-zA-Z0-9_-]{8,}\.(?:js|css|svg|png|webp|woff2?)$/.test(basename);
    res.setHeader("Cache-Control", file.endsWith("index.html")
      ? "no-store"
      : isHashedAsset ? "public, max-age=31536000, immutable" : "public, max-age=3600");
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
