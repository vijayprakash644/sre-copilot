import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    BACKEND_URL: process.env.BACKEND_URL ?? "http://localhost:8000",
    API_KEY: process.env.API_KEY ?? "",
  },
  async rewrites() {
    return [];
  },
};

export default nextConfig;
