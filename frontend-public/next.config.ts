import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
        hostname: "**.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "placehold.co",
      },
    ],
  },
};

export default nextConfig;
