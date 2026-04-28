// Custom Next.js server: forwards /api/* to BACKEND_URL at runtime.
// Replaces the standalone-generated server.js in the container, so BACKEND_URL
// is read on container start instead of being baked at `next build` time.
//
// Production must NOT use `require("next")` — that entry pulls
// `next/dist/server/config-utils.js` -> `next/dist/compiled/webpack/webpack.js`,
// which Next.js standalone tracing intentionally omits, so the runtime image
// would crash with `Cannot find module './bundle5'` on container start
// (issue #230). Instead, we mirror the standalone-generated server.js by
// instantiating `next/dist/server/next-server` directly and feeding it the
// inlined config from `.next/required-server-files.json`.
const http = require("http");
const https = require("https");
const path = require("path");
const fs = require("fs");
const { parse } = require("url");

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

async function createNextHandler() {
  if (dev) {
    // Dev: full `next` package is available; webpack et al. are needed anyway.
    const next = require("next");
    const app = next({ dev: true, hostname, port });
    await app.prepare();
    return app.getRequestHandler();
  }
  // Production standalone: use `next-server` directly. Avoids
  // `require("next")` -> webpack chain that's not in the standalone trace.
  const requiredServerFilesPath = path.join(__dirname, ".next", "required-server-files.json");
  const requiredServerFiles = JSON.parse(fs.readFileSync(requiredServerFilesPath, "utf8"));
  process.env.__NEXT_PRIVATE_STANDALONE_CONFIG = JSON.stringify(requiredServerFiles.config);
  process.chdir(__dirname);

  const NextServer = require("next/dist/server/next-server").default;
  const app = new NextServer({
    hostname,
    port,
    dir: __dirname,
    dev: false,
    customServer: false,
    conf: requiredServerFiles.config,
  });
  await app.prepare();
  return app.getRequestHandler();
}

(async () => {
  const handler = await createNextHandler();
  const server = http.createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    if (parsedUrl.pathname && parsedUrl.pathname.startsWith("/api/")) {
      return proxyApi(req, res);
    }
    return handler(req, res, parsedUrl);
  });

  server.keepAliveTimeout = 65_000;
  server.headersTimeout = 66_000;

  server.listen(port, hostname, () => {
    console.log(`> Ready on http://${hostname}:${port}`);
    console.log(`> Proxying /api/* -> ${backendUrl}`);
  });
})().catch((err) => {
  console.error("Fatal: failed to start server:", err);
  process.exit(1);
});
