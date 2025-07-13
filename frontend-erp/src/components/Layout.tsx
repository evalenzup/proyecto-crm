// src/components/Layout.tsx
import React from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { PageContainer } from '@ant-design/pro-layout';
import {
  PieChartOutlined,
  TableOutlined,
  SmileOutlined,
  BankOutlined,
} from '@ant-design/icons';

// carga ProLayout solo en cliente
const ProLayout = dynamic(
  () => import('@ant-design/pro-layout').then(mod => mod.default),
  { ssr: false }
);

const menuData = [
  { path: '/', name: 'Dashboard', icon: <PieChartOutlined /> },
  { path: '/empresas', name: 'Empresas', icon: <BankOutlined /> },
  { path: '/facturas', name: 'Facturación', icon: <TableOutlined /> },
  { path: '/inventario', name: 'Inventario', icon: <SmileOutlined /> },
  
];

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const router = useRouter();
  return (
    <ProLayout
      title="ERP Unificado POC"
      menuDataRender={() => menuData}
      location={{ pathname: router.pathname }}
      menuItemRender={(item, dom) => <Link href={item.path || '/'}>{dom}</Link>}
      fixSiderbar
      siderWidth={200}
    >
      <PageContainer>{children}</PageContainer>
    </ProLayout>
  );
};
