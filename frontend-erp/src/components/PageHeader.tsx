// src/components/PageHeader.tsx
// Header estándar de página: breadcrumbs + título a la izquierda, acciones a la derecha.
// Reemplaza el bloque .app-page-header repetido en cada página.
import React from 'react';
import { Space } from 'antd';
import { Breadcrumbs, Breadcrumb } from '@/components/Breadcrumb';

interface PageHeaderProps {
  title: React.ReactNode;
  /** Acciones del lado derecho (botones, selects, etc.) */
  extra?: React.ReactNode;
  /** Texto secundario bajo el título */
  subtitle?: React.ReactNode;
  /** Breadcrumbs explícitos; si se omite se infieren de la ruta */
  breadcrumbItems?: Breadcrumb[];
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, extra, subtitle, breadcrumbItems }) => (
  <div className="app-page-header">
    <div className="app-page-header__left">
      <Breadcrumbs items={breadcrumbItems} />
      <h1 className="app-title">{title}</h1>
      {subtitle && (
        <div style={{ fontSize: 13, opacity: 0.65 }}>{subtitle}</div>
      )}
    </div>
    {extra && (
      <div className="app-page-header__right">
        <Space wrap>{extra}</Space>
      </div>
    )}
  </div>
);

export default PageHeader;
