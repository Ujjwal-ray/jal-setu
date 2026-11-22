import type { NextConfig } from "next";

// The Flask backend (../app.py) serves the JSON API. Next.js proxies /api/* to it,
// so the browser only ever talks to one origin.
const BACKEND = process.env.JALSETU_API ?? "http://127.0.0.1:5000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
};

export default nextConfig;
