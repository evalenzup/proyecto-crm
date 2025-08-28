// pages/facturas/index.tsx
'use client';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import {
  Table,
  message,
  Button,
  Space,
  Select,
  DatePicker,
  Card,
  Grid,
  theme,
} from 'antd';
import { PlusOutlined, EditOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import api from '@/lib/axios';
import { Breadcrumbs } from '@/components/Breadcrumb';
import debounce from 'lodash/debounce';
import dayjs, { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;
const { useToken } = theme;
const { useBreakpoint } = Grid;

type EstatusCFDI = 'BORRADOR' | 'TIMBRADA' | 'CANCELADA';
type EstatusPago = 'PAGADA' | 'NO_PAGADA';

interface FacturaRow {
  id: string;
  empresa_id: string;
  cliente_id: string;
  serie: string;
  folio: number;
  creado_en: string;
  estatus: EstatusCFDI;
  status_pago: EstatusPago;
  total: number;
  cliente?: { id: string; nombre_comercial: string };
}

interface FacturasListResponse {
  items: FacturaRow[];
  total: number;
  limit: number;
  offset: number;
}

interface Opcion { label: string; value: string }

// ───────────────────────────────────────────────────────────
// Utils
const formatDateTijuana = (iso: string) => {
  const utc = iso?.endsWith('Z') ? iso : `${iso}Z`;
  return new Date(utc).toLocaleString('es-MX', {
    timeZone: 'America/Tijuana',
    dateStyle: 'short',
    timeStyle: 'medium',
  });
};

const toLimitOffset = (pagination: TablePaginationConfig) => {
  const page = pagination.current ?? 1;
  const pageSize = pagination.pageSize ?? 10;
  const offset = (page - 1) * pageSize;
  return { limit: pageSize, offset };
};

// calcula una altura para scroll.y que aproveche la pantalla
const useTableHeight = () => {
  const ref = useRef<HTMLDivElement | null>(null);
  const [y, setY] = useState<number | undefined>(undefined);

  useEffect(() => {
    const calc = () => {
      if (!ref.current) return setY(undefined);
      const rect = ref.current.getBoundingClientRect();
      // deja ~220px para margen inferior/paginación
      const h = window.innerHeight - rect.top - 220;
      setY(h > 240 ? h : 240);
    };
    calc();
    window.addEventListener('resize', calc);
    return () => window.removeEventListener('resize', calc);
  }, []);

  return { containerRef: ref, tableY: y };
};

// ───────────────────────────────────────────────────────────

const FacturasIndexPage: React.FC = () => {
  const router = useRouter();
  const { token } = useToken();
  const screens = useBreakpoint();
  const { containerRef, tableY } = useTableHeight();

  // Tabla
  const [rows, setRows] = useState<FacturaRow[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [loading, setLoading] = useState(false);

  // Paginación
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 10,
    showSizeChanger: true,
    pageSizeOptions: [10, 20, 50, 100],
  });

  // Filtros
  const [empresasOptions, setEmpresasOptions] = useState<Opcion[]>([]);
  const [empresaId, setEmpresaId] = useState<string | undefined>(undefined);

  const [clienteOptions, setClienteOptions] = useState<Opcion[]>([]);
  const [clienteId, setClienteId] = useState<string | undefined>(undefined);
  const [clienteQuery, setClienteQuery] = useState<string>('');

  const [estatus, setEstatus] = useState<EstatusCFDI | undefined>(undefined);
  const [estatusPago, setEstatusPago] = useState<EstatusPago | undefined>(undefined);
  const [rangoFechas, setRangoFechas] = useState<[Dayjs, Dayjs] | null>(null);

  // Cargar empresas
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/empresas/');
        setEmpresasOptions(
          (data || []).map((e: any) => ({ value: e.id, label: e.nombre_comercial || e.nombre }))
        );
      } catch {
        message.error('No se pudieron cargar empresas');
      }
    })();
  }, []);

  // Autocomplete clientes
  const buscarClientes = useCallback(async (q: string) => {
    if (!q || q.trim().length < 3) {
      setClienteOptions([]);
      return;
    }
    try {
      const { data } = await api.get(`/clientes/busqueda?q=${encodeURIComponent(q)}`);
      setClienteOptions(
        (data || []).slice(0, 20).map((c: any) => ({
          value: c.id,
          label: c.nombre_comercial || c.nombre || c.razon_social || 'Cliente',
        }))
      );
    } catch {
      setClienteOptions([]);
    }
  }, []);
  const debouncedBuscarClientes = useMemo(() => debounce(buscarClientes, 300), [buscarClientes]);

  // Fetch facturas
  const fetchFacturas = async (pag: TablePaginationConfig = pagination) => {
    const { limit, offset } = toLimitOffset(pag);
    const params: Record<string, any> = { limit, offset, order_by: 'serie_folio', order_dir: 'desc' };
    if (empresaId) params.empresa_id = empresaId;
    if (clienteId) params.cliente_id = clienteId;
    if (estatus) params.estatus = estatus;
    if (estatusPago) params.status_pago = estatusPago;
    if (rangoFechas) {
      params.fecha_desde = rangoFechas[0].format('YYYY-MM-DD');
      params.fecha_hasta = rangoFechas[1].format('YYYY-MM-DD');
    }

    console.log("Enviando parámetros a /api/facturas/:", params);

    setLoading(true);
    try {
      const { data } = await api.get<FacturasListResponse>('/facturas/', { params });
      console.log("Respuesta recibida de /api/facturas/:", data);
      setRows(data.items || []);
      setTotalRows(data.total || 0);
      setPagination((p) => ({ ...p, current: pag.current, pageSize: pag.pageSize }));
    } catch {
      message.error('No se pudieron cargar las facturas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFacturas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const aplicarFiltros = () => fetchFacturas({ ...pagination, current: 1 });

  // Columnas
  const columns: ColumnsType<FacturaRow> = [
    { title: 'Folio', key: 'folio', render: (_: any, r) => `${r.serie ?? ''}-${r.folio ?? ''}`, width: 110 },
    { title: 'Fecha', dataIndex: 'creado_en', key: 'creado_en', render: (v: string) => formatDateTijuana(v), width: 180 },
    { title: 'Cliente', key: 'cliente', render: (_: any, r) => r.cliente?.nombre_comercial || '—' },
    { title: 'Estatus CFDI', dataIndex: 'estatus', key: 'estatus', width: 130 },
    { title: 'Estatus Pago', dataIndex: 'status_pago', key: 'status_pago', width: 130 },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 140,
      align: 'right',
      render: (v: string | number) => {
        const num = Number(v);
        return (Number.isFinite(num) ? num : 0).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
      },
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 90,
      render: (_: any, r) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => router.push(`/facturas/form/${r.id}`)} />
      ),
    },
  ];

  // Sumatoria
  const sumatoriaMostrada = useMemo(
    () => rows.reduce((acc, r) => acc + (Number(r.total) || 0), 0),
    [rows]
  );

  // ───────────────────────────────────────────────────────────
  // UI

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">Facturas</h1>
        </div>
        <div className="app-page-header__right">
          <Space wrap>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => router.push('/facturas/form')}>
              Nueva factura
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => fetchFacturas()}>
              Recargar
            </Button>
          </Space>
        </div>
      </div>
      <div className="app-content" ref={containerRef}>
        <Card
          size="small"
          bordered
          bodyStyle={{ padding: 12 }}
          style={{
            // reduce márgenes externos
            marginTop: 4,
          }}
        >
          {/* Filtros STICKY para que no "bailen" al hacer scroll */}
          <div
            style={{
              position: 'sticky',
              top: 0,
              zIndex: 9,
              padding: screens.lg ? '8px 8px 12px' : '8px',
              marginBottom: 8,
              background: token.colorBgContainer,
              borderRadius: 8,
              boxShadow: token.boxShadowSecondary,
            }}
          >
            <Space wrap size={[8, 8]}>
              <Select
                allowClear
                placeholder="Empresa"
                style={{ width: 220 }}
                options={empresasOptions}
                value={empresaId}
                onChange={setEmpresaId}
                onClear={() => setEmpresaId(undefined)}
              />
              <Select
                allowClear
                showSearch
                placeholder="Cliente (escribe ≥ 3 letras)"
                style={{ width: 280 }}
                filterOption={false}
                onSearch={(val) => { setClienteQuery(val); debouncedBuscarClientes(val); }}
                onChange={(val) => setClienteId(val)}
                onClear={() => { setClienteQuery(''); setClienteId(undefined); setClienteOptions([]); }}
                notFoundContent={clienteQuery && clienteQuery.length < 3 ? 'Escribe al menos 3 caracteres' : undefined}
                options={clienteOptions}
                suffixIcon={<SearchOutlined />}
                value={clienteId}
              />
              <Select
                allowClear
                placeholder="Estatus CFDI"
                style={{ width: 180 }}
                value={estatus}
                onChange={(v: EstatusCFDI | undefined) => setEstatus(v)}
                options={[
                  { value: 'BORRADOR', label: 'BORRADOR' },
                  { value: 'TIMBRADA', label: 'TIMBRADA' },
                  { value: 'CANCELADA', label: 'CANCELADA' },
                ]}
              />
              <Select
                allowClear
                placeholder="Estatus Pago"
                style={{ width: 180 }}
                value={estatusPago}
                onChange={(v: EstatusPago | undefined) => setEstatusPago(v)}
                options={[
                  { value: 'PAGADA', label: 'PAGADA' },
                  { value: 'NO_PAGADA', label: 'NO_PAGADA' },
                ]}
              />
              <RangePicker
                onChange={(range) => setRangoFechas(range as any)}
                value={rangoFechas as any}
                placeholder={['Desde', 'Hasta']}
                allowClear
              />
              <Button type="primary" onClick={aplicarFiltros}>Aplicar filtros</Button>
            </Space>
          </div>

          <Table<FacturaRow>
            size="small"
            rowKey="id"
            columns={columns}
            dataSource={rows}
            loading={loading}
            pagination={{
              ...pagination,
              total: totalRows,
              showTotal: (t) => `${t} facturas`,
            }}
            onChange={(pag) => fetchFacturas(pag)}
            scroll={{ x: 980, y: tableY }}
            summary={() => (
              <Table.Summary>
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0} colSpan={5} align="right">
                    <strong>Total mostrado:</strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={5} align="right">
                    <strong>
                      {sumatoriaMostrada.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}
                    </strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={6} />
                </Table.Summary.Row>
              </Table.Summary>
            )}
            locale={{ emptyText: 'No hay facturas' }}
          />
        </Card>
      </div>
    </>
  );
};

export default FacturasIndexPage;
