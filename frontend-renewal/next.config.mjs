/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    optimizePackageImports: ["recharts", "@remixicon/react", "@tanstack/react-table"],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          ...(process.env.ENABLE_HSTS === "true"
            ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" }]
            : []),
        ],
      },
    ];
  },
  // /api/* is proxied to BACKEND_URL at runtime by ./server.js (Next.js
  // `rewrites()` would otherwise be evaluated at `next build` time and bake
  // BACKEND_URL into the routes manifest, breaking any release whose
  // backend Service hostname differs from the build-time value).
};

export default nextConfig;
