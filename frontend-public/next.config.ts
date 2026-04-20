import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  compiler: {
    // Strip dev-only console output at build; keep console.error so
    // the logError indirection in lib/log-error.ts has a working
    // runtime channel. Every real error path already routes through
    // logError() per Task 10b.
    removeConsole: {
      exclude: ["error"],
    },
  },
  // NEXT_PUBLIC_API_URL is exposed to the browser via NEXT_PUBLIC_ prefix.
  // In production: https://api.summa.vision
  // In development: http://localhost:8000
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.summa.vision",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "9000",
      },
      {
        protocol: "https",
        hostname: "**.amazonaws.com",
      },
    ],
  },
};

export default nextConfig;
