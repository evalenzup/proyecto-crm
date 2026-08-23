// frontend-erp/src/pages/mi-agenda/index.tsx
'use client';

/**
 * Agenda del técnico de campo.
 *
 * Es la pantalla que ve una cuenta con rol OPERATIVO al entrar, y la única a la
 * que tiene acceso. Se diseñó para el celular: una tarjeta por servicio, botones
 * grandes y un solo botón de avance por vez, para que no haya que pensar cuál
 * apretar con el teléfono en una mano.
 *
 * El estado avanza en un solo sentido (EN_CAMINO → EN_PROGRESO → COMPLETADO).
 * Cancelar no está: si el servicio no se pudo hacer, el técnico lo reporta con
 * el motivo y la oficina decide si cancela o reagenda. El backend impone las
 * mismas reglas, esto sólo es la cara amable.
 */

import React from 'react';
import {
  Button, Card, Empty, Modal, Input, Spin, Tag, Typography, message, DatePicker,
} from 'antd';
import {
  EnvironmentOutlined, ClockCircleOutlined,
  WarningOutlined, LogoutOutlined, ReloadOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import ordenServicioService from '@/services/ordenServicioService';
import type { OrdenServicioListOut } from '@/services/ordenServicioService';
import { useAuth } from '@/context/AuthContext';

const { Text, Title } = Typography;

/** Qué botón de avance toca según el estado. null = ya no avanza. */
const SIGUIENTE: Record<string, { estado: string; texto: string } | null> = {
  PENDIENTE:   { estado: 'EN_CAMINO',   texto: 'Voy en camino' },
  ASIGNADO:    { estado: 'EN_CAMINO',   texto: 'Voy en camino' },
  EN_CAMINO:   { estado: 'EN_PROGRESO', texto: 'Llegué, empecé' },
  EN_PROGRESO: { estado: 'COMPLETADO',  texto: 'Terminé' },
  COMPLETADO:  null,
  CANCELADO:   null,
  REAGENDADO:  null,
};

const ESTADO_COLOR: Record<string, string> = {
  PENDIENTE: 'default',
  ASIGNADO: 'blue',
  EN_CAMINO: 'orange',
  EN_PROGRESO: 'gold',
  COMPLETADO: 'green',
  CANCELADO: 'red',
  REAGENDADO: 'purple',
};

const ESTADO_TEXTO: Record<string, string> = {
  PENDIENTE: 'Pendiente',
  ASIGNADO: 'Asignado',
  EN_CAMINO: 'En camino',
  EN_PROGRESO: 'En proceso',
  COMPLETADO: 'Terminado',
  CANCELADO: 'Cancelado',
  REAGENDADO: 'Reagendado',
};

const MiAgendaPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [fecha, setFecha] = React.useState<Dayjs>(dayjs());
  const [items, setItems] = React.useState<OrdenServicioListOut[]>([]);
  const [cargando, setCargando] = React.useState(false);
  const [guardando, setGuardando] = React.useState<string | null>(null);

  const cargar = React.useCallback(async (dia: Dayjs) => {
    setCargando(true);
    try {
      const { items } = await ordenServicioService.list({
        fecha_desde: dia.format('YYYY-MM-DD'),
        fecha_hasta: dia.format('YYYY-MM-DD'),
        limit: 200,
      });
      setItems(items);
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo cargar tu agenda');
    } finally {
      setCargando(false);
    }
  }, []);

  React.useEffect(() => { cargar(fecha); }, [fecha, cargar]);

  const avanzar = async (o: OrdenServicioListOut) => {
    const paso = SIGUIENTE[o.estado];
    if (!paso) return;
    setGuardando(o.id);
    try {
      await ordenServicioService.cambiarEstado(o.id, { estado: paso.estado as any });
      message.success(`${o.folio_os}: ${ESTADO_TEXTO[paso.estado]}`);
      await cargar(fecha);
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo actualizar el servicio');
    } finally {
      setGuardando(null);
    }
  };

  const reportar = (o: OrdenServicioListOut) => {
    let motivo = '';
    Modal.confirm({
      title: `${o.folio_os}: no se pudo realizar`,
      icon: <WarningOutlined style={{ color: '#faad14' }} />,
      content: (
        <>
          <p>Cuéntale a la oficina qué pasó. Ellos deciden si se cancela o se reagenda.</p>
          <Input.TextArea
            rows={3}
            maxLength={500}
            placeholder="Ej. El local estaba cerrado, no había quien abriera…"
            onChange={(e) => { motivo = e.target.value; }}
          />
        </>
      ),
      okText: 'Enviar reporte',
      cancelText: 'Cancelar',
      onOk: async () => {
        if (motivo.trim().length < 5) {
          message.warning('Escribe brevemente qué pasó.');
          throw new Error('motivo vacío');   // deja el diálogo abierto
        }
        await ordenServicioService.reportarIncidencia(o.id, motivo.trim());
        message.success('Reporte enviado a la oficina');
        await cargar(fecha);
      },
    });
  };

  const esHoy = fecha.isSame(dayjs(), 'day');

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: '12px 12px 32px' }}>
      {/* Encabezado */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Title level={4} style={{ margin: 0 }}>Mi agenda</Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {user?.nombre_completo || user?.email}
          </Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => cargar(fecha)} loading={cargando} />
        <Button icon={<LogoutOutlined />} onClick={logout} />
      </div>

      {/* Día */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <DatePicker
          value={fecha}
          onChange={(d) => d && setFecha(d)}
          format="dddd D [de] MMMM"
          allowClear={false}
          inputReadOnly
          style={{ flex: 1 }}
        />
        {!esHoy && <Button onClick={() => setFecha(dayjs())}>Hoy</Button>}
      </div>

      {cargando && items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      ) : items.length === 0 ? (
        <Empty description={esHoy ? 'No tienes servicios hoy' : 'No tienes servicios ese día'} />
      ) : (
        items.map((o) => {
          const paso = SIGUIENTE[o.estado];
          const cerrada = o.estado === 'COMPLETADO' || o.estado === 'CANCELADO';
          return (
            <Card
              key={o.id}
              size="small"
              style={{ marginBottom: 10, opacity: cerrada ? 0.65 : 1 }}
              styles={{ body: { padding: 12 } }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <Text strong style={{ fontSize: 15 }}>
                  <ClockCircleOutlined /> {o.hora_inicio?.slice(0, 5) ?? 'Sin hora'}
                </Text>
                <Tag color={ESTADO_COLOR[o.estado]} style={{ marginInlineEnd: 0 }}>
                  {ESTADO_TEXTO[o.estado] ?? o.estado}
                </Tag>
                <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
                  {o.folio_os}
                </Text>
              </div>

              <div style={{ fontSize: 15, fontWeight: 500 }}>{o.cliente_nombre ?? '—'}</div>
              {o.servicio_nombre && (
                <div style={{ fontSize: 13, color: '#888' }}>{o.servicio_nombre}</div>
              )}

              {o.direccion_servicio && (
                <a
                  href={`https://maps.google.com/?q=${encodeURIComponent(o.direccion_servicio)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ display: 'block', fontSize: 13, marginTop: 6 }}
                >
                  <EnvironmentOutlined /> {o.direccion_servicio}
                </a>
              )}

              {o.notas_tecnico && (
                <div style={{
                  fontSize: 13, marginTop: 8, padding: 8,
                  background: 'rgba(250,173,20,.12)', borderRadius: 6,
                }}>
                  {o.notas_tecnico}
                </div>
              )}

              {!cerrada && (
                <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                  {paso && (
                    <Button
                      type="primary"
                      size="large"
                      block
                      loading={guardando === o.id}
                      onClick={() => avanzar(o)}
                    >
                      {paso.texto}
                    </Button>
                  )}
                  <Button
                    size="large"
                    danger
                    icon={<WarningOutlined />}
                    onClick={() => reportar(o)}
                    title="No se pudo realizar"
                  />
                </div>
              )}
            </Card>
          );
        })
      )}
    </div>
  );
};

export default MiAgendaPage;
