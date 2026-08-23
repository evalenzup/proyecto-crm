// components/HistorialFacturaModal.tsx
// Todo lo que le pasó a una factura, en una sola línea de tiempo: lo que hizo
// la gente (auditoría) y lo que contestaron el PAC y el SAT en cada solicitud
// de cancelación (bitácora). Antes esto sólo se podía ver entrando a la base y
// cruzando dos tablas a mano.
import React, { useCallback, useEffect, useState } from 'react';
import { Modal, Timeline, Spin, Tag, Empty, Switch, Space, Typography } from 'antd';
import {
  FileAddOutlined, EditOutlined, SafetyCertificateOutlined, MailOutlined,
  CloseCircleOutlined, SearchOutlined, WarningOutlined, HistoryOutlined,
} from '@ant-design/icons';
import { getHistorialFactura } from '@/services/facturaService';
import type { CambioFactura, EventoHistorial, HistorialFactura } from '@/services/facturaService';
import { formatDate } from '@/utils/formatDate';

const { Text } = Typography;

interface Props {
  facturaId: string | null;
  open: boolean;
  onClose: () => void;
}

/** Icono y color por tipo de evento, para poder recorrer la lista de un vistazo. */
const APARIENCIA: Record<string, { color: string; icono: React.ReactNode }> = {
  CREAR_FACTURA: { color: 'gray', icono: <FileAddOutlined /> },
  CREAR_FACTURA_DESDE_ORDEN: { color: 'gray', icono: <FileAddOutlined /> },
  ACTUALIZAR_FACTURA: { color: 'blue', icono: <EditOutlined /> },
  TIMBRAR_FACTURA: { color: 'green', icono: <SafetyCertificateOutlined /> },
  ENVIAR_FACTURA_EMAIL: { color: 'gray', icono: <MailOutlined /> },
  CANCELAR_FACTURA: { color: 'orange', icono: <CloseCircleOutlined /> },
  SOLICITUD_CANCELACION: { color: 'orange', icono: <CloseCircleOutlined /> },
  VERIFICAR_SAT: { color: 'cyan', icono: <SearchOutlined /> },
  REVERTIR_CANCELACION: { color: 'red', icono: <WarningOutlined /> },
};

const COLOR_GRUPO: Record<CambioFactura['grupo'], string> = {
  fiscal: 'red',
  cobranza: 'gold',
  interno: 'default',
};

const ETIQUETA_CAMPO: Record<string, string> = {
  cliente_id: 'Cliente',
  uso_cfdi: 'Uso de CFDI',
  forma_pago: 'Forma de pago',
  metodo_pago: 'Método de pago',
  status_pago: 'Estatus de pago',
  fecha_cobro: 'Fecha de cobro',
  fecha_pago: 'Fecha de pago programada',
  cfdi_relacionados: 'CFDI relacionados',
  cfdi_relacionados_tipo: 'Tipo de relación',
  observaciones: 'Observaciones',
  conceptos: 'Conceptos',
};

const nombreCampo = (campo: string) =>
  ETIQUETA_CAMPO[campo] ?? campo.replace(/_/g, ' ');

const comoTexto = (v: any): string => {
  if (v === null || v === undefined || v === '') return '—';
  if (Array.isArray(v)) return `${v.length} renglón(es)`;
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
};

/** Los cambios de una modificación, en tabla chica. */
const Cambios: React.FC<{ cambios: CambioFactura[] }> = ({ cambios }) => (
  <table style={{ marginTop: 6, fontSize: 12, borderCollapse: 'collapse', width: '100%' }}>
    <tbody>
      {cambios.map((c, i) => (
        <tr key={`${c.campo}-${i}`}>
          <td style={{ padding: '2px 8px 2px 0', whiteSpace: 'nowrap', verticalAlign: 'top' }}>
            <Tag color={COLOR_GRUPO[c.grupo]} style={{ marginInlineEnd: 6 }}>
              {c.grupo}
            </Tag>
            {nombreCampo(c.campo)}
          </td>
          <td style={{ padding: '2px 8px 2px 0', color: '#999', textDecoration: 'line-through' }}>
            {comoTexto(c.antes)}
          </td>
          <td style={{ padding: '2px 0' }}>→ {comoTexto(c.despues)}</td>
        </tr>
      ))}
    </tbody>
  </table>
);

/** Lo que contestaron el PAC y el SAT en una solicitud de cancelación. */
const DetalleCancelacion: React.FC<{ d: any }> = ({ d }) => (
  <div style={{ marginTop: 6, fontSize: 12 }}>
    <Space size={4} wrap>
      {d.motivo && <Tag>Motivo {d.motivo}</Tag>}
      {d.pac_code && <Tag color="blue">PAC: {d.pac_code}</Tag>}
      {d.sat_estado && <Tag color="purple">SAT: {d.sat_estado}</Tag>}
      {d.sat_estatus_cancelacion && <Tag color="purple">{d.sat_estatus_cancelacion}</Tag>}
      {/* El dato que más cuesta ver en otro lado y el que explica los casos raros. */}
      {d.sat_registro_solicitud === false && (
        <Tag color="red">El SAT no registró la solicitud</Tag>
      )}
      {d.tiene_acuse && <Tag color="green">Con acuse sellado</Tag>}
      {d.resultado && <Tag color={d.resultado === 'CANCELADO' ? 'green' : 'volcano'}>{d.resultado}</Tag>}
    </Space>
    {d.pac_message && (
      <div style={{ marginTop: 4, color: '#666', whiteSpace: 'pre-wrap' }}>{d.pac_message}</div>
    )}
  </div>
);

/** Resultado de una consulta al SAT: sólo interesa cuando dijo algo distinto. */
const DetalleVerificacion: React.FC<{ d: any }> = ({ d }) => {
  const cambio = d.estatus_propuesto || (d.actualizado ? d.estatus_nuevo : null);
  return (
    <div style={{ marginTop: 6, fontSize: 12 }}>
      <Space size={4} wrap>
        {d.sat_estado && <Tag color="purple">SAT: {d.sat_estado}</Tag>}
        {d.sat_estatus_cancelacion && <Tag color="purple">{d.sat_estatus_cancelacion}</Tag>}
        {cambio && (
          <Tag color={d.actualizado ? 'green' : 'orange'}>
            {d.estatus_anterior} → {cambio}
            {!d.actualizado && ' (propuesto, sin aplicar)'}
          </Tag>
        )}
        {!cambio && <Tag>Sin diferencias</Tag>}
      </Space>
    </div>
  );
};

const Detalle: React.FC<{ evento: EventoHistorial }> = ({ evento }) => {
  const d = evento.detalle;
  if (!d || typeof d !== 'object') return null;
  if (evento.fuente === 'cancelacion') return <DetalleCancelacion d={d} />;
  if (evento.accion === 'VERIFICAR_SAT') return <DetalleVerificacion d={d} />;
  if (Array.isArray(d.cambios) && d.cambios.length) return <Cambios cambios={d.cambios} />;
  return null;
};

export const HistorialFacturaModal: React.FC<Props> = ({ facturaId, open, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [datos, setDatos] = useState<HistorialFactura | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Los cambios internos (notas, observaciones) se esconden por defecto: si no,
  // una corrección de texto tapa el cambio de receptor que sí importa.
  const [verInternos, setVerInternos] = useState(false);

  const cargar = useCallback(async () => {
    if (!facturaId) return;
    setLoading(true);
    setError(null);
    try {
      setDatos(await getHistorialFactura(facturaId));
    } catch (e: any) {
      setError(
        e?.response?.data?.error?.detail ||
        e?.response?.data?.detail ||
        'No se pudo cargar el historial.',
      );
    } finally {
      setLoading(false);
    }
  }, [facturaId]);

  useEffect(() => {
    if (open) cargar();
  }, [open, cargar]);

  const eventos = (datos?.eventos ?? []).map((e) => {
    if (verInternos || !Array.isArray(e.detalle?.cambios)) return e;
    const visibles = e.detalle.cambios.filter((c: CambioFactura) => c.grupo !== 'interno');
    return { ...e, detalle: { ...e.detalle, cambios: visibles } };
  });

  const items = eventos.map((e, i) => {
    const ap = APARIENCIA[e.accion] ?? { color: 'gray', icono: <HistoryOutlined /> };
    return {
      key: i,
      color: ap.color,
      dot: ap.icono,
      children: (
        <div>
          <Space size={8} wrap>
            <Text strong>{e.titulo}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>{formatDate(e.fecha)}</Text>
            {e.usuario && <Text type="secondary" style={{ fontSize: 12 }}>· {e.usuario}</Text>}
          </Space>
          <Detalle evento={e} />
        </div>
      ),
    };
  });

  const f = datos?.factura;

  return (
    <Modal
      title={
        <Space>
          <HistoryOutlined />
          {f ? `Historial de ${f.serie ?? ''}-${f.folio ?? ''}` : 'Historial de la factura'}
          {f?.estatus && <Tag>{f.estatus}</Tag>}
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={780}
      style={{ top: 24 }}
      styles={{ body: { maxHeight: '70vh', overflowY: 'auto', paddingTop: 12 } }}
      destroyOnHidden
    >
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
          <Spin />
        </div>
      ) : error ? (
        <div style={{ padding: 24, textAlign: 'center', color: '#cf1322' }}>{error}</div>
      ) : items.length === 0 ? (
        <Empty description="Sin movimientos registrados" />
      ) : (
        <>
          <div style={{ marginBottom: 12, textAlign: 'right' }}>
            <Space size={6}>
              <Text type="secondary" style={{ fontSize: 12 }}>Ver cambios internos</Text>
              <Switch size="small" checked={verInternos} onChange={setVerInternos} />
            </Space>
          </div>
          <Timeline items={items} />
        </>
      )}
    </Modal>
  );
};

export default HistorialFacturaModal;
