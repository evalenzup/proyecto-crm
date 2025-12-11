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
  FileTextOutlined,
  UserOutlined,
  LogoutOutlined,
  DownOutlined,
} from '@ant-design/icons';
import { ConfigProvider, theme as antdTheme, Switch, Tooltip, Dropdown, Space, Avatar, MenuProps } from 'antd';
import esES from 'antd/locale/es_ES';
import { Breadcrumbs } from './Breadcrumb';
import { useAuth } from '@/context/AuthContext';
import { usuarioService } from '@/services/usuarioService';

// Carga ProLayout solo en cliente
const ProLayout = dynamic(
  () => import('@ant-design/pro-layout').then((m) => m.default),
  { ssr: false }
);

// Componente para el contenido derecho (Usuario + Logout)
const RightContent: React.FC = () => {
  const { user, logout } = useAuth();

  const items: MenuProps['items'] = [
    {
      key: 'logout',
      label: 'Cerrar Sesión',
      icon: <LogoutOutlined />,
      onClick: logout,
      danger: true,
    },
  ];

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16, paddingRight: 16 }}>
      {user && (
        <Dropdown menu={{ items }}>
          <Space style={{ cursor: 'pointer' }}>
            <Avatar style={{ backgroundColor: '#1890ff' }} icon={<UserOutlined />} />
            <span style={{ color: 'var(--ant-color-text)' }}>
              {user.nombre_completo || user.email}
            </span>
            <DownOutlined style={{ fontSize: '10px', color: 'var(--ant-color-text-description)' }} />
          </Space>
        </Dropdown>
      )}
    </div>
  );
};

// Definición base del menú
const baseMenuData = [
  { path: '/', name: 'Dashboard', icon: <PieChartOutlined /> },
  { path: '/empresas', name: 'Empresas', icon: <BankOutlined /> },
  { path: '/clientes', name: 'Clientes', icon: <ContactsOutlined /> },
  { path: '/productos-servicios', name: 'Productos', icon: <ProductOutlined /> },
  { path: '/facturas', name: 'Facturación', icon: <ContainerOutlined /> },
  // { path: '/presupuestos', name: 'Presupuestos', icon: <FileTextOutlined /> },
  { path: '/pagos', name: 'Pagos', icon: <ContainerOutlined /> },
  { path: '/egresos', name: 'Egresos', icon: <TableOutlined /> },
  // { path: '/inventario', name: 'Inventario', icon: <SmileOutlined /> },
  // El ítem de Usuarios se agrega dinámicamente
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
  const { user, isAuthenticated } = useAuth();

  // Tema con persistencia
  const [mode, setMode] = useState<'light' | 'dark'>('light');

  // Cargar preferencia inicial del localStorage o sistema
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY) as 'light' | 'dark' | null;
      if (saved === 'dark' || saved === 'light') {
        setMode(saved);
      } else {
        const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
        setMode(prefersDark ? 'dark' : 'light');
      }
    }
  }, []);

  // Sincronizar con backend cuando el usuario se autentica
  useEffect(() => {
    if (isAuthenticated && user) {
      usuarioService.getPreferences().then(prefs => {
        if (prefs.theme && (prefs.theme === 'light' || prefs.theme === 'dark')) {
          setMode(prefs.theme as 'light' | 'dark');
          // Actualizar localStorage también para mantener sync
          if (typeof window !== 'undefined') {
            localStorage.setItem(STORAGE_KEY, prefs.theme);
          }
        }
      }).catch(err => console.error("Error cargando preferencias", err));
    }
  }, [isAuthenticated, user]);

  // Aplicar tema al DOM y localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, mode);
      document.documentElement.setAttribute('data-theme', mode);
    }
  }, [mode]);

  const handleThemeChange = (checked: boolean) => {
    const newMode = checked ? 'dark' : 'light';
    setMode(newMode);

    // Guardar en backend si está logueado
    if (isAuthenticated) {
      usuarioService.updatePreferences({ theme: newMode })
        .catch(err => console.error("Error guardando preferencias", err));
    }
  };

  const algorithm = useMemo(
    () => (mode === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm),
    [mode]
  );

  const themeConfig = useMemo(
    () => ({
      algorithm,
      token: {
        padding: 12,
        paddingLG: 16,
        paddingSM: 8,
        borderRadius: 8,
      },
    }),
    [algorithm]
  );

  // Logo de empresa arriba del menú (estático desde /public)
  const [logoUrl] = useState<string>('/logo-empresa.png');

  const menuData = useMemo(() => {
    const menu = [...baseMenuData];
    if (user?.rol === 'admin') {
      menu.push({ path: '/usuarios', name: 'Usuarios', icon: <UserOutlined /> });
    }
    return menu;
  }, [user]);

  return (
    <ConfigProvider theme={themeConfig} locale={esES}>
      <ProLayout
        title={false}
        menuDataRender={() => menuData}
        location={{ pathname: router.pathname }}
        menuItemRender={(item, dom) => <Link href={item.path || '/'}>{dom}</Link>}
        layout="side"
        fixedHeader={false}
        fixSiderbar={true}
        siderWidth={240}
        contentWidth="Fluid"
        contentStyle={{ margin: 0, padding: 0, maxWidth: '100%' }}
        rightContentRender={() => <RightContent />}
        // Render del header del sider para colocar el logo arriba del menú
        menuHeaderRender={() => (
          <div
            style={{
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '100%',
            }}
          >
            {logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={logoUrl}
                alt="Logo empresa"
                style={{ width: '100%', maxWidth: '100%', height: 'auto', objectFit: 'contain', display: 'block' }}
                onError={(e) => {
                  const t = e.currentTarget as HTMLImageElement;
                  if (t.src.endsWith('/vercel.svg')) return;
                  t.src = '/vercel.svg';
                }}
              />
            ) : (
              <div style={{ width: '100%', height: 40, background: 'var(--ant-color-fill-tertiary)' }} />
            )}
          </div>
        )}
        // Footer del menú lateral: switch de tema fijo al final del menú
        menuFooterRender={(props) => (
          <div
            style={{
              padding: props?.collapsed ? '12px 8px' : 12,
              borderTop: '1px solid var(--ant-color-border-secondary, #f0f0f0)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: props?.collapsed ? 'center' : 'space-between',
              gap: 8,
              width: '100%',
            }}
          >
            {!props?.collapsed && (
              <span style={{ fontSize: 12, opacity: 0.85 }}>Modo oscuro</span>
            )}
            <ThemeSwitch mode={mode} onToggle={handleThemeChange} />
          </div>
        )}
        // No usamos PageContainer interno de ProLayout
        pageTitleRender={false}
        breadcrumbRender={(routers = []) => {
          if (breadcrumbs) {
            return breadcrumbs;
          }
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