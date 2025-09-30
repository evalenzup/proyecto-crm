// frontend-erp/src/components/Layout.tsx

'use client';
import React, { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  PieChartOutlined,
  TableOutlined,
  ContainerOutlined,
  SmileOutlined,
  BankOutlined,
  ProductOutlined,
  ContactsOutlined,
  BulbOutlined,
  MoonOutlined,
} from '@ant-design/icons';
import { ConfigProvider, theme as antdTheme, Switch, Tooltip } from 'antd';
import esES from 'antd/locale/es_ES';
import { Breadcrumbs } from './Breadcrumb';

// Carga ProLayout solo en cliente
const ProLayout = dynamic(
  () => import('@ant-design/pro-layout').then((m) => m.default),
  { ssr: false }
);

const menuData = [
  { path: '/', name: 'Dashboard', icon: <PieChartOutlined /> },
  { path: '/empresas', name: 'Empresas', icon: <BankOutlined /> },
  { path: '/clientes', name: 'Clientes', icon: <ContactsOutlined /> },
  { path: '/productos-servicios', name: 'Productos', icon: <ProductOutlined /> },
  { path: '/facturas', name: 'Facturación', icon: <ContainerOutlined />},
  { path: '/pagos', name: 'Pagos', icon: <ContainerOutlined />},
  { path: '/egresos', name: 'Egresos', icon: <TableOutlined /> },
  { path: '/inventario', name: 'Inventario', icon: <SmileOutlined /> },
];

const STORAGE_KEY = 'ui.theme.mode';

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

type Crumb = { path: string; label: string };

export const Layout: React.FC<{
  children: React.ReactNode;
  title?: string;
  breadcrumbs?: Crumb[];
  extra?: React.ReactNode;
}> = ({ children, title, breadcrumbs, extra }) => {
  const router = useRouter();

  // Tema con persistencia
  const [mode, setMode] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY) as 'light' | 'dark' | null;
      if (saved === 'dark' || saved === 'light') return saved;
      const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
      return prefersDark ? 'dark' : 'light';
    }
    return 'light';
  });

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
        // compactar un poco
        padding: 12,
        paddingLG: 16,
        paddingSM: 8,
        borderRadius: 8,
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
        layout="side"
        fixedHeader={false}
        fixSiderbar={false}
        siderWidth={180}
        contentWidth="Fluid"
        contentStyle={{ margin: 0, padding: 0, maxWidth: '100%' }}
        rightContentRender={() => (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingRight: 12 }}>
            <ThemeSwitch mode={mode} onToggle={(c) => setMode(c ? 'dark' : 'light')} />
          </div>
        )}
        // No usamos PageContainer interno de ProLayout
        pageTitleRender={false}
        breadcrumbRender={(routers = []) => {
          // if breadcrumbs are provided, use them
          if (breadcrumbs) {
            return breadcrumbs;
          }
          // otherwise, generate them from the router
          return [
            { path: '/', breadcrumbName: 'Inicio' },
            ...routers.map((router) => ({
              path: router.path,
              breadcrumbName: router.breadcrumbName,
            })),
          ];
        }}
      >
        {/* Header de página propio, sin max-width */}
        {(title || extra) && (
          <div className="app-page-header">
            <div className="app-page-header__left">
              {title && <h1 className="app-title">{title}</h1>}
            </div>
            <div className="app-page-header__right">{extra}</div>
          </div>
        )}

        {/* Contenido a ancho completo */}
        <main className="app-content">{children}</main>
      </ProLayout>
    </ConfigProvider>
  );
};