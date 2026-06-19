// components/OrdenClienteContexto.tsx
// Muestra, para el cliente de una orden, el resumen de equipos de control,
// el contrato vigente y los croquis — los que apliquen. Reutilizable en la
// página de detalle de la orden y en el modal de la agenda.
import React, { useEffect, useState, useCallback } from 'react';
import { Card, Spin, Tag, Button, Space, Modal, message, Empty } from 'antd';
import {
  ToolOutlined, FileProtectOutlined, PictureOutlined,
  EyeOutlined, DownloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { equipoService } from '@/services/equipoService';
import { clienteService, ClienteDocumento, Croquis } from '@/services/clienteService';

interface Props {
  clienteId: string;
  empresaId: string;
}

interface EquipoResumen { tipo: string; cantidad: number; }

const esImagen = (nombre: string) => /\.(jpe?g|png|webp|gif)$/i.test(nombre);

export const OrdenClienteContexto: React.FC<Props> = ({ clienteId, empresaId }) => {
  const [loading, setLoading] = useState(true);
  const [equipos, setEquipos] = useState<EquipoResumen[]>([]);
  const [contrato, setContrato] = useState<ClienteDocumento | null>(null);
  const [contratoVigente, setContratoVigente] = useState(false);
  const [croquis, setCroquis] = useState<Croquis[]>([]);

  const [preview, setPreview] = useState<{ url: string; tipo: 'pdf' | 'imagen'; titulo: string } | null>(null);

  const cargar = useCallback(async () => {
    if (!clienteId) return;
    setLoading(true);
    try {
      const [eqPage, docs, croqs] = await Promise.all([
        equipoService.getEquipos({ cliente_id: clienteId, empresa_id: empresaId, activo: true, limit: 500 }),
        clienteService.listDocumentos(clienteId),
        clienteService.listCroquis(clienteId, empresaId),
      ]);

      // Resumen de equipos por tipo
      const map = new Map<string, number>();
      for (const e of eqPage.items) {
        const t = e.tipo_equipo_nombre ?? 'Sin tipo';
        map.set(t, (map.get(t) ?? 0) + 1);
      }
      setEquipos(Array.from(map.entries()).map(([tipo, cantidad]) => ({ tipo, cantidad })).sort((a, b) => a.tipo.localeCompare(b.tipo)));

      // Contrato: el documento tipo CONTRATO con vigencia más reciente
      const hoy = dayjs();
      const contratos = docs
        .filter((d) => d.tipo === 'CONTRATO')
        .sort((a, b) => dayjs(b.vigencia_hasta ?? b.creado_en).valueOf() - dayjs(a.vigencia_hasta ?? a.creado_en).valueOf());
      const c = contratos[0] ?? null;
      setContrato(c);
      setContratoVigente(
        !!c && (!c.vigencia_hasta || dayjs(c.vigencia_hasta).endOf('day').isAfter(hoy)) &&
        (!c.vigencia_desde || !dayjs(c.vigencia_desde).startOf('day').isAfter(hoy))
      );

      setCroquis(croqs);
    } catch {
      message.error('No se pudo cargar la información del cliente');
    } finally {
      setLoading(false);
    }
  }, [clienteId, empresaId]);

  useEffect(() => { cargar(); }, [cargar]);

  const verBlob = async (getBlob: () => Promise<Blob>, archivo: string, titulo: string) => {
    try {
      const blob = await getBlob();
      const url = window.URL.createObjectURL(blob);
      setPreview({ url, tipo: esImagen(archivo) ? 'imagen' : 'pdf', titulo });
    } catch {
      message.error('No se pudo abrir el archivo');
    }
  };

  const descargarBlob = async (getBlob: () => Promise<Blob>, nombre: string) => {
    try {
      const blob = await getBlob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = nombre; a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error('No se pudo descargar el archivo');
    }
  };

  const cerrarPreview = () => {
    if (preview) window.URL.revokeObjectURL(preview.url);
    setPreview(null);
  };

  if (loading) {
    return <Card title="Cliente" style={{ marginBottom: 16 }}><div style={{ textAlign: 'center', padding: 16 }}><Spin /></div></Card>;
  }

  const sinNada = equipos.length === 0 && !contrato && croquis.length === 0;

  return (
    <Card title="Equipos, contrato y croquis" style={{ marginBottom: 16 }} size="small">
      {sinNada ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Este cliente no tiene equipos, contrato ni croquis registrados" />
      ) : (
        <Space direction="vertical" size={14} style={{ width: '100%' }}>
          {/* Equipos de control */}
          {equipos.length > 0 && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#389e0d', marginBottom: 6 }}>
                <ToolOutlined /> Equipos de control
              </div>
              <Space size={[6, 6]} wrap>
                {equipos.map((e) => (
                  <Tag key={e.tipo} color="green" style={{ margin: 0 }}>{e.tipo} ×{e.cantidad}</Tag>
                ))}
              </Space>
            </div>
          )}

          {/* Contrato vigente */}
          {contrato && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#0a5c91', marginBottom: 6 }}>
                <FileProtectOutlined /> Contrato
                {contratoVigente
                  ? <Tag color="blue" style={{ marginLeft: 6 }}>Vigente</Tag>
                  : <Tag color="red" style={{ marginLeft: 6 }}>Vencido</Tag>}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{contrato.nombre}</div>
                  <div style={{ fontSize: 12, color: '#888' }}>
                    {contrato.numero ? `Nº ${contrato.numero} · ` : ''}
                    {contrato.vigencia_desde || contrato.vigencia_hasta
                      ? `${contrato.vigencia_desde ? dayjs(contrato.vigencia_desde).format('DD/MM/YYYY') : '—'} – ${contrato.vigencia_hasta ? dayjs(contrato.vigencia_hasta).format('DD/MM/YYYY') : '—'}`
                      : 'Sin vigencia registrada'}
                  </div>
                </div>
                <Space size={4}>
                  <Button size="small" icon={<EyeOutlined />} onClick={() => verBlob(() => clienteService.downloadDocumento(clienteId, contrato.id), contrato.archivo, contrato.nombre)} />
                  <Button size="small" icon={<DownloadOutlined />} onClick={() => descargarBlob(() => clienteService.downloadDocumento(clienteId, contrato.id), contrato.nombre)} />
                </Space>
              </div>
            </div>
          )}

          {/* Croquis */}
          {croquis.length > 0 && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#531dab', marginBottom: 6 }}>
                <PictureOutlined /> Croquis ({croquis.length})
              </div>
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                {croquis.map((c) => (
                  <div key={c.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{c.titulo}</div>
                      <div style={{ fontSize: 12, color: '#888' }}>{c.area ? c.area : 'General'}</div>
                    </div>
                    <Space size={4}>
                      <Button size="small" icon={<EyeOutlined />} onClick={() => verBlob(() => clienteService.downloadCroquis(clienteId, c.id), c.archivo, c.titulo)} />
                      <Button size="small" icon={<DownloadOutlined />} onClick={() => descargarBlob(() => clienteService.downloadCroquis(clienteId, c.id), c.titulo)} />
                    </Space>
                  </div>
                ))}
              </Space>
            </div>
          )}
        </Space>
      )}

      {/* Modal de visualización */}
      <Modal
        title={preview?.titulo}
        open={!!preview}
        onCancel={cerrarPreview}
        footer={null}
        width="90%"
        style={{ top: 20, maxWidth: 1000 }}
        styles={{ body: { height: '80vh', padding: 0 } }}
        destroyOnClose
      >
        {preview && (
          preview.tipo === 'imagen' ? (
            <div style={{ width: '100%', height: '100%', overflow: 'auto', textAlign: 'center', background: '#f0f0f0' }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={preview.url} alt={preview.titulo} style={{ maxWidth: '100%' }} />
            </div>
          ) : (
            <iframe src={preview.url} title={preview.titulo} style={{ width: '100%', height: '100%', border: 'none' }} />
          )
        )}
      </Modal>
    </Card>
  );
};

export default OrdenClienteContexto;
