import type { NextConfig } from "next";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Browser calls go to /api/* on the Next.js origin and are proxied to FastAPI,
  // so the backend's CORS settings don't matter in development.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
  images: { unoptimized: true },
};

export default nextConfig;
