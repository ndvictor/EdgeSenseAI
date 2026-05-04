import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const appDir = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  turbopack: {
    root: appDir,
    resolveAlias: {
      tailwindcss: path.join(appDir, "node_modules/tailwindcss"),
    },
  },
  webpack: (config) => {
    config.resolve ??= {};
    config.resolve.alias ??= {};
    config.resolve.modules ??= [];

    config.resolve.alias.tailwindcss = path.join(appDir, "node_modules/tailwindcss");
    config.resolve.modules = [
      path.join(appDir, "node_modules"),
      ...config.resolve.modules,
    ];

    return config;
  },
  experimental: {
    // This helps with Tailwind in newer versions
  },
};

export default nextConfig;
