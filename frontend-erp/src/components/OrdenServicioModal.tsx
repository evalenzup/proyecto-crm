// components/OrdenServicioModal.tsx
// Modal de detalle de orden de servicio — usado desde la agenda (vista diaria)
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import {
  Modal,
  Spin,
  Descriptions,
  Tag,
  Badge,
  Timeline,
  Typography,
  Space,
  Select,
  Input,
  Button,
  Divider,
  message,
} from 'antd';
import {
  EditOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExportOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import ordenServicioService, {
  OrdenServicioOut,
  EstadoOS,
  PrioridadOS,
} from '@/services/ordenServicioService';

const { Text } = Typography;
const { Option } = Select;

const ESTADO_COLOR: Record<EstadoOS, string> = {
  PENDIENTE:   'default',
  ASIGNADO:    'blue',
  EN_CAMINO:   'cyan',
  EN_PROGRESO: 'processing',
  COMPLETADO:  'success',
  CANCELADO:   'error',
  REAGENDADO:  'warning',
};

const ESTADO_LABEL: Record<EstadoOS, string> = {
  PENDIENTE:   'Pendiente',
  ASIGNADO:    'Asignado',
  EN_CAMINO:   'En camino',
  EN_PROGRESO: 'En progreso',
  COMPLETADO:  'Completado',
  CANCELADO:   'Cancelado',
  REAGENDADO:  'Reagendado',
};

const PRIORIDAD_COLOR: Record<PrioridadOS, string> = {
  BAJA:    'green',
  MEDIA:   'blue',
  ALTA:    'orange',
  URGENTE: 'red',
};

const TRANSICIONES: Record<EstadoOS, EstadoOS[]> = {
  PENDIENTE:   ['ASIGNADO', 'CANCELADO'],
  ASIGNADO:    ['EN_CAMINO', 'REAGENDADO', 'CANCELADO'],
  EN_CAMINO:   ['EN_PROGRESO', 'REAGENDADO'],
  EN_PROGRESO: ['COMPLETADO', 'REAGENDADO'],
  COMPLETADO:  [],
  CANCELADO:   ['PENDIENTE'],
  REAGENDADO:  ['PENDIENTE', 'ASIGNADO'],
};

interface Props {
  ordenId: string | null;       // null = cerrado
  onClose: () => void;
  onEstadoChanged?: () => void; // para refrescar la agenda tras cambio de estado
}

export default function OrdenServicioModal({ ordenId, onClose, onEstadoChanged }: Props) {
  const router = useRouter();

  const [data, setData]                       = useState<OrdenServicioOut | null>(null);
  const [loading, setLoading]                 = useState(false);
  const [cambiandoEstado, setCambiandoEstado] = useState(false);
  const [nuevoEstado, setNuevoEstado]         = useState<EstadoOS | null>(null);
  const [notasCierre, setNotasCierre]         = useState('');

  const load = async (id: string) => {
    setLoading(true);
    setData(null);
    setNuevoEstado(null);
    setNotasCierre('');
    try {
      const result = await ordenServicioService.get(id);
      setData(result);
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo cargar la orden');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (ordenId) load(ordenId);
  }, [ordenId]);

  const handleCambiarEstado = async () => {
    if (!nuevoEstado || !ordenId) return;
    setCambiandoEstado(true);
    try {
      await ordenServicioService.cambiarEstado(ordenId, {
        estado: nuevoEstado,
        notas: notasCierre || null,
      });
      message.success(`Estado cambiado a: ${ESTADO_LABEL[nuevoEstado]}`);
      setNuevoEstado(null);
      setNotasCierre('');
      await load(ordenId);
      onEstadoChanged?.();
    } catch (err: any) {
      if (!err?._handled) message.error(err?.response?.data?.detail ?? 'Error al cambiar el estado');
    } finally {
      setCambiandoEstado(false);
    }
  };

  const transiciones = data ? (TRANSICIONES[data.estado] ?? []) : [];

  return (
    <Modal
      open={!!ordenId}
      onCancel={onClose}
      footer={null}
      width={700}
      title={
        data ? (
          <Space>
            <Text strong style={{ fontFamily: 'monospace', fontSize: 15 }}>{data.folio_os}</Text>
            <Badge status={ESTADO_COLOR[data.estado] as any} text={ESTADO_LABEL[data.estado]} />
            <Tag color={PRIORIDAD_COLOR[data.prioridad]}>{data.prioridad}</Tag>
          </Space>
        ) : 'Cargando…'
      }
      styles={{ body: { maxHeight: '75vh', overflowY: 'auto', paddingTop: 8 } }}
    >
      {loading || !data ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : (
        <>
          {/* ── Datos principales ── */}
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="Cliente" span={2}>
              <Text strong>{data.cliente?.nombre_comercial ?? data.cliente_id}</Text>
              {data.cliente?.telefono && (
                <Text type="secondary" style={{ marginLeft: 8 }}>{data.cliente.telefono}</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Técnico">
              {data.tecnico?.nombre_completo ?? <Text type="secondary">Sin asignar</Text>}
            </Descriptions.Item>
            <Descriptions.Item label="Unidad">
              {data.unidad
                ? `${data.unidad.nombre}${data.unidad.placas ? ` (${data.unidad.placas})` : ''}`
                : <Text type="secondary">Sin asignar</Text>}
            </Descriptions.Item>
            <Descriptions.Item label="Servicio">
              {data.servicio?.nombre ?? <Text type="secondary">—</Text>}
            </Descriptions.Item>
            <Descriptions.Item label="Precio acordado">
              {data.precio_acordado != null
                ? `$${Number(data.precio_acordado).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
                : '—'}
            </Descriptions.Item>
          </Descriptions>

          {/* ── Programación ── */}
          <Divider orientation="left" style={{ fontSize: 13, marginTop: 16, marginBottom: 10 }}>Programación</Divider>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="Fecha">
              {dayjs(data.fecha_programada).format('DD [de] MMMM [de] YYYY')}
            </Descriptions.Item>
            <Descriptions.Item label="Duración">
              {data.duracion_minutos ? `${data.duracion_minutos} min` : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Hora inicio">
              {data.hora_inicio ? data.hora_inicio.slice(0, 5) : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Hora fin">
              {data.hora_fin ? data.hora_fin.slice(0, 5) : '—'}
            </Descriptions.Item>
            {data.direccion_servicio && (
              <Descriptions.Item label="Dirección" span={2}>
                {data.direccion_servicio}
              </Descriptions.Item>
            )}
          </Descriptions>

          {/* ── Notas ── */}
          {(data.notas_tecnico || data.notas_internas || data.notas_cierre) && (
            <>
              <Divider orientation="left" style={{ fontSize: 13, marginTop: 16, marginBottom: 10 }}>Notas</Divider>
              <Descriptions column={1} size="small" bordered>
                {data.notas_tecnico && (
                  <Descriptions.Item label="Al técnico">{data.notas_tecnico}</Descriptions.Item>
                )}
                {data.notas_internas && (
                  <Descriptions.Item label="Internas">{data.notas_internas}</Descriptions.Item>
                )}
                {data.notas_cierre && (
                  <Descriptions.Item label="Cierre">{data.notas_cierre}</Descriptions.Item>
                )}
              </Descriptions>
            </>
          )}

          {/* ── Cambio de estado ── */}
          {transiciones.length > 0 && (
            <>
              <Divider orientation="left" style={{ fontSize: 13, marginTop: 16, marginBottom: 10 }}>Cambiar Estado</Divider>
              <Space.Compact style={{ width: '100%', marginBottom: nuevoEstado === 'COMPLETADO' ? 8 : 0 }}>
                <Select
                  style={{ flex: 1 }}
                  placeholder="Nuevo estado…"
                  value={nuevoEstado ?? undefined}
                  onChange={(v) => setNuevoEstado(v)}
                >
                  {transiciones.map((e) => (
                    <Option key={e} value={e}>
                      <Badge status={ESTADO_COLOR[e] as any} text={ESTADO_LABEL[e]} />
                    </Option>
                  ))}
                </Select>
                <Button
                  type="primary"
                  disabled={!nuevoEstado}
                  loading={cambiandoEstado}
                  icon={<CheckCircleOutlined />}
                  onClick={handleCambiarEstado}
                >
                  Aplicar
                </Button>
              </Space.Compact>
              {nuevoEstado === 'COMPLETADO' && (
                <Input.TextArea
                  rows={2}
                  placeholder="Notas de cierre (opcional)…"
                  value={notasCierre}
                  onChange={(e) => setNotasCierre(e.target.value)}
                />
              )}
            </>
          )}

          {/* ── Historial ── */}
          {data.historial.length > 0 && (
            <>
              <Divider orientation="left" style={{ fontSize: 13, marginTop: 16, marginBottom: 10 }}>Historial</Divider>
              <Timeline
                items={data.historial.map((h) => ({
                  dot: <ClockCircleOutlined style={{ fontSize: 12 }} />,
                  children: (
                    <div>
                      <div>
                        {h.estado_anterior && (
                          <><Tag>{h.estado_anterior}</Tag>{' → '}</>
                        )}
                        <Tag color="blue">{h.estado_nuevo}</Tag>
                      </div>
                      {h.notas && (
                        <Text type="secondary" style={{ fontSize: 12 }}>{h.notas}</Text>
                      )}
                      <div style={{ fontSize: 11, color: '#aaa' }}>
                        {dayjs(h.creado_en).format('DD/MM/YYYY HH:mm')}
                      </div>
                    </div>
                  ),
                }))}
              />
            </>
          )}

          {/* ── Footer: ir a página completa / editar ── */}
          <Divider style={{ marginTop: 12, marginBottom: 12 }} />
          <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              icon={<ExportOutlined />}
              onClick={() => router.push(`/ordenes-servicio/${data.id}`)}
            >
              Ver página completa
            </Button>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => router.push(`/ordenes-servicio/form/${data.id}`)}
            >
              Editar
            </Button>
          </Space>
        </>
      )}
    </Modal>
  );
}
