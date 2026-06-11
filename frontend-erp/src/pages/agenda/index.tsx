// pages/agenda/index.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import { PageHeader } from '@/components/PageHeader';
import {
  Calendar,
  Tag,
  Button,
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
  EditOutlined,
  CalendarOutlined,
  LeftOutlined,
  RightOutlined,
  FilePdfOutlined,
} from '@ant-design/icons';
import type { CalendarProps } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import 'dayjs/locale/es';
import OrdenServicioModal from '@/components/OrdenServicioModal';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import ordenServicioService, {
  OrdenServicioListOut,
  EstadoOS,
} from '@/services/ordenServicioService';
import {
  ESTADO_COLOR,
  ESTADO_HEX,
  ESTADO_LABEL,
} from '@/utils/ordenServicioConstants';

dayjs.locale('es');

const { Text } = Typography;
const { Option } = Select;

// ── Constantes de la vista diaria ────────────────────────────────────────────
const HOUR_START  = 7;   // 7:00 AM
const HOUR_END    = 21;  // 9:00 PM
const HOUR_HEIGHT = 60;  // px por hora

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

  // ── Estado sincronizado con la URL ──────────────────────────────────────────
  // /agenda?view=day&fecha=2026-05-25&estado=PENDIENTE
  //
  // IMPORTANTE: todos los valores derivados de router.query se memorizan para
  // que las dependencias del useEffect sean estables entre renders.

  const viewMode: 'month' | 'day' = React.useMemo(() => {
    const v = router.query.view;
    return v === 'day' ? 'day' : 'month';
  }, [router.query.view]);

  // Usamos un string YYYY-MM-DD como dep estable; el objeto Dayjs lo derivamos aparte.
  const fechaStr: string = React.useMemo(() => {
    const f = router.query.fecha;
    const s = Array.isArray(f) ? f[0] : f;
    return s && dayjs(s).isValid() ? s : dayjs().format('YYYY-MM-DD');
  }, [router.query.fecha]);

  const selectedDate: Dayjs = React.useMemo(() => dayjs(fechaStr), [fechaStr]);

  const estadoFilter: EstadoOS | undefined = React.useMemo(() => {
    const e = router.query.estado;
    const s = Array.isArray(e) ? e[0] : e;
    return s ? (s as EstadoOS) : undefined;
  }, [router.query.estado]);

  // Helper para actualizar parámetros de la URL sin recargar la página.
  // Usamos ref para evitar que router sea una dependencia inestable.
  const routerRef = React.useRef(router);
  useEffect(() => { routerRef.current = router; });

  const setQuery = useCallback((patch: Record<string, string | undefined>) => {
    const q = { ...routerRef.current.query, ...patch };
    Object.keys(q).forEach(k => { if (q[k] === undefined) delete q[k]; });
    routerRef.current.replace({ pathname: '/agenda', query: q }, undefined, { shallow: true });
  }, []); // dependencias vacías: es estable toda la vida del componente

  // ── Datos ───────────────────────────────────────────────────────────────────

  const [ordenes, setOrdenes] = useState<OrdenServicioListOut[]>([]);
  const [loading, setLoading]  = useState(false);
  const [modalOrdenId, setModalOrdenId] = useState<string | null>(null);

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
    if (!router.isReady) return;
    if (viewMode === 'month') {
      const d = dayjs(fechaStr);
      fetchRange(
        d.startOf('month').format('YYYY-MM-DD'),
        d.endOf('month').format('YYYY-MM-DD')
      );
    } else {
      fetchRange(fechaStr, fechaStr);
    }
  // fechaStr y viewMode son strings primitivos → dependencias estables
  }, [router.isReady, fetchRange, fechaStr, viewMode]);

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
            <Tag
              color={ESTADO_COLOR[o.estado]}
              style={{ fontSize: 10, padding: '0 4px', lineHeight: '16px', marginRight: 0 }}
            >
              {o.hora_inicio ? `${o.hora_inicio.slice(0, 5)} ` : ''}
              {o.folio_os}
              {o.tecnico_nombre ? ` · ${o.tecnico_nombre.split(' ')[0]}` : ''}
            </Tag>
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

  // ── Vista mensual: click en día → ir a vista diaria ─────────────────────────

  const handleDateSelect = (date: Dayjs, info: { source: string }) => {
    // Solo navega a vista diaria cuando el usuario hace clic en un día concreto.
    // Ant Design también dispara onSelect al navegar entre meses (source='nav' o
    // 'month'/'year') — en esos casos solo actualizamos el mes sin cambiar la vista.
    if (info.source === 'date') {
      setQuery({ view: 'day', fecha: date.format('YYYY-MM-DD') });
    }
  };

  const handlePanelChange = (date: Dayjs) => {
    // Actualiza la fecha en la URL para que el mes visible persista y se recarguen datos.
    setQuery({ fecha: date.startOf('month').format('YYYY-MM-DD') });
  };

  // ── Vista diaria: datos del día ─────────────────────────────────────────────

  const dayOrdenes = React.useMemo(() => {
    const key = selectedDate.format('YYYY-MM-DD');
    return (ordenesByDate[key] ?? []).slice().sort((a, b) => {
      const am = toMinutes(a.hora_inicio) ?? 0;
      const bm = toMinutes(b.hora_inicio) ?? 0;
      return am - bm;
    });
  }, [ordenesByDate, selectedDate]);

  const timedOrdenes  = dayOrdenes.filter(o => o.hora_inicio);
  const allDayOrdenes = dayOrdenes.filter(o => !o.hora_inicio);

  function eventStyle(o: OrdenServicioListOut) {
    const startMin = toMinutes(o.hora_inicio)!;
    const endMin   = toMinutes(o.hora_fin) ?? (startMin + 60);
    const top      = (startMin - HOUR_START * 60) * (HOUR_HEIGHT / 60);
    const height   = Math.max((endMin - startMin) * (HOUR_HEIGHT / 60), 28);
    return { top, height };
  }

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
        if (aStart < bEnd && aEnd > bStart) usedLanes.push(result[j].lane);
      }
      let lane = 0;
      while (usedLanes.includes(lane)) lane++;
      result[i].lane = lane;
    }
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

  // ── Exportar PDF (impresión de la vista diaria) ─────────────────────────────

  const handlePrint = useCallback(() => {
    const sorted = dayOrdenes.slice().sort((a, b) => {
      const am = toMinutes(a.hora_inicio) ?? -1;
      const bm = toMinutes(b.hora_inicio) ?? -1;
      return am - bm;
    });

    /** Escapa caracteres HTML especiales antes de interpolar en document.write. */
    const esc = (s: string) =>
      s.replace(/&/g, '&amp;')
       .replace(/</g, '&lt;')
       .replace(/>/g, '&gt;')
       .replace(/"/g, '&quot;')
       .replace(/'/g, '&#39;');

    const formatHora = (h?: string | null) => h ? esc(h.slice(0, 5)) : '—';
    const rows = sorted.map((o) => `
      <tr>
        <td style="white-space:nowrap">
          ${formatHora(o.hora_inicio)}${o.hora_fin ? ` – ${formatHora(o.hora_fin)}` : ''}
        </td>
        <td>${esc(o.cliente_nombre ?? '—')}</td>
        <td>${esc(o.tecnico_nombre ?? '—')}</td>
        <td style="font-size:12px">
          ${esc(o.direccion_servicio ?? '—')}
          ${o.notas_tecnico ? `<div style="margin-top:4px;color:#0a5c91;font-style:italic;font-size:11px">📝 ${esc(o.notas_tecnico)}</div>` : ''}
        </td>
      </tr>
    `).join('');

    const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <title>Agenda ${selectedDate.format('DD-MM-YYYY')}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; color: #1a1a1a; padding: 24px; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; border-bottom: 2px solid #0a5c91; padding-bottom: 12px; }
    .header-left h1 { font-size: 22px; color: #0a5c91; font-weight: 700; }
    .header-left p  { font-size: 13px; color: #555; margin-top: 3px; text-transform: capitalize; }
    .header-right   { text-align: right; font-size: 12px; color: #888; }
    .badge-total    { background: #0a5c91; color: #fff; border-radius: 12px; padding: 2px 10px; font-size: 12px; display: inline-block; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; margin-top: 4px; }
    th { background: #f0f7ff; color: #0a5c91; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; padding: 7px 10px; text-align: left; border-bottom: 2px solid #cce0f5; }
    td { padding: 8px 10px; border-bottom: 1px solid #edf2f7; vertical-align: top; }
    tr:last-child td { border-bottom: none; }
    tr:nth-child(even) td { background: #fafcff; }
    .footer { margin-top: 18px; font-size: 11px; color: #aaa; text-align: center; border-top: 1px solid #eee; padding-top: 8px; }
    @media print {
      body { padding: 12px; }
      @page { margin: 1cm; size: A4 landscape; }
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="header-left">
      <h1>Agenda del día</h1>
      <p>${selectedDate.format('dddd D [de] MMMM [de] YYYY')}</p>
    </div>
    <div class="header-right">
      <div>NORTON CRM/ERP</div>
      <div class="badge-total">${sorted.length} ${sorted.length === 1 ? 'orden' : 'órdenes'}</div>
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th style="width:90px">Horario</th>
        <th>Cliente</th>
        <th style="width:140px">Técnico</th>
        <th>Dirección / Notas al técnico</th>
      </tr>
    </thead>
    <tbody>${rows || '<tr><td colspan="6" style="text-align:center;color:#aaa;padding:20px">Sin órdenes para este día</td></tr>'}</tbody>
  </table>
  <div class="footer">Generado el ${dayjs().format('DD/MM/YYYY HH:mm')} · Sistema NORTON CRM/ERP</div>
  <script>window.onload = () => { window.print(); window.onafterprint = () => window.close(); }<\/script>
</body>
</html>`;

    const win = window.open('', '_blank', 'width=1000,height=700');
    if (!win) { message.warning('Permite ventanas emergentes para exportar el PDF'); return; }
    win.document.write(html);
    win.document.close();
  }, [dayOrdenes, selectedDate]);

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <>
      <PageHeader
        title="Agenda"
        extra={
          <>
            <Select
              placeholder="Filtrar por estado"
              allowClear
              style={{ width: 160 }}
              value={estadoFilter}
              onChange={(v) => setQuery({ estado: v ?? undefined })}
            >
              {(Object.keys(ESTADO_LABEL) as EstadoOS[]).map((e) => (
                <Option key={e} value={e}>
                  <Tag color={ESTADO_COLOR[e]} style={{ margin: 0 }}>{ESTADO_LABEL[e]}</Tag>
                </Option>
              ))}
            </Select>

            {/* Toggle vista */}
            <Button.Group>
              <Button
                icon={<CalendarOutlined />}
                type={viewMode === 'month' ? 'primary' : 'default'}
                onClick={() => setQuery({ view: 'month' })}
              >
                Mes
              </Button>
              <Button
                type={viewMode === 'day' ? 'primary' : 'default'}
                onClick={() => setQuery({ view: 'day', fecha: selectedDate.format('YYYY-MM-DD') })}
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
          </>
        }
      />

      <div className="app-content">
        <Spin spinning={loading}>

          {/* ── Vista mensual ── */}
          {viewMode === 'month' && (
            <Calendar
              value={selectedDate}
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
              }}>
                <Button
                  icon={<LeftOutlined />}
                  onClick={() => setQuery({ fecha: selectedDate.subtract(1, 'day').format('YYYY-MM-DD') })}
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
                    onClick={() => setQuery({ fecha: dayjs().format('YYYY-MM-DD') })}
                    disabled={selectedDate.isSame(dayjs(), 'day')}
                  >
                    Hoy
                  </Button>
                  <Button
                    icon={<RightOutlined />}
                    onClick={() => setQuery({ fecha: selectedDate.add(1, 'day').format('YYYY-MM-DD') })}
                  />
                  <Button
                    icon={<FilePdfOutlined />}
                    onClick={handlePrint}
                    title="Exportar agenda del día como PDF"
                  >
                    PDF
                  </Button>
                </Space>
              </div>

              {/* Órdenes sin hora */}
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
                        color={ESTADO_COLOR[o.estado]}
                        style={{ cursor: 'pointer', marginBottom: 2 }}
                        onClick={() => setModalOrdenId(o.id)}
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
                      <div key={hour} style={{
                        position: 'absolute',
                        top: i * HOUR_HEIGHT - 8,
                        right: 8,
                        fontSize: 11,
                        color: token.colorTextTertiary,
                        userSelect: 'none',
                      }}>
                        {`${String(hour).padStart(2, '0')}:00`}
                      </div>
                    );
                  })}
                </div>

                {/* Grid + eventos */}
                <div style={{ flex: 1, position: 'relative', height: totalTimelineHeight, minWidth: 0 }}>
                  {/* Líneas de hora */}
                  {Array.from({ length: HOUR_END - HOUR_START + 1 }, (_, i) => (
                    <div key={i} style={{
                      position: 'absolute', top: i * HOUR_HEIGHT, left: 0, right: 0,
                      borderTop: `1px solid ${token.colorBorderSecondary}`,
                    }} />
                  ))}
                  {/* Líneas de media hora */}
                  {Array.from({ length: HOUR_END - HOUR_START }, (_, i) => (
                    <div key={`half-${i}`} style={{
                      position: 'absolute', top: i * HOUR_HEIGHT + HOUR_HEIGHT / 2, left: 0, right: 0,
                      borderTop: `1px dashed ${token.colorBorderSecondary}`, opacity: 0.5,
                    }} />
                  ))}

                  {/* Línea "ahora" */}
                  {selectedDate.isSame(dayjs(), 'day') && (() => {
                    const now = dayjs();
                    const nowTop = (now.hour() * 60 + now.minute() - HOUR_START * 60) * (HOUR_HEIGHT / 60);
                    if (nowTop < 0 || nowTop > totalTimelineHeight) return null;
                    return (
                      <div style={{
                        position: 'absolute', top: nowTop, left: 0, right: 0,
                        display: 'flex', alignItems: 'center', zIndex: 10, pointerEvents: 'none',
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
                            {o.cliente_nombre    && <div>👤 {o.cliente_nombre}</div>}
                            {o.tecnico_nombre    && <div>🔧 {o.tecnico_nombre}</div>}
                            {o.direccion_servicio && <div>📍 {o.direccion_servicio}</div>}
                          </div>
                        }
                      >
                        <div
                          onClick={() => setModalOrdenId(o.id)}
                          style={{
                            position: 'absolute',
                            top,
                            left: `calc(${lane * laneW}% + 4px)`,
                            width: `calc(${laneW}% - 8px)`,
                            height,
                            background: `${ESTADO_HEX[o.estado]}22`,
                            borderLeft: `3px solid ${ESTADO_HEX[o.estado]}`,
                            border: `1px solid ${ESTADO_HEX[o.estado]}55`,
                            borderLeftWidth: 3,
                            borderRadius: 4,
                            padding: '3px 6px',
                            overflow: 'hidden',
                            cursor: 'pointer',
                            zIndex: 5,
                            boxSizing: 'border-box',
                            transition: 'filter 0.15s',
                          }}
                          onMouseEnter={e => (e.currentTarget.style.filter = 'brightness(1.15)')}
                          onMouseLeave={e => (e.currentTarget.style.filter = '')}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                            <Text strong style={{ fontSize: 11, fontFamily: 'monospace' }}>{o.folio_os}</Text>
                            <Tag color={ESTADO_COLOR[o.estado]} style={{ margin: 0, fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>
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

                  {/* Empty state */}
                  {timedOrdenes.length === 0 && allDayOrdenes.length === 0 && (
                    <div style={{
                      position: 'absolute', top: '50%', left: '50%',
                      transform: 'translate(-50%, -50%)', textAlign: 'center',
                    }}>
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={<span style={{ color: token.colorTextTertiary }}>Sin órdenes para este día</span>}
                      >
                        <Button
                          type="primary"
                          icon={<PlusOutlined />}
                          onClick={() =>
                            router.push(`/ordenes-servicio/form/nuevo?fecha=${selectedDate.format('YYYY-MM-DD')}`)
                          }
                        >
                          Crear orden para este día
                        </Button>
                      </Empty>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

        </Spin>
      </div>

      {/* Modal de detalle (vista diaria) */}
      <OrdenServicioModal
        ordenId={modalOrdenId}
        onClose={() => setModalOrdenId(null)}
        onEstadoChanged={() => {
          fetchRange(
            selectedDate.format('YYYY-MM-DD'),
            selectedDate.format('YYYY-MM-DD')
          );
        }}
        onDeleted={() => {
          fetchRange(
            selectedDate.format('YYYY-MM-DD'),
            selectedDate.format('YYYY-MM-DD')
          );
        }}
      />
    </>
  );
}
