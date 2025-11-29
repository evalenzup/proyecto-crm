import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: [
    // Orígenes desde los que permites peticiones a /_next/*
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://158.97.12.153:3000',
  ],
  // Oculta el indicador de actividad de compilación de Next.js (icono redondo con "N") en desarrollo
  devIndicators: {
    buildActivity: false,
    appIsrStatus: false,
  },
};

export default nextConfig;