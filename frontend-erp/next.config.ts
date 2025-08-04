/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: [
    // Orígenes desde los que permites peticiones a /_next/*
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://158.97.12.153:3000',
  ],
};

module.exports = nextConfig;