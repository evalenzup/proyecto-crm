// src/pages/_app.tsx
import 'antd/dist/reset.css';
import type { AppProps } from 'next/app';
import { App as AntApp } from 'antd';
import { Layout } from '@/components/Layout';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@/styles/pro-overrides.css';

// Crear una instancia de QueryClient
const queryClient = new QueryClient();

export default function App({ Component, pageProps }: AppProps) {
  // Oculta el indicador de compilación de Next en desarrollo como respaldo
  if (process.env.NODE_ENV !== 'production' && typeof window !== 'undefined') {
    // Ejecutar una vez por render en cliente
    setTimeout(() => {
      const hide = () => {
        const selectors = [
          '#nextjs__build_indicator',
          '[data-nextjs-build-indicator]',
          '#__next-build-indicator',
          '#__next-build-watcher',
          'nextjs-portal',
        ];
        document.querySelectorAll(selectors.join(',')).forEach((el) => {
          (el as HTMLElement).style.display = 'none';
        });
      };
      hide();
      const mo = new MutationObserver(hide);
      mo.observe(document.documentElement, { childList: true, subtree: true });
      // Limpieza al descargar
      window.addEventListener('beforeunload', () => mo.disconnect());
    }, 0);
  }
  return (
    <QueryClientProvider client={queryClient}>
      <AntApp>
        <Layout>
          <Component {...pageProps} />
        </Layout>
      </AntApp>
    </QueryClientProvider>
  );
}
