// frontend-erp/src/components/facturas/FacturaFormHeader.tsx
import React from 'react';
import { Breadcrumbs } from '@/components/Breadcrumb';

interface FacturaFormHeaderProps {
  id: string | null;
}

export const FacturaFormHeader: React.FC<FacturaFormHeaderProps> = ({ id }) => {
  return (
    <div className="app-page-header">
      <div className="app-page-header__left">
        <Breadcrumbs />
        <h1 className="app-title">{id ? 'Editar Factura' : 'Nueva Factura'}</h1>
      </div>
    </div>
  );
};
