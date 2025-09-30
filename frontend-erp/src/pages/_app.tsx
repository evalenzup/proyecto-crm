// src/pages/_app.tsx
import 'antd/dist/reset.css';
import type { AppProps } from 'next/app';
import { App as AntApp } from 'antd';
import { Layout } from '@/components/Layout'; // 
import '@/styles/pro-overrides.css'; // ✅ Importa global aquí


export default function App({ Component, pageProps }: AppProps) {
  return (
    <AntApp>
      <Layout>
        <Component {...pageProps} />
      </Layout>
    </AntApp>
  );
}