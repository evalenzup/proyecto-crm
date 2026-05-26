// pages/ordenes-servicio/[id].tsx
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import {
  Button,
  Spin,
  Card,
  Tag,
  Badge,
  Descriptions,
  Timeline,
  Typography,
  Space,
  Select,
  Input,
  message,
  Row,
  Col,
} from 'antd';
import {
  EditOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { Breadcrumbs } from '@/components/Breadcrumb';
import ordenServicioService, {
  OrdenServicioOut,
  EstadoOS,
} from '@/services/ordenServicioService';
import { ESTADO_COLOR, ESTADO_LABEL, PRIORIDAD_COLOR } from '@/utils/ordenServicioConstants';

const { Text } = Typography;
const { Option } = Select;

const TODOS_ESTADOS: EstadoOS[] = [
  'PENDIENTE', 'ASIGNADO', 'EN_CAMINO', 'EN_PROGRESO', 'COMPLETADO', 'CANCELADO', 'REAGENDADO',
];

export default function OrdenServicioDetalle() {
  const router = useRouter();
  const { id } = router.query;

  const [data, setData] = useState<OrdenServicioOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [cambiandoEstado, setCambiandoEstado] = useState(false);
  const [nuevoEstado, setNuevoEstado] = useState<EstadoOS | null>(null);
  const [notasCierre, setNotasCierre] = useState('');

  const load = async () => {
    if (!id || typeof id !== 'string') return;
    setLoading(true);
    try {
      const result = await ordenServicioService.get(id);
      setData(result);
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo cargar la orden');
      router.push('/ordenes-servicio');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  const handleCambiarEstado = async () => {
    if (!nuevoEstado || !id || typeof id !== 'string') return;
    setCambiandoEstado(true);
    try {
      await ordenServicioService.cambiarEstado(id, {
        estado: nuevoEstado,
        notas: notasCierre || null,
      });
      message.success(`Estado cambiado a: ${ESTADO_LABEL[nuevoEstado]}`);
      setNuevoEstado(null);
      setNotasCierre('');
      load();
    } catch (err: any) {
      if (!err?._handled) message.error(err?.response?.data?.detail ?? 'Error al cambiar el estado');
    } finally {
      setCambiandoEstado(false);
    }
  };

  if (loading) {
    return (
      <Spin spinning tip="Cargando...">
        <div style={{ minHeight: 200 }} />
      </Spin>
    );
  }

  if (!data) return null;

  const transicionesDisponibles = TODOS_ESTADOS.filter(e => e !== data.estado);

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">
            {data.folio_os}
            <Space size={8} style={{ marginLeft: 12, fontWeight: 'normal', fontSize: 14 }}>
              <Tag color={ESTADO_COLOR[data.estado]}>{ESTADO_LABEL[data.estado]}</Tag>
              <Tag color={PRIORIDAD_COLOR[data.prioridad]}>{data.prioridad}</Tag>
            </Space>
          </h1>
        </div>
        <div className="app-page-header__right">
          <Button
            icon={<EditOutlined />}
            onClick={() => router.push(`/ordenes-servicio/form/${data.id}`)}
          >
            Editar
          </Button>
        </div>
      </div>

      <div className="app-content">
      <Row gutter={16}>
        {/* Columna izquierda */}
        <Col xs={24} lg={16}>
          <Card style={{ marginBottom: 16 }}>
            <Descriptions column={2} size="small">
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
          </Card>

          <Card title="Programación" style={{ marginBottom: 16 }}>
            <Descriptions column={2} size="small">
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
          </Card>

          {(data.notas_tecnico || data.notas_internas || data.notas_cierre) && (
            <Card title="Notas" style={{ marginBottom: 16 }}>
              <Descriptions column={1} size="small">
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
            </Card>
          )}
        </Col>

        {/* Columna derecha */}
        <Col xs={24} lg={8}>
          {/* Cambio de estado */}
          {transicionesDisponibles.length > 0 && (
            <Card title="Cambiar Estado" style={{ marginBottom: 16 }}>
              <Select
                style={{ width: '100%', marginBottom: 8 }}
                placeholder="Nuevo estado…"
                value={nuevoEstado ?? undefined}
                onChange={(v) => setNuevoEstado(v)}
              >
                {transicionesDisponibles.map((e) => (
                  <Option key={e} value={e}>
                    <Tag color={ESTADO_COLOR[e]}>{ESTADO_LABEL[e]}</Tag>
                  </Option>
                ))}
              </Select>
              {nuevoEstado === 'COMPLETADO' && (
                <Input.TextArea
                  rows={2}
                  placeholder="Notas de cierre (opcional)…"
                  value={notasCierre}
                  onChange={(e) => setNotasCierre(e.target.value)}
                  style={{ marginBottom: 8 }}
                />
              )}
              <Button
                type="primary"
                block
                disabled={!nuevoEstado}
                loading={cambiandoEstado}
                icon={<CheckCircleOutlined />}
                onClick={handleCambiarEstado}
              >
                Aplicar
              </Button>
            </Card>
          )}

          {/* Historial */}
          <Card title="Historial">
            {data.historial.length === 0 ? (
              <Text type="secondary">Sin historial</Text>
            ) : (
              <Timeline
                items={data.historial.map((h) => ({
                  dot: <ClockCircleOutlined style={{ fontSize: 12 }} />,
                  children: (
                    <div>
                      <div>
                        {h.estado_anterior && (
                          <>
                            <Tag>{h.estado_anterior}</Tag>
                            {' → '}
                          </>
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
            )}
          </Card>
        </Col>
      </Row>
      </div>
    </>
  );
}
