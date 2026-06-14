import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  trailingSlash: true,
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000',
  },
};

export default nextConfig;
