// src/pages/_app.tsx
import 'antd/dist/reset.css';
import type { AppProps } from 'next/app';
import { App as AntApp, Spin, ConfigProvider } from 'antd';
import esES from 'antd/locale/es_ES';
import dayjs from 'dayjs';
import 'dayjs/locale/es';
import React from 'react';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { EmpresaProvider } from '@/context/EmpresaContext';
import { FilterProvider } from '@/context/FilterContext';
import { useRouter } from 'next/router';
import { Layout as MainLayout } from '@/components/Layout';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@/styles/pro-overrides.css';

dayjs.locale('es');

// Componente para proteger rutas
const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated && router.pathname !== '/login') {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100vh', gap: 16 }}>
        <Spin size="large" />
        <div>Cargando sesión...</div>
      </div>
    );
  }

  // Si no está autenticado y no es la página de login, no renderizar nada mientras redirige
  if (!isAuthenticated && router.pathname !== '/login') {
    return null;
  }

  return <>{children}</>;
};

// Crear una instancia de QueryClient
const queryClient = new QueryClient();

export default function App({ Component, pageProps }: AppProps) {
  // Ajuste para el build indicator de Next.js en dev
  if (process.env.NODE_ENV !== 'production' && typeof window !== 'undefined') {
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
      window.addEventListener('beforeunload', () => mo.disconnect());
    }, 0);
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={esES}>
        <AuthProvider>
          <EmpresaProvider>
            <AntApp>
              <AuthGuard>
                <FilterProvider>
                  {/* Si estamos en login, no usamos el MainLayout (que tiene sidebar, etc) */}
                  {/* Esto requiere verificar router.pathname. Para simplificar, asumimos que MainLayout maneja esto o Login es una pagina aparte */}
                  {/* Vamos a hacer render condicional del Layout */}
                  <RenderLayout Component={Component} pageProps={pageProps} />
                </FilterProvider>
              </AuthGuard>
            </AntApp>
          </EmpresaProvider>
        </AuthProvider>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

// Helper para renderizar layout condicionalmente
const RenderLayout = ({ Component, pageProps }: any) => {
  const router = useRouter();
  const isLoginPage = router.pathname === '/login';

  if (isLoginPage) {
    return <Component {...pageProps} />;
  }

  return (
    <MainLayout>
      <Component {...pageProps} />
    </MainLayout>
  );
};
