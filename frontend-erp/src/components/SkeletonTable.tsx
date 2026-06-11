// src/components/SkeletonTable.tsx
// Placeholder de tabla para la carga inicial: filas grises animadas en lugar
// de un spinner sobre un área vacía. Usar solo cuando aún no hay datos:
//   {loading && items.length === 0 ? <SkeletonTable /> : <Table ... />}
import React from 'react';
import { Skeleton } from 'antd';

interface SkeletonTableProps {
  /** Número de filas fantasma (default 8) */
  rows?: number;
}

export const SkeletonTable: React.FC<SkeletonTableProps> = ({ rows = 8 }) => (
  <div style={{ padding: '8px 4px' }} aria-busy aria-label="Cargando datos">
    <Skeleton.Input active block size="small" style={{ height: 30, marginBottom: 16 }} />
    {Array.from({ length: rows }).map((_, i) => (
      <Skeleton.Input
        key={i}
        active
        block
        size="small"
        style={{ height: 20, marginBottom: 14, opacity: 1 - i * 0.09 }}
      />
    ))}
  </div>
);

export default SkeletonTable;
