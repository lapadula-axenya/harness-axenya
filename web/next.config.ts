import type { NextConfig } from "next";

const apiBase = process.env.XENIA_API_URL ?? "http://localhost:8080";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/xenia/:path*", destination: `${apiBase}/:path*` },
    ];
  },
};

export default nextConfig;
