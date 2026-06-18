// src/components/OrdenFacturaSection.tsx
// Sección "Factura" de una orden de servicio: crear borrador, vincular existente,
// ver o desvincular. Reutilizada por el modal de la agenda y la página de orden.
import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { Space, Button, Tag, Typography, Modal, Select, message } from 'antd';
import { FileTextOutlined, ExportOutlined, LinkOutlined, PlusOutlined } from '@ant-design/icons';
import ordenServicioService, { OrdenServicioOut } from '@/services/ordenServicioService';

const { Text } = Typography;

interface Props {
  orden: OrdenServicioOut;
  /** Se llama tras vincular/desvincular con la orden actualizada (o sin args si solo refrescar). */
  onChanged?: (orden?: OrdenServicioOut) => void;
}

export const OrdenFacturaSection: React.FC<Props> = ({ orden, onChanged }) => {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [vincularOpen, setVincularOpen] = useState(false);
  const [facturas, setFacturas] = useState<any[]>([]);
  const [sel, setSel] = useState<string | undefined>(undefined);

  const crear = async () => {
    setBusy(true);
    try {
      const res = await ordenServicioService.crearFactura(orden.id);
      message.success('Factura borrador creada');
      router.push(`/facturas/form/${res.factura_id}`);
    } catch (err: any) {
      if (!err?._handled) message.error(err?.response?.data?.detail ?? 'Error al crear la factura');
    } finally {
      setBusy(false);
    }
  };

  const confirmarCrear = () => {
    Modal.confirm({
      title: `¿Crear factura para la orden ${orden.folio_os}?`,
      content: 'Se generará una factura en borrador, ligada a esta orden y a su cliente. Después podrás completar el concepto fiscal y timbrarla.',
      okText: 'Sí, crear borrador',
      cancelText: 'Cancelar',
      onOk: crear,
    });
  };

  const abrirVincular = async () => {
    setSel(undefined);
    setVincularOpen(true);
    try {
      const res = await ordenServicioService.facturasVinculables(orden.id);
      setFacturas(res ?? []);
    } catch {
      setFacturas([]);
    }
  };

  const confirmarVincular = async () => {
    if (!sel) return;
    setBusy(true);
    try {
      const actualizada = await ordenServicioService.vincularFactura(orden.id, sel);
      setVincularOpen(false);
      message.success('Factura vinculada');
      onChanged?.(actualizada);
    } catch (err: any) {
      if (!err?._handled) message.error(err?.response?.data?.detail ?? 'Error al vincular la factura');
    } finally {
      setBusy(false);
    }
  };

  const desvincular = async () => {
    setBusy(true);
    try {
      const actualizada = await ordenServicioService.desvincularFactura(orden.id);
      message.success('Factura desvinculada');
      onChanged?.(actualizada);
    } catch (err: any) {
      if (!err?._handled) message.error(err?.response?.data?.detail ?? 'Error al desvincular');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {orden.factura ? (
        <Space wrap align="center">
          <FileTextOutlined style={{ color: '#1677ff' }} />
          <Text strong>{orden.factura.serie}-{orden.factura.folio}</Text>
          <Tag>{orden.factura.estatus}</Tag>
          {orden.factura.status_pago && (
            <Tag color={orden.factura.status_pago === 'PAGADA' ? 'green' : 'orange'}>{orden.factura.status_pago}</Tag>
          )}
          <Button size="small" icon={<ExportOutlined />} onClick={() => router.push(`/facturas/form/${orden.factura_id}`)}>
            Ver factura
          </Button>
          <Button size="small" danger onClick={desvincular} loading={busy}>Desvincular</Button>
        </Space>
      ) : (
        <Space wrap>
          <Button icon={<PlusOutlined />} onClick={confirmarCrear} loading={busy}>Crear factura</Button>
          <Button icon={<LinkOutlined />} onClick={abrirVincular}>Vincular existente</Button>
        </Space>
      )}

      <Modal
        title="Vincular factura existente"
        open={vincularOpen}
        onCancel={() => setVincularOpen(false)}
        onOk={confirmarVincular}
        okText="Vincular"
        okButtonProps={{ disabled: !sel, loading: busy }}
      >
        <Text type="secondary">Facturas del cliente o de clientes con el mismo RFC (sucursales):</Text>
        <Select
          style={{ width: '100%', marginTop: 8 }}
          showSearch
          placeholder="Selecciona una factura"
          optionFilterProp="label"
          value={sel}
          onChange={setSel}
          options={facturas.map((f: any) => ({
            value: f.id,
            label: `${f.serie}-${f.folio} · ${f.cliente_nombre ?? ''} · ${f.estatus} · ${Number(f.total ?? 0).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}`,
          }))}
          notFoundContent="Sin facturas vinculables"
        />
      </Modal>
    </>
  );
};

export default OrdenFacturaSection;
