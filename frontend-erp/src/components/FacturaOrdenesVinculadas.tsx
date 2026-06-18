// src/components/FacturaOrdenesVinculadas.tsx
// Lista las órdenes de servicio vinculadas a una factura.
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Card, Table, Tag, Button, Tooltip } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import ordenServicioService, { OrdenServicioListOut } from '@/services/ordenServicioService';

interface Props {
  facturaId: string;
  empresaId?: string;
}

export const FacturaOrdenesVinculadas: React.FC<Props> = ({ facturaId, empresaId }) => {
  const router = useRouter();
  const [ordenes, setOrdenes] = useState<OrdenServicioListOut[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Esperar a tener empresaId: el endpoint lo requiere para usuarios admin.
    if (!facturaId || !empresaId) return;
    let active = true;
    setLoading(true);
    ordenServicioService
      .list({ factura_id: facturaId, empresa_id: empresaId, activo: undefined, limit: 200 } as any)
      .then((res) => { if (active) setOrdenes(res.items ?? []); })
      .catch(() => { if (active) setOrdenes([]); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [facturaId, empresaId]);

  // No mostrar la tarjeta si no hay órdenes vinculadas
  if (!loading && ordenes.length === 0) return null;

  const columns = [
    {
      title: 'Folio', dataIndex: 'folio_os', key: 'folio_os', width: 110,
      render: (v: string) => <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{v}</span>,
    },
    { title: 'Fecha', dataIndex: 'fecha_programada', key: 'fecha', width: 110, render: (v: string) => dayjs(v).format('DD/MM/YYYY') },
    { title: 'Cliente', dataIndex: 'cliente_nombre', key: 'cliente', ellipsis: true, render: (v: string) => v ?? '—' },
    { title: 'Estado', dataIndex: 'estado', key: 'estado', width: 130, render: (v: string) => <Tag>{v}</Tag> },
    {
      title: 'Precio', dataIndex: 'precio_acordado', key: 'precio', width: 110, align: 'right' as const,
      render: (v: number | null) => v != null ? `$${Number(v).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '—',
    },
    {
      title: '', key: 'acc', width: 50, align: 'center' as const,
      render: (_: unknown, r: OrdenServicioListOut) => (
        <Tooltip title="Ver orden">
          <Button size="small" icon={<EyeOutlined />} onClick={() => router.push(`/ordenes-servicio/${r.id}`)} />
        </Tooltip>
      ),
    },
  ];

  return (
    <Card title={`Órdenes vinculadas (${ordenes.length})`} size="small" style={{ marginTop: 16 }}>
      <Table
        rowKey="id" size="small" loading={loading} columns={columns}
        dataSource={ordenes} pagination={false}
      />
    </Card>
  );
};

export default FacturaOrdenesVinculadas;
