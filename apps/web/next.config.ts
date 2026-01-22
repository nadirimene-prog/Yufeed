import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/login",
        destination: "/",
      },
    ];
  },
};

export default nextConfig;
