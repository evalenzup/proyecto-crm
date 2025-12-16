import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: [
    // Orígenes desde los que permites peticiones a /_next/*
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://192.168.68.136:3000',
  ],

};

export default nextConfig;