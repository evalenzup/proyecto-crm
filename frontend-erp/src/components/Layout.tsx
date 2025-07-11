// src/components/Layout.tsx
import React from 'react';
import ProLayout, { PageContainer } from '@ant-design/pro-layout';
import { PieChartOutlined, TableOutlined } from '@ant-design/icons';

const menuData = [
  { path: '/', name: 'Dashboard', icon: <PieChartOutlined /> },
  { path: '/facturas', name: 'Facturación', icon: <TableOutlined /> },
  { path: '/inventario', name: 'Inventario', icon: <PieChartOutlined /> },
];

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ProLayout
    title="ERP Unificado POC"
    menuDataRender={() => menuData}
    location={{ pathname: '/' }}
    fixSiderbar
    siderWidth={200}
  >
    <PageContainer>
      {children}
    </PageContainer>
  </ProLayout>
);

