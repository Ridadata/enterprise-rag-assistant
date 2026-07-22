import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dev-only: this project is accessed via 127.0.0.1 (curl/Playwright tooling) as well as
  // localhost, and Next.js blocks cross-origin dev resources (HMR websocket, etc.) by
  // default for hosts it doesn't recognize as the dev origin.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Produces a self-contained server bundle (only the deps actually reachable at runtime)
  // so the Docker image doesn't need to carry the whole node_modules tree.
  output: "standalone",
};

export default nextConfig;
