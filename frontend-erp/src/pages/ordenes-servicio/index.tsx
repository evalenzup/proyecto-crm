// pages/ordenes-servicio/index.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import { PageHeader } from '@/components/PageHeader';
import {
  Table,
  Button,
  Popconfirm,
  Space,
  Input,
  Select,
  Tag,
  message,
  theme,
  Badge,
  Tooltip,
  DatePicker,
  Card,
} from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  SearchOutlined,
  CalendarOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { debounce } from 'lodash';
import type { ColumnsType } from 'antd/es/table';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import { useTableHeight } from '@/hooks/useTableHeight';
import ordenServicioService, {
  OrdenServicioListOut,
  EstadoOS,
  PrioridadOS,
} from '@/services/ordenServicioService';
import { ESTADO_COLOR, ESTADO_LABEL, PRIORIDAD_COLOR } from '@/utils/ordenServicioConstants';
import dayjs from 'dayjs';

const { Option } = Select;
const { RangePicker } = DatePicker;

// ── Componente ────────────────────────────────────────────────────────────────

const OrdenesServicioPage: React.FC = () => {
  const router = useRouter();
  const { token } = theme.useToken();
  const { containerRef, tableY } = useTableHeight();
  const { selectedEmpresaId } = useEmpresaSelector();

  const [data, setData] = useState<OrdenServicioListOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sort, setSort] = useState<{ order_by?: string; order_dir?: 'asc' | 'desc' }>({});
  const [searchInput, setSearchInput] = useState('');
  const [q, setQ] = useState<string | undefined>(undefined);
  const [estadoFilter, setEstadoFilter] = useState<EstadoOS | undefined>(undefined);
  const [prioridadFilter, setPrioridadFilter] = useState<PrioridadOS | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  const fetchData = useCallback(
    async (page: number, size: number, query?: string) => {
      if (!selectedEmpresaId) return;
      setLoading(true);
      try {
        const params: any = {
          limit: size,
          offset: (page - 1) * size,
          empresa_id: selectedEmpresaId,
        };
        if (query) params.q = query;
        if (estadoFilter) params.estado = estadoFilter;
        if (prioridadFilter) params.prioridad = prioridadFilter;

        if (dateRange?.[0]) params.fecha_desde = dateRange[0].format('YYYY-MM-DD');
        if (dateRange?.[1]) params.fecha_hasta = dateRange[1].format('YYYY-MM-DD');
        if (sort.order_by) { params.order_by = sort.order_by; params.order_dir = sort.order_dir; }

        const result = await ordenServicioService.list(params);
        setData(result.items);
        setTotal(result.total);
      } catch (e: any) {
        if (!e?._handled) message.error('Error al cargar las órdenes de servicio');
      } finally {
        setLoading(false);
      }
    },
    [selectedEmpresaId, estadoFilter, prioridadFilter, dateRange, sort]
  );

  const so = (key: string): 'ascend' | 'descend' | undefined =>
    sort.order_by === key ? (sort.order_dir === 'asc' ? 'ascend' : 'descend') : undefined;
  const handleTableChange = (_pag: any, _filters: any, sorter: any) => {
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    const next = s && s.order
      ? { order_by: String(s.columnKey ?? s.field), order_dir: (s.order === 'ascend' ? 'asc' : 'desc') as 'asc' | 'desc' }
      : {};
    if (next.order_by !== sort.order_by || next.order_dir !== sort.order_dir) {
      setSort(next);
      setCurrentPage(1);
    }
  };

  useEffect(() => {
    fetchData(currentPage, pageSize, q);
  }, [fetchData, currentPage, pageSize, q]);

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedEmpresaId, estadoFilter, prioridadFilter, dateRange]);

  const debouncedSearch = useCallback(
    debounce((value: string) => {
      setQ(value || undefined);
      setCurrentPage(1);
    }, 400),
    []
  );

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchInput(e.target.value);
    debouncedSearch(e.target.value);
  };

  const handleDelete = async (id: string) => {
    try {
      await ordenServicioService.delete(id);
      message.success('Orden eliminada');
      fetchData(currentPage, pageSize, q);
    } catch (e: any) {
      if (!e?._handled) message.error('Error al eliminar la orden');
    }
  };

  const columns: ColumnsType<OrdenServicioListOut> = [
    {
      title: 'Folio',
      dataIndex: 'folio_os',
      key: 'folio_os',
      width: 100,
      sorter: true,
      sortOrder: so('folio_os'),
      render: (v: string) => <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{v}</span>,
    },
    {
      title: 'Fecha',
      dataIndex: 'fecha_programada',
      key: 'fecha_programada',
      width: 110,
      sorter: true,
      sortOrder: so('fecha_programada'),
      render: (v: string) => dayjs(v).format('DD/MM/YYYY'),
    },
    {
      title: 'Horario',
      key: 'horario',
      width: 120,
      render: (_: any, r: OrdenServicioListOut) => {
        if (!r.hora_inicio) return <span style={{ color: token.colorTextTertiary }}>—</span>;
        const fin = r.hora_fin ? ` – ${r.hora_fin.slice(0, 5)}` : '';
        return `${r.hora_inicio.slice(0, 5)}${fin}`;
      },
    },
    {
      title: 'Estado',
      dataIndex: 'estado',
      key: 'estado',
      width: 120,
      sorter: true,
      sortOrder: so('estado'),
      render: (v: EstadoOS) => (
        <Badge status={ESTADO_COLOR[v] as any} text={ESTADO_LABEL[v]} />
      ),
    },
    {
      title: 'Prioridad',
      dataIndex: 'prioridad',
      key: 'prioridad',
      width: 90,
      sorter: true,
      sortOrder: so('prioridad'),
      render: (v: PrioridadOS) => (
        <Tag color={PRIORIDAD_COLOR[v]}>{v}</Tag>
      ),
    },
    {
      title: 'Cliente',
      dataIndex: 'cliente_nombre',
      key: 'cliente_nombre',
      ellipsis: true,
      render: (v: string | null) => v ?? '—',
    },
    {
      title: 'Técnico',
      dataIndex: 'tecnico_nombre',
      key: 'tecnico_nombre',
      ellipsis: true,
      render: (v: string | null) => v ?? <span style={{ color: token.colorTextTertiary }}>Sin asignar</span>,
    },
    {
      title: 'Dirección',
      dataIndex: 'direccion_servicio',
      key: 'direccion_servicio',
      ellipsis: true,
      render: (v: string | null) => v ?? '—',
    },
    {
      title: 'Precio',
      dataIndex: 'precio_acordado',
      key: 'precio_acordado',
      width: 110,
      align: 'right',
      render: (v: number | null) =>
        v != null
          ? `$${Number(v).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
          : '—',
    },
    {
      title: 'Factura',
      key: 'factura',
      width: 120,
      render: (_: any, r: OrdenServicioListOut) =>
        r.factura_folio ? (
          <Tooltip title={r.factura_estatus ?? ''}>
            <a onClick={(e) => { e.stopPropagation(); router.push(`/facturas/form/${r.factura_id}`); }}
               style={{ fontFamily: 'monospace' }}>
              {r.factura_folio}
            </a>
          </Tooltip>
        ) : <span style={{ color: token.colorTextTertiary }}>—</span>,
    },
    {
      title: '',
      key: 'actions',
      width: 110,
      align: 'center',
      render: (_: any, record: OrdenServicioListOut) => (
        <Space size={4}>
          <Tooltip title="Ver detalle">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => router.push(`/ordenes-servicio/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Editar">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => router.push(`/ordenes-servicio/form/${record.id}`)}
            />
          </Tooltip>
          <Popconfirm
            title="¿Eliminar esta orden?"
            onConfirm={() => handleDelete(record.id)}
            okText="Sí"
            cancelText="No"
          >
            <Tooltip title="Eliminar">
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Órdenes de Servicio"
        extra={
          <>
            <Button
              icon={<CalendarOutlined />}
              onClick={() => router.push('/agenda')}
            >
              Ver Agenda
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => router.push('/ordenes-servicio/form/nuevo')}
            >
              Nueva Orden
            </Button>
          </>
        }
      />

      <div className="app-content" ref={containerRef}>
        {/* Filtros */}
        <Card size="small" variant="borderless" styles={{ body: { padding: 12 } }} style={{ marginBottom: 8 }}>
          <Space wrap>
            <Input
              placeholder="Buscar por folio o cliente…"
              prefix={<SearchOutlined />}
              value={searchInput}
              onChange={handleSearchChange}
              allowClear
              style={{ width: 240, minWidth: 160 }}
            />
            <Select
              placeholder="Estado"
              allowClear
              style={{ width: 150, minWidth: 130 }}
              value={estadoFilter}
              onChange={(v) => setEstadoFilter(v)}
            >
              {(Object.keys(ESTADO_LABEL) as EstadoOS[]).map((e) => (
                <Option key={e} value={e}>{ESTADO_LABEL[e]}</Option>
              ))}
            </Select>
            <Select
              placeholder="Prioridad"
              allowClear
              style={{ width: 120, minWidth: 110 }}
              value={prioridadFilter}
              onChange={(v) => setPrioridadFilter(v)}
            >
              {(['BAJA', 'MEDIA', 'ALTA', 'URGENTE'] as PrioridadOS[]).map((p) => (
                <Option key={p} value={p}>{p}</Option>
              ))}
            </Select>
            <RangePicker
              format="DD/MM/YYYY"
              onChange={(dates) => setDateRange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null])}
              placeholder={['Desde', 'Hasta']}
              style={{ minWidth: 200 }}
            />
          </Space>
        </Card>

        {/* Tabla */}
        <Table<OrdenServicioListOut>
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          size="small"
          scroll={{ x: 900, y: tableY }}
          locale={{ emptyText: 'No hay órdenes de servicio' }}
          onChange={handleTableChange}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `${t} registros`,
            onChange: (page, size) => {
              setCurrentPage(page);
              if (size) setPageSize(size);
            },
          }}
        />
      </div>
    </>
  );
};

export default OrdenesServicioPage;
