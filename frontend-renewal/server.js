// Custom Next.js server: forwards /api/* to BACKEND_URL at runtime.
// Replaces the standalone-generated server.js in the container, so BACKEND_URL
// is read on container start instead of being baked at `next build` time.
const http = require("http");
const https = require("https");
const { parse } = require("url");
const next = require("next");

const dev = process.env.NODE_ENV !== "production";
const port = parseInt(process.env.PORT || "3100", 10);
const hostname = process.env.HOSTNAME || "0.0.0.0";
const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

let parsedBackend;
try {
  parsedBackend = new URL(backendUrl);
} catch (err) {
  console.error(`Invalid BACKEND_URL=${backendUrl}: ${err.message}`);
  process.exit(1);
}
const backendIsHttps = parsedBackend.protocol === "https:";
const backendPort = parsedBackend.port || (backendIsHttps ? 443 : 80);
const backendLib = backendIsHttps ? https : http;

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

function proxyApi(req, res) {
  const targetPath = req.url;
  const headers = { ...req.headers };
  delete headers.host;

  const proxyReq = backendLib.request(
    {
      hostname: parsedBackend.hostname,
      port: backendPort,
      path: targetPath,
      method: req.method,
      headers,
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );

  proxyReq.on("error", (err) => {
    console.error(`[proxy] ${req.method} ${targetPath} -> ${backendUrl} failed: ${err.message}`);
    if (!res.headersSent) {
      res.writeHead(502, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Bad gateway", target: backendUrl }));
    } else {
      res.end();
    }
  });

  req.on("aborted", () => proxyReq.destroy());
  req.pipe(proxyReq);
}

app.prepare().then(() => {
  const server = http.createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    if (parsedUrl.pathname && parsedUrl.pathname.startsWith("/api/")) {
      return proxyApi(req, res);
    }
    return handle(req, res, parsedUrl);
  });

  server.keepAliveTimeout = 65_000;
  server.headersTimeout = 66_000;

  server.listen(port, hostname, () => {
    console.log(`> Ready on http://${hostname}:${port}`);
    console.log(`> Proxying /api/* -> ${backendUrl}`);
  });
});
