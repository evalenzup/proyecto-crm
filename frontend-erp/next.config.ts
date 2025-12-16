import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: [
    // Orígenes desde los que permites peticiones a /_next/*
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://192.168.68.136:3000',
  ],
  distDir: process.env.NEXT_DIST_DIR || '.next',
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Warning: This allows production builds to successfully complete even if
    // your project has type errors.
    ignoreBuildErrors: true,
  },
};

export default nextConfig;