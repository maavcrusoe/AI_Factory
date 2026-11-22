import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone: el Dockerfile copia solo lo necesario para `node server.js`.
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    root: import.meta.dirname,
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
