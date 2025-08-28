// src/pages/_app.tsx
import 'antd/dist/reset.css';
import type { AppProps } from 'next/app';
import { Layout } from '@/components/Layout'; // 
import '@/styles/pro-overrides.css'; // ✅ Importa global aquí


export default function App({ Component, pageProps }: AppProps) {
  return (
    <Layout>
      <Component {...pageProps} />
    </Layout>
  );
}