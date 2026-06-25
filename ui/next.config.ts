import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Pin the workspace root to this dir. Without it, Next infers the root from
  // the nearest lockfile and can pick a stray ~/package-lock.json, sending the
  // build output to the wrong .next and breaking `next start`. (UI-CONFIG-1)
  outputFileTracingRoot: path.join(__dirname),
  trailingSlash: true,
  experimental: {
    optimizePackageImports: ['lucide-react', 'date-fns', 'recharts'],
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000',
  },
};

export default nextConfig;
