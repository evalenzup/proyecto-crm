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
  FontSizeOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { ConfigProvider, theme as antdTheme, Switch, Tooltip, Dropdown, Space, Avatar, MenuProps, Grid, Typography } from 'antd';
import esES from 'antd/locale/es_ES';
import { Breadcrumbs } from './Breadcrumb';
import { useAuth } from '@/context/AuthContext';
import { usuarioService } from '@/services/usuarioService';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import { empresaService } from '@/services/empresaService';
import { useFilterContext } from '@/context/FilterContext';
import api from '@/lib/axios';

// Carga ProLayout solo en cliente
const ProLayout = dynamic(
  () => import('@ant-design/pro-layout').then((m) => m.default),
  { ssr: false }
);

// Componente para el contenido derecho (Usuario + Logout)
const RightContent: React.FC = () => {
  const { user, logout: authLogout } = useAuth();
  const { clearAllFilters } = useFilterContext();

  const logout = () => {
    clearAllFilters();
    authLogout();
  };

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
  { path: '/ayuda', name: 'Ayuda', icon: <QuestionCircleOutlined /> },
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
  const { user, isAuthenticated, logout: authLogout } = useAuth();
  const { clearAllFilters } = useFilterContext();

  const logout = () => {
    clearAllFilters();
    authLogout();
  };

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
        if (prefs.font_size) {
          setFontSize(prefs.font_size);
          if (typeof window !== 'undefined') {
            localStorage.setItem(FONT_SIZE_KEY, prefs.font_size.toString());
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

  // Font Size con persistencia
  const [fontSize, setFontSize] = useState<number>(14);
  const FONT_SIZE_KEY = 'ui.theme.fontsize';

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedSize = localStorage.getItem(FONT_SIZE_KEY);
      if (savedSize) {
        const parsed = parseInt(savedSize, 10);
        if (!isNaN(parsed)) setFontSize(parsed);
      }
    }
  }, []);

  const handleFontSizeChange = (val: number) => {
    setFontSize(val);
    if (typeof window !== 'undefined') {
      localStorage.setItem(FONT_SIZE_KEY, val.toString());
    }
    if (isAuthenticated) {
      usuarioService.updatePreferences({ font_size: val })
        .catch(err => console.error("Error guardando tamaño de letra", err));
    }
  };

  const themeConfig = useMemo(
    () => ({
      algorithm,
      token: {
        padding: 12,
        paddingLG: 16,
        paddingSM: 8,
        borderRadius: 8,
        fontSize: fontSize,
      },
    }),
    [algorithm, fontSize]
  );

  // Logo dinámico basado en la empresa seleccionada
  const { selectedEmpresaId, empresas, isAdmin } = useEmpresaSelector();
  const [logoUrl, setLogoUrl] = useState<string>('/logo-empresa.png');

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;

    const fetchLogo = async () => {
      // Si es Admin, siempre mostrar logo default (pedido explícito del usuario)
      if (isAdmin) {
        setLogoUrl('/logo-empresa.png');
        return;
      }

      const currentEmpresa = empresas.find(e => e.id === selectedEmpresaId);

      if (currentEmpresa?.logo) {
        try {
          // El endpoint es protegido, así que usamos axios (via empresaService o directo) para bajar el blob
          // empresaService.descargarLogo devuelve la URL string, la usamos para el get
          const url = empresaService.descargarLogo(currentEmpresa.id);
          // Importamos api instance si es necesario, o usamos fetch con headers si tenemos el token.
          // Mejor: importamos 'api' de axios instance que ya tiene el interceptor de auth.
          // Necesitamos importar 'api' en este archivo.
          // Como no tengo 'api' importado, voy a usar la URL pero agregando el token si pudiera.
          // Pero lo más limpio es importar la instancia 'api' configurada.
          // Voy a asumir que puedo importar api from '@/lib/axios'

          // IMPORTANTE: Primero tengo que agregar el import de api arriba.
          // Por ahora escribo la lógica asumiendo que "api" estará disponible.
          const response = await api.get(url, { responseType: 'blob' });
          if (active) {
            objectUrl = URL.createObjectURL(response.data);
            setLogoUrl(objectUrl);
          }
        } catch (error) {
          console.error("Error cargando logo:", error);
          if (active) setLogoUrl('/logo-empresa.png');
        }
      } else {
        if (active) setLogoUrl('/logo-empresa.png');
      }
    };

    fetchLogo();

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selectedEmpresaId, empresas, isAdmin]);

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
        rightContentRender={false}
        // Render del header del sider para colocar el logo arriba del menú
        menuHeaderRender={() => {
          // eslint-disable-next-line react-hooks/rules-of-hooks
          const screens = Grid.useBreakpoint();
          // Ocultar logo en pantallas pequeñas (xs y sm)
          // Si no es md (desktop), asumimos que es móvil o tablet vertical
          if (!screens.md) {
            return null;
          }

          return (
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
          )
        }}
        // Footer del menú lateral: switch de tema fijo al final del menú
        // Footer del menú lateral: Usuario + Switch tema + Font Size
        menuFooterRender={(props) => {
          if (props?.collapsed) {
            return (
              <div style={{ padding: '12px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
                <Tooltip title="Cerrar Sesión">
                  <LogoutOutlined
                    style={{ fontSize: 16, cursor: 'pointer', color: 'var(--ant-color-error)' }}
                    onClick={logout}
                  />
                </Tooltip>
                <ThemeSwitch mode={mode} onToggle={handleThemeChange} />
                <Dropdown
                  menu={{
                    items: [
                      { key: '12', label: 'Chico (A-)', onClick: () => handleFontSizeChange(12) },
                      { key: '14', label: 'Normal (A)', onClick: () => handleFontSizeChange(14) },
                      { key: '16', label: 'Grande (A+)', onClick: () => handleFontSizeChange(16) },
                      { key: '18', label: 'Extra (A++)', onClick: () => handleFontSizeChange(18) },
                    ],
                    selectedKeys: [fontSize.toString()]
                  }}
                  placement="topRight"
                >
                  <FontSizeOutlined style={{ fontSize: 16, cursor: 'pointer', color: 'var(--ant-color-text-description)' }} />
                </Dropdown>
              </div>
            );
          }

          return (
            <div
              style={{
                padding: 12,
                borderTop: '1px solid var(--ant-color-border-secondary, #f0f0f0)',
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
                width: '100%',
              }}
            >
              {user && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Avatar style={{ backgroundColor: '#1890ff' }} icon={<UserOutlined />} />
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{ fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {user.nombre_completo || 'Usuario'}
                    </div>
                    <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      <Typography.Text type="secondary" style={{ fontSize: '0.85em' }}>
                        {user.email}
                      </Typography.Text>
                    </div>
                  </div>
                  <Tooltip title="Cerrar Sesión">
                    <LogoutOutlined
                      style={{ cursor: 'pointer', color: 'var(--ant-color-text-description)' }}
                      onClick={logout}
                    />
                  </Tooltip>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography.Text style={{ fontSize: '0.9em', opacity: 0.85 }}>Modo oscuro</Typography.Text>
                <ThemeSwitch mode={mode} onToggle={handleThemeChange} />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <Typography.Text style={{ fontSize: '0.9em', opacity: 0.85 }}>Tamaño de letra</Typography.Text>
                <Space.Compact block>
                  {[
                    { label: 'A-', val: 12, title: 'Chico' },
                    { label: 'A', val: 14, title: 'Normal' },
                    { label: 'A+', val: 16, title: 'Grande' },
                    { label: 'A++', val: 18, title: 'Extra' }
                  ].map(opt => (
                    <Tooltip title={opt.title} key={opt.val}>
                      <div
                        onClick={() => handleFontSizeChange(opt.val)}
                        style={{
                          flex: 1,
                          textAlign: 'center',
                          cursor: 'pointer',
                          padding: '4px 0',
                          fontSize: '0.9em',
                          // Usar colores del tema actual si es posible, o fallback
                          backgroundColor: fontSize === opt.val ? (mode === 'dark' ? '#177ddc' : '#1890ff') : 'transparent',
                          color: fontSize === opt.val ? '#fff' : 'inherit',
                          border: '1px solid var(--ant-color-border, #d9d9d9)',
                          borderRightWidth: opt.val === 18 ? 1 : 0, // Ultimo item tiene borde
                          // First item rounded left, last right
                          borderRadius: opt.val === 12 ? '4px 0 0 4px' : opt.val === 18 ? '0 4px 4px 0' : 0,
                          transition: 'all 0.2s'
                        }}
                      >
                        {opt.label}
                      </div>
                    </Tooltip>
                  ))}
                </Space.Compact>
              </div>
            </div>
          );
        }}
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