import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    agentUpgrade: "security",
  },
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: "http://127.0.0.1:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
