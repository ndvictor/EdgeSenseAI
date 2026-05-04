import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: process.cwd(),
  },
  experimental: {
    // This helps with Tailwind in newer versions
  },
};

export default nextConfig;
