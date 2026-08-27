import type { NextConfig } from "next";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    // React 19 features
  },
  async rewrites() {
    // The BFF (`lib/data/*` → `/api/*` route handlers) is the single API
    // surface for request/response calls. The one exception is the SSE run
    // stream (`lib/hooks/useRunStream.ts` → `/api/v1/runs/:id/events`), which
    // needs a direct pass-through to FastAPI — Next route handlers are a poor
    // fit for long-lived streaming responses. This rewrite exists only for that.
    return [
      {
        source: "/api/v1/:path*",
        destination: `${API_URL}/v1/:path*`,
      },
    ];
  },
  webpack: (config, { isServer }) => {
    // Monaco Editor requires these to be handled
    if (!isServer) {
      config.resolve = {
        ...config.resolve,
        fallback: {
          ...config.resolve?.fallback,
          fs: false,
          path: false,
          os: false,
        },
      };
    }
    return config;
  },
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
      },
    ],
  },
};

export default nextConfig;
