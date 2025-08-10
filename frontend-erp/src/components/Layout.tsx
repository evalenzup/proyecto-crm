// src/components/Layout.tsx
'use client';
import React, { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { PageContainer } from '@ant-design/pro-layout';
import {
  PieChartOutlined,
  TableOutlined,
  SmileOutlined,
  BankOutlined,
  ProductOutlined,
  ContactsOutlined,
  BulbOutlined,
  MoonOutlined,
} from '@ant-design/icons';
import { ConfigProvider, theme as antdTheme, Switch, Tooltip } from 'antd';
import esES from 'antd/locale/es_ES';

// Carga ProLayout solo en cliente
const ProLayout = dynamic(
  () => import('@ant-design/pro-layout').then((mod) => mod.default),
  { ssr: false }
);

const menuData = [
  { path: '/', name: 'Dashboard', icon: <PieChartOutlined /> },
  { path: '/empresas', name: 'Empresas', icon: <BankOutlined /> },
  { path: '/clientes', name: 'Clientes', icon: <ContactsOutlined /> },
  { path: '/productos-servicios', name: 'Productos', icon: <ProductOutlined /> },
  { path: '/facturas', name: 'Facturación', icon: <TableOutlined /> },
  { path: '/inventario', name: 'Inventario', icon: <SmileOutlined /> },
];

const STORAGE_KEY = 'ui.theme.mode'; // 'light' | 'dark'

const ThemeSwitch: React.FC<{
  mode: 'light' | 'dark';
  onToggle: (checked: boolean) => void;
}> = ({ mode, onToggle }) => (
  <Tooltip title={mode === 'dark' ? 'Modo oscuro' : 'Modo claro'}>
    <Switch
      checked={mode === 'dark'}
      onChange={onToggle}
      checkedChildren={<MoonOutlined />}
      unCheckedChildren={<BulbOutlined />}
    />
  </Tooltip>
);

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const router = useRouter();

  // Inicialización sin "flash" claro
  const [mode, setMode] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY) as 'light' | 'dark' | null;
      if (saved === 'dark' || saved === 'light') return saved;
      const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
      return prefersDark ? 'dark' : 'light';
    }
    return 'light';
  });

  // Persistir y exponer data-theme (opcional para estilos globales)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, mode);
      document.documentElement.setAttribute('data-theme', mode);
    }
  }, [mode]);

  const algorithm = useMemo(
    () => (mode === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm),
    [mode]
  );

  const themeConfig = useMemo(
    () => ({
      algorithm,
      token: {
        // Personaliza tokens si quieres:
        // colorPrimary: '#1677ff',
        // borderRadius: 8,
      },
    }),
    [algorithm]
  );

  return (
    <ConfigProvider theme={themeConfig} locale={esES}>
      <ProLayout
        title="CORPORATIVO NORTON"
        menuDataRender={() => menuData}
        location={{ pathname: router.pathname }}
        menuItemRender={(item, dom) => <Link href={item.path || '/'}>{dom}</Link>}
        fixSiderbar
        siderWidth={200}
        // Toggle en el header superior (top bar)
        rightContentRender={() => (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingRight: 12 }}>
            <ThemeSwitch mode={mode} onToggle={(c) => setMode(c ? 'dark' : 'light')} />
          </div>
        )}
      >
        {/* Fallback: por si tu top bar no se ve, también mostramos el switch aquí */}
        <PageContainer
          header={{
            extra: (
              <ThemeSwitch mode={mode} onToggle={(c) => setMode(c ? 'dark' : 'light')} />
            ),
          }}
        >
          {children}
        </PageContainer>
      </ProLayout>
    </ConfigProvider>
  );
};