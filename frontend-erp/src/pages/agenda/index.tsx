// pages/agenda/index.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Calendar,
  Badge,
  Tag,
  Button,
  Drawer,
  List,
  Typography,
  Spin,
  message,
  Space,
  theme,
  Select,
  Empty,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  UnorderedListOutlined,
  EyeOutlined,
  EditOutlined,
  CalendarOutlined,
  LeftOutlined,
  RightOutlined,
} from '@ant-design/icons';
import type { CalendarProps } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import 'dayjs/locale/es';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import ordenServicioService, {
  OrdenServicioListOut,
  EstadoOS,
} from '@/services/ordenServicioService';
import { ESTADO_COLOR, ESTADO_LABEL, PRIORIDAD_COLOR } from '@/utils/ordenServicioConstants';

dayjs.locale('es');

const { Text } = Typography;
const { Option } = Select;

// ── Constantes de la vista diaria ────────────────────────────────────────────
const HOUR_START = 7;   // 7:00 AM
const HOUR_END   = 21;  // 9:00 PM
const HOUR_HEIGHT = 60; // px por hora

// Color por estado (hex) para bloques en el timeline
const ESTADO_HEX: Record<EstadoOS, string> = {
  PENDIENTE:   '#faad14',
  ASIGNADO:    '#722ed1',
  EN_CAMINO:   '#13c2c2',
  EN_PROGRESO: '#1677ff',
  COMPLETADO:  '#52c41a',
  CANCELADO:   '#ff4d4f',
  REAGENDADO:  '#eb2f96',
};
const ESTADO_BG: Record<EstadoOS, string> = {
  PENDIENTE:   '#fffbe6',
  ASIGNADO:    '#f9f0ff',
  EN_CAMINO:   '#e6fffb',
  EN_PROGRESO: '#e6f4ff',
  COMPLETADO:  '#f6ffed',
  CANCELADO:   '#fff2f0',
  REAGENDADO:  '#fff0f6',
};

// Convierte "HH:MM:SS" o "HH:MM" → minutos desde medianoche
function toMinutes(time: string | null | undefined): number | null {
  if (!time) return null;
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
}

// ── Componente ────────────────────────────────────────────────────────────────

export default function AgendaPage() {
  const router = useRouter();
  const { token } = theme.useToken();
  const { selectedEmpresaId } = useEmpresaSelector();

  const [ordenes, setOrdenes] = useState<OrdenServicioListOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(dayjs());
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  const [estadoFilter, setEstadoFilter] = useState<EstadoOS | undefined>(undefined);
  const [viewMode, setViewMode] = useState<'month' | 'day'>('month');

  // ── Carga de datos ──────────────────────────────────────────────────────────

  const fetchRange = useCallback(
    async (desde: string, hasta: string) => {
      if (!selectedEmpresaId) return;
      setLoading(true);
      try {
        const params: any = {
          fecha_desde: desde,
          fecha_hasta: hasta,
          limit: 500,
          empresa_id: selectedEmpresaId,
        };
        if (estadoFilter) params.estado = estadoFilter;
        const result = await ordenServicioService.list(params);
        setOrdenes(result.items);
      } catch {
        message.error('Error al cargar la agenda');
      } finally {
        setLoading(false);
      }
    },
    [selectedEmpresaId, estadoFilter]
  );

  useEffect(() => {
    if (viewMode === 'month') {
      fetchRange(
        currentMonth.startOf('month').format('YYYY-MM-DD'),
        currentMonth.endOf('month').format('YYYY-MM-DD')
      );
    } else {
      fetchRange(
        selectedDate.format('YYYY-MM-DD'),
        selectedDate.format('YYYY-MM-DD')
      );
    }
  }, [fetchRange, currentMonth, selectedDate, viewMode]);

  // ── Agrupar por día ─────────────────────────────────────────────────────────

  const ordenesByDate = React.useMemo(() => {
    const map: Record<string, OrdenServicioListOut[]> = {};
    ordenes.forEach((o) => {
      const key = o.fecha_programada;
      if (!map[key]) map[key] = [];
      map[key].push(o);
    });
    return map;
  }, [ordenes]);

  // ── Vista mensual: render de celda ──────────────────────────────────────────

  const dateCellRender = (value: Dayjs) => {
    const key = value.format('YYYY-MM-DD');
    const items = ordenesByDate[key] ?? [];
    if (items.length === 0) return null;

    return (
      <ul style={{ padding: 0, margin: 0, listStyle: 'none' }}>
        {items.slice(0, 3).map((o) => (
          <li key={o.id} style={{ marginBottom: 2 }}>
            <Badge
              status={ESTADO_COLOR[o.estado] as any}
              text={
                <span style={{ fontSize: 11 }}>
                  {o.hora_inicio ? `${o.hora_inicio.slice(0, 5)} ` : ''}
                  {o.folio_os}
                  {o.tecnico_nombre ? ` · ${o.tecnico_nombre.split(' ')[0]}` : ''}
                </span>
              }
            />
          </li>
        ))}
        {items.length > 3 && (
          <li style={{ fontSize: 11, color: token.colorTextTertiary }}>
            +{items.length - 3} más
          </li>
        )}
      </ul>
    );
  };

  const cellRender: CalendarProps<Dayjs>['cellRender'] = (current, info) => {
    if (info.type === 'date') return dateCellRender(current);
    return info.originNode;
  };

  // ── Vista mensual: selección de día ────────────────────────────────────────

  const handleDateSelect = (date: Dayjs) => {
    setSelectedDate(date);
    const key = date.format('YYYY-MM-DD');
    if (viewMode === 'month') {
      if (ordenesByDate[key]?.length) {
        setDrawerOpen(true);
      }
    }
  };

  const handlePanelChange = (date: Dayjs) => {
    setCurrentMonth(date);
  };

  // ── Vista diaria: cálculo de posición de eventos ────────────────────────────

  const dayOrdenes = React.useMemo(() => {
    const key = selectedDate.format('YYYY-MM-DD');
    return (ordenesByDate[key] ?? []).slice().sort((a, b) => {
      const am = toMinutes(a.hora_inicio) ?? 0;
      const bm = toMinutes(b.hora_inicio) ?? 0;
      return am - bm;
    });
  }, [ordenesByDate, selectedDate]);

  // Separa órdenes con hora de las que no tienen hora ("todo el día")
  const timedOrdenes  = dayOrdenes.filter(o => o.hora_inicio);
  const allDayOrdenes = dayOrdenes.filter(o => !o.hora_inicio);

  // Calcula top y height de cada evento en el timeline
  function eventStyle(o: OrdenServicioListOut) {
    const startMin = toMinutes(o.hora_inicio)!;
    const endMin   = toMinutes(o.hora_fin) ?? (startMin + 60);
    const top      = (startMin - HOUR_START * 60) * (HOUR_HEIGHT / 60);
    const height   = Math.max((endMin - startMin) * (HOUR_HEIGHT / 60), 28);
    return { top, height };
  }

  // Resolución de solapamientos: asigna columna (lane) a cada evento
  type Lane = { orden: OrdenServicioListOut; lane: number; totalLanes: number };
  const timedWithLanes: Lane[] = React.useMemo(() => {
    const result: Lane[] = timedOrdenes.map(o => ({ orden: o, lane: 0, totalLanes: 1 }));
    for (let i = 0; i < result.length; i++) {
      const aStart = toMinutes(result[i].orden.hora_inicio)!;
      const aEnd   = toMinutes(result[i].orden.hora_fin) ?? (aStart + 60);
      const usedLanes: number[] = [];
      for (let j = 0; j < i; j++) {
        const bStart = toMinutes(result[j].orden.hora_inicio)!;
        const bEnd   = toMinutes(result[j].orden.hora_fin) ?? (bStart + 60);
        if (aStart < bEnd && aEnd > bStart) {
          usedLanes.push(result[j].lane);
        }
      }
      let lane = 0;
      while (usedLanes.includes(lane)) lane++;
      result[i].lane = lane;
    }
    // Calcular totalLanes para cada grupo solapado
    for (let i = 0; i < result.length; i++) {
      const aStart = toMinutes(result[i].orden.hora_inicio)!;
      const aEnd   = toMinutes(result[i].orden.hora_fin) ?? (aStart + 60);
      let maxLane = result[i].lane;
      for (let j = 0; j < result.length; j++) {
        if (i === j) continue;
        const bStart = toMinutes(result[j].orden.hora_inicio)!;
        const bEnd   = toMinutes(result[j].orden.hora_fin) ?? (bStart + 60);
        if (aStart < bEnd && aEnd > bStart) maxLane = Math.max(maxLane, result[j].lane);
      }
      result[i].totalLanes = maxLane + 1;
    }
    return result;
  }, [timedOrdenes]);

  const totalTimelineHeight = (HOUR_END - HOUR_START) * HOUR_HEIGHT;

  const drawerOrdenes = ordenesByDate[selectedDate.format('YYYY-MM-DD')] ?? [];

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">Agenda</h1>
        </div>
        <div className="app-page-header__right">
          <Space wrap>
            <Select
              placeholder="Filtrar por estado"
              allowClear
              style={{ width: 160 }}
              value={estadoFilter}
              onChange={(v) => setEstadoFilter(v)}
            >
              {(Object.keys(ESTADO_LABEL) as EstadoOS[]).map((e) => (
                <Option key={e} value={e}>{ESTADO_LABEL[e]}</Option>
              ))}
            </Select>

            {/* Toggle vista */}
            <Button.Group>
              <Button
                icon={<CalendarOutlined />}
                type={viewMode === 'month' ? 'primary' : 'default'}
                onClick={() => setViewMode('month')}
              >
                Mes
              </Button>
              <Button
                type={viewMode === 'day' ? 'primary' : 'default'}
                onClick={() => { setViewMode('day'); setSelectedDate(selectedDate); }}
              >
                Día
              </Button>
            </Button.Group>

            <Button
              icon={<UnorderedListOutlined />}
              onClick={() => router.push('/ordenes-servicio')}
            >
              Ver Lista
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                const qs = viewMode === 'day' ? `?fecha=${selectedDate.format('YYYY-MM-DD')}` : '';
                router.push(`/ordenes-servicio/form/nuevo${qs}`);
              }}
            >
              Nueva Orden
            </Button>
          </Space>
        </div>
      </div>

      <div className="app-content">
        <Spin spinning={loading}>

          {/* ── Vista mensual ── */}
          {viewMode === 'month' && (
            <Calendar
              cellRender={cellRender}
              onSelect={handleDateSelect}
              onPanelChange={handlePanelChange}
              style={{
                border: `1px solid ${token.colorBorderSecondary}`,
                borderRadius: token.borderRadius,
              }}
            />
          )}

          {/* ── Vista diaria ── */}
          {viewMode === 'day' && (
            <div style={{
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: token.borderRadius,
              background: token.colorBgContainer,
              overflow: 'hidden',
            }}>
              {/* Cabecera de navegación */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 20px',
                borderBottom: `1px solid ${token.colorBorderSecondary}`,
                background: token.colorBgContainer,
              }}>
                <Button
                  icon={<LeftOutlined />}
                  onClick={() => setSelectedDate(d => d.subtract(1, 'day'))}
                />
                <Space direction="vertical" align="center" size={0}>
                  <Text strong style={{ fontSize: 16 }}>
                    {selectedDate.format('dddd D [de] MMMM [de] YYYY')}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {dayOrdenes.length} {dayOrdenes.length === 1 ? 'orden' : 'órdenes'}
                  </Text>
                </Space>
                <Space>
                  <Button
                    size="small"
                    onClick={() => setSelectedDate(dayjs())}
                    disabled={selectedDate.isSame(dayjs(), 'day')}
                  >
                    Hoy
                  </Button>
                  <Button
                    icon={<RightOutlined />}
                    onClick={() => setSelectedDate(d => d.add(1, 'day'))}
                  />
                </Space>
              </div>

              {/* Órdenes sin hora ("todo el día") */}
              {allDayOrdenes.length > 0 && (
                <div style={{
                  padding: '8px 16px 8px 72px',
                  borderBottom: `1px solid ${token.colorBorderSecondary}`,
                  background: token.colorFillAlter,
                }}>
                  <Text type="secondary" style={{ fontSize: 11, marginRight: 8 }}>Sin hora</Text>
                  <Space wrap size={4}>
                    {allDayOrdenes.map(o => (
                      <Tag
                        key={o.id}
                        color={ESTADO_HEX[o.estado]}
                        style={{ cursor: 'pointer', marginBottom: 2 }}
                        onClick={() => router.push(`/ordenes-servicio/${o.id}`)}
                      >
                        {o.folio_os}
                        {o.tecnico_nombre ? ` · ${o.tecnico_nombre.split(' ')[0]}` : ''}
                      </Tag>
                    ))}
                  </Space>
                </div>
              )}

              {/* Timeline */}
              <div style={{ display: 'flex', overflow: 'auto', maxHeight: 'calc(100vh - 280px)' }}>
                {/* Columna de horas */}
                <div style={{ width: 56, flexShrink: 0, position: 'relative', height: totalTimelineHeight }}>
                  {Array.from({ length: HOUR_END - HOUR_START + 1 }, (_, i) => {
                    const hour = HOUR_START + i;
                    return (
                      <div
                        key={hour}
                        style={{
                          position: 'absolute',
                          top: i * HOUR_HEIGHT - 8,
                          right: 8,
                          fontSize: 11,
                          color: token.colorTextTertiary,
                          userSelect: 'none',
                        }}
                      >
                        {`${String(hour).padStart(2, '0')}:00`}
                      </div>
                    );
                  })}
                </div>

                {/* Grid + eventos */}
                <div style={{ flex: 1, position: 'relative', height: totalTimelineHeight, minWidth: 0 }}>
                  {/* Líneas horizontales de hora */}
                  {Array.from({ length: HOUR_END - HOUR_START + 1 }, (_, i) => (
                    <div
                      key={i}
                      style={{
                        position: 'absolute',
                        top: i * HOUR_HEIGHT,
                        left: 0,
                        right: 0,
                        borderTop: `1px solid ${token.colorBorderSecondary}`,
                      }}
                    />
                  ))}
                  {/* Líneas de media hora (más suaves) */}
                  {Array.from({ length: HOUR_END - HOUR_START }, (_, i) => (
                    <div
                      key={`half-${i}`}
                      style={{
                        position: 'absolute',
                        top: i * HOUR_HEIGHT + HOUR_HEIGHT / 2,
                        left: 0,
                        right: 0,
                        borderTop: `1px dashed ${token.colorBorderSecondary}`,
                        opacity: 0.5,
                      }}
                    />
                  ))}

                  {/* Línea "ahora" si es hoy */}
                  {selectedDate.isSame(dayjs(), 'day') && (() => {
                    const now = dayjs();
                    const nowMin = now.hour() * 60 + now.minute();
                    const nowTop = (nowMin - HOUR_START * 60) * (HOUR_HEIGHT / 60);
                    if (nowTop < 0 || nowTop > totalTimelineHeight) return null;
                    return (
                      <div style={{
                        position: 'absolute',
                        top: nowTop,
                        left: 0,
                        right: 0,
                        display: 'flex',
                        alignItems: 'center',
                        zIndex: 10,
                        pointerEvents: 'none',
                      }}>
                        <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ff4d4f', flexShrink: 0 }} />
                        <div style={{ flex: 1, height: 2, background: '#ff4d4f' }} />
                      </div>
                    );
                  })()}

                  {/* Eventos con hora */}
                  {timedWithLanes.map(({ orden: o, lane, totalLanes }) => {
                    const { top, height } = eventStyle(o);
                    const laneW = 100 / totalLanes;
                    return (
                      <Tooltip
                        key={o.id}
                        title={
                          <div>
                            <div><strong>{o.folio_os}</strong></div>
                            {o.cliente_nombre && <div>👤 {o.cliente_nombre}</div>}
                            {o.tecnico_nombre && <div>🔧 {o.tecnico_nombre}</div>}
                            {o.direccion_servicio && <div>📍 {o.direccion_servicio}</div>}
                          </div>
                        }
                      >
                        <div
                          onClick={() => router.push(`/ordenes-servicio/${o.id}`)}
                          style={{
                            position: 'absolute',
                            top,
                            left: `calc(${lane * laneW}% + 4px)`,
                            width: `calc(${laneW}% - 8px)`,
                            height,
                            background: ESTADO_BG[o.estado],
                            borderLeft: `3px solid ${ESTADO_HEX[o.estado]}`,
                            borderRadius: 4,
                            padding: '3px 6px',
                            overflow: 'hidden',
                            cursor: 'pointer',
                            zIndex: 5,
                            boxSizing: 'border-box',
                            transition: 'filter 0.15s',
                          }}
                          onMouseEnter={e => (e.currentTarget.style.filter = 'brightness(0.95)')}
                          onMouseLeave={e => (e.currentTarget.style.filter = '')}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                            <Text strong style={{ fontSize: 11, fontFamily: 'monospace' }}>{o.folio_os}</Text>
                            <Tag color={ESTADO_HEX[o.estado]} style={{ margin: 0, fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>
                              {ESTADO_LABEL[o.estado]}
                            </Tag>
                          </div>
                          {height > 36 && (
                            <div style={{ fontSize: 10, color: token.colorTextSecondary, marginTop: 1 }}>
                              {o.hora_inicio!.slice(0, 5)}{o.hora_fin ? ` – ${o.hora_fin.slice(0, 5)}` : ''}
                              {o.tecnico_nombre ? ` · ${o.tecnico_nombre.split(' ')[0]}` : ''}
                            </div>
                          )}
                          {height > 52 && o.cliente_nombre && (
                            <div style={{ fontSize: 10, color: token.colorTextTertiary, marginTop: 1, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                              {o.cliente_nombre}
                            </div>
                          )}
                        </div>
                      </Tooltip>
                    );
                  })}

                  {/* Mensaje cuando no hay eventos con hora */}
                  {timedOrdenes.length === 0 && allDayOrdenes.length === 0 && (
                    <div style={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      textAlign: 'center',
                      pointerEvents: 'none',
                    }}>
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={
                          <span style={{ color: token.colorTextTertiary }}>
                            Sin órdenes para este día
                          </span>
                        }
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

        </Spin>
      </div>

      {/* Drawer: órdenes del día seleccionado (vista mensual) */}
      <Drawer
        title={`Órdenes del ${selectedDate.format('DD [de] MMMM [de] YYYY')}`}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={420}
        extra={
          <Button
            size="small"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push(`/ordenes-servicio/form/nuevo?fecha=${selectedDate.format('YYYY-MM-DD')}`)}
          >
            Nueva
          </Button>
        }
      >
        {drawerOrdenes.length === 0 ? (
          <Empty description="Sin órdenes este día" />
        ) : (
          <List
            dataSource={drawerOrdenes}
            renderItem={(o) => (
              <List.Item
                actions={[
                  <Button
                    key="ver"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => router.push(`/ordenes-servicio/${o.id}`)}
                  />,
                  <Button
                    key="edit"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => router.push(`/ordenes-servicio/form/${o.id}`)}
                  />,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong style={{ fontFamily: 'monospace' }}>{o.folio_os}</Text>
                      <Badge status={ESTADO_COLOR[o.estado] as any} text={ESTADO_LABEL[o.estado]} />
                      <Tag color={PRIORIDAD_COLOR[o.prioridad]}>{o.prioridad}</Tag>
                    </Space>
                  }
                  description={
                    <div>
                      {o.hora_inicio && (
                        <div style={{ fontSize: 12 }}>
                          🕐 {o.hora_inicio.slice(0, 5)}
                          {o.hora_fin ? ` – ${o.hora_fin.slice(0, 5)}` : ''}
                        </div>
                      )}
                      {o.cliente_nombre && <div style={{ fontSize: 12 }}>👤 {o.cliente_nombre}</div>}
                      {o.tecnico_nombre && <div style={{ fontSize: 12 }}>🔧 {o.tecnico_nombre}</div>}
                      {o.direccion_servicio && (
                        <div style={{ fontSize: 12, color: token.colorTextTertiary }}>
                          📍 {o.direccion_servicio}
                        </div>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Drawer>
    </>
  );
}
