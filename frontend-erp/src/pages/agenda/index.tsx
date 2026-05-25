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
} from 'antd';
import {
  PlusOutlined,
  UnorderedListOutlined,
  EyeOutlined,
  EditOutlined,
} from '@ant-design/icons';
import type { CalendarProps } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import ordenServicioService, {
  OrdenServicioListOut,
  EstadoOS,
} from '@/services/ordenServicioService';
import { ESTADO_COLOR, ESTADO_LABEL, PRIORIDAD_COLOR } from '@/utils/ordenServicioConstants';

const { Text } = Typography;
const { Option } = Select;

// ── Componente ────────────────────────────────────────────────────────────────

export default function AgendaPage() {
  const router = useRouter();
  const { token } = theme.useToken();
  const { selectedEmpresaId } = useEmpresaSelector();

  const [ordenes, setOrdenes] = useState<OrdenServicioListOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(dayjs());
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Dayjs | null>(null);
  const [estadoFilter, setEstadoFilter] = useState<EstadoOS | undefined>(undefined);

  // ── Carga de datos ──────────────────────────────────────────────────────────

  const fetchMonth = useCallback(
    async (month: Dayjs) => {
      if (!selectedEmpresaId) return;
      setLoading(true);
      try {
        const params: any = {
          fecha_desde: month.startOf('month').format('YYYY-MM-DD'),
          fecha_hasta: month.endOf('month').format('YYYY-MM-DD'),
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
    fetchMonth(currentMonth);
  }, [fetchMonth, currentMonth]);

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

  // ── Render de celda ─────────────────────────────────────────────────────────

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

  // ── Selección de día ────────────────────────────────────────────────────────

  const handleDateSelect = (date: Dayjs) => {
    setSelectedDate(date);
    const key = date.format('YYYY-MM-DD');
    if (ordenesByDate[key]?.length) {
      setDrawerOpen(true);
    }
  };

  const handlePanelChange = (date: Dayjs) => {
    setCurrentMonth(date);
  };

  const drawerOrdenes = selectedDate
    ? (ordenesByDate[selectedDate.format('YYYY-MM-DD')] ?? [])
    : [];

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
            <Button
              icon={<UnorderedListOutlined />}
              onClick={() => router.push('/ordenes-servicio')}
            >
              Ver Lista
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => router.push('/ordenes-servicio/form/nuevo')}
            >
              Nueva Orden
            </Button>
          </Space>
        </div>
      </div>

      <div className="app-content">
        {/* Calendario */}
        <Spin spinning={loading}>
          <Calendar
            cellRender={cellRender}
            onSelect={handleDateSelect}
            onPanelChange={handlePanelChange}
            style={{ border: `1px solid ${token.colorBorderSecondary}`, borderRadius: token.borderRadius }}
          />
        </Spin>
      </div>

      {/* Drawer: órdenes del día seleccionado */}
      <Drawer
        title={
          selectedDate
            ? `Órdenes del ${selectedDate.format('DD [de] MMMM [de] YYYY')}`
            : 'Órdenes'
        }
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={420}
        extra={
          <Button
            size="small"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/ordenes-servicio/form/nuevo')}
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
