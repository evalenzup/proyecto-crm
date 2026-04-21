// src/pages/reportes/index.tsx
import React, { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  Row, Col, Card, Statistic, Typography, Tooltip, Space,
  Select, Skeleton, Alert, Table, Button, Tag, DatePicker,
  Tabs,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  BarChartOutlined, FileTextOutlined, ArrowUpOutlined, ArrowDownOutlined,
  RiseOutlined, FallOutlined, DollarOutlined, TeamOutlined,
  UserAddOutlined, WarningOutlined, DownloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import { useQuery } from '@tanstack/react-query';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEmpresaContext } from '@/context/EmpresaContext';
import {
  reportesService,
  FinancieroMes,
  EgresoCatItem,
  EmbudoItem,
  TopCliente,
  EmpresaFinanciero,
} from '@/services/reportesService';
import { getAgingReport } from '@/services/cobranzaService';
import { AgingReportResponse, ClienteAging } from '@/types/cobranza';

// SSR-safe ECharts import
const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// ─── Helpers ────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    maximumFractionDigits: 0,
  }).format(n);

const fmtMonth = (periodo: string) =>
  dayjs(periodo + '-01').format('MMM YYYY');

const fmtMonthShort = (periodo: string) =>
  dayjs(periodo + '-01').format('MMM YY');

// ─── Tab Financiero ──────────────────────────────────────────────────────────

// Paleta de colores por empresa (hasta 8)
const EMPRESA_COLORS = ['#1677ff', '#52c41a', '#fa8c16', '#722ed1', '#13c2c2', '#eb2f96', '#fadb14', '#a0d911'];

interface TabFinancieroProps {
  params: { fechaInicio: string; fechaFin: string; empresaId?: string; rfc?: string };
  isAllEmpresas: boolean;
}

const TabFinanciero: React.FC<TabFinancieroProps> = ({ params, isAllEmpresas }) => {
  const { data: finData, isLoading: finLoading } = useQuery({
    queryKey: ['reportes-financiero', params],
    queryFn: () => reportesService.getFinanciero(params),
  });

  const { data: egresosData, isLoading: egresosLoading } = useQuery({
    queryKey: ['reportes-egresos-cat', params],
    queryFn: () => reportesService.getEgresosCategorias(params),
  });

  // Desglose por empresa — solo cuando se ven "todas"
  const { data: porEmpresaData, isLoading: porEmpresaLoading } = useQuery({
    queryKey: ['reportes-por-empresa', params],
    queryFn: () => reportesService.getFinancieroPorEmpresa(params),
    enabled: isAllEmpresas,
  });

  const loading = finLoading || egresosLoading || (isAllEmpresas && porEmpresaLoading);
  const kpis = finData?.kpis;
  const meses = finData?.meses ?? [];
  const egresos = egresosData ?? [];
  const porEmpresa: EmpresaFinanciero[] = porEmpresaData ?? [];

  // ── CSV export ───────────────────────────────────────────────────────────
  const handleExportCSV = useCallback(() => {
    if (!meses.length) return;
    const header = 'Mes,Facturado,Cobrado,Por Cobrar,Egresos,Utilidad,Margen %';
    const rows = meses.map(m =>
      [
        fmtMonth(m.periodo),
        m.facturado,
        m.cobrado,
        m.por_cobrar,
        m.egresos,
        m.utilidad,
        m.margen_pct,
      ].join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `estado_resultados_${params.fechaInicio}_${params.fechaFin}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [meses, params]);

  // ── Table columns ────────────────────────────────────────────────────────
  const columns: ColumnsType<FinancieroMes> = [
    {
      title: 'Mes',
      dataIndex: 'periodo',
      render: (v: string) => fmtMonth(v),
      width: 100,
    },
    { title: 'Facturado', dataIndex: 'facturado', render: fmt, align: 'right' },
    { title: 'Cobrado', dataIndex: 'cobrado', render: fmt, align: 'right' },
    { title: 'Por Cobrar', dataIndex: 'por_cobrar', render: fmt, align: 'right' },
    { title: 'Egresos', dataIndex: 'egresos', render: fmt, align: 'right' },
    {
      title: 'Utilidad',
      dataIndex: 'utilidad',
      align: 'right',
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#52c41a' : '#f5222d', fontWeight: 500 }}>{fmt(v)}</span>
      ),
    },
    {
      title: 'Margen %',
      dataIndex: 'margen_pct',
      align: 'right',
      render: (v: number) => {
        const color = v >= 20 ? '#52c41a' : v >= 0 ? '#fa8c16' : '#f5222d';
        return <span style={{ color, fontWeight: 500 }}>{v.toFixed(1)}%</span>;
      },
    },
  ];

  // ── Summary row ──────────────────────────────────────────────────────────
  const summary = () => {
    if (!kpis) return null;
    const marginColor = kpis.margen_pct >= 20 ? '#52c41a' : kpis.margen_pct >= 0 ? '#fa8c16' : '#f5222d';
    const utilColor = kpis.utilidad >= 0 ? '#52c41a' : '#f5222d';
    return (
      <Table.Summary.Row style={{ fontWeight: 700, background: '#fafafa' }}>
        <Table.Summary.Cell index={0}>Total</Table.Summary.Cell>
        <Table.Summary.Cell index={1} align="right">{fmt(kpis.total_facturado)}</Table.Summary.Cell>
        <Table.Summary.Cell index={2} align="right">{fmt(kpis.cobrado)}</Table.Summary.Cell>
        <Table.Summary.Cell index={3} align="right">{fmt(kpis.por_cobrar)}</Table.Summary.Cell>
        <Table.Summary.Cell index={4} align="right">{fmt(kpis.egresos)}</Table.Summary.Cell>
        <Table.Summary.Cell index={5} align="right">
          <span style={{ color: utilColor }}>{fmt(kpis.utilidad)}</span>
        </Table.Summary.Cell>
        <Table.Summary.Cell index={6} align="right">
          <span style={{ color: marginColor }}>{kpis.margen_pct.toFixed(1)}%</span>
        </Table.Summary.Cell>
      </Table.Summary.Row>
    );
  };

  // ── ECharts: Flujo de Caja (adaptativo según modo) ───────────────────────
  const xAxisData = meses.map(m => fmtMonthShort(m.periodo));
  const utilidadAcum = meses.reduce<number[]>((acc, m, i) => {
    acc.push((acc[i - 1] ?? 0) + m.utilidad);
    return acc;
  }, []);

  const flujoCajaOption = isAllEmpresas && porEmpresa.length > 0
    ? {
        // ── Modo "todas": barras apiladas por empresa ──
        animation: true,
        tooltip: {
          trigger: 'axis',
          formatter: (ps: any[]) => {
            const title = ps[0]?.axisValueLabel ?? '';
            const lines = ps.map((p: any) => `${p.marker} ${p.seriesName}: ${fmt(p.value)}`);
            const total = ps.filter(p => p.seriesType === 'bar').reduce((s: number, p: any) => s + (p.value ?? 0), 0);
            return `${title}<br/>${lines.join('<br/>')}<br/><strong>Total cobrado: ${fmt(total)}</strong>`;
          },
        },
        legend: {
          data: [...porEmpresa.map(e => e.nombre_comercial), 'Utilidad Acum.'],
          type: 'scroll',
        },
        xAxis: { type: 'category', data: xAxisData },
        yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmt(v) } },
        series: [
          // Una serie de barras apiladas por empresa
          ...porEmpresa.map((emp, i) => ({
            name: emp.nombre_comercial,
            type: 'bar',
            stack: 'cobrado',
            data: emp.meses.map(m => m.cobrado),
            itemStyle: { color: EMPRESA_COLORS[i % EMPRESA_COLORS.length] },
          })),
          // Línea de utilidad acumulada total
          {
            name: 'Utilidad Acum.',
            type: 'line',
            data: utilidadAcum,
            itemStyle: { color: '#f5222d' },
            lineStyle: { width: 2 },
            symbol: 'circle',
            z: 10,
          },
        ],
      }
    : {
        // ── Modo empresa individual / RFC: barras cobrado + egresos ──
        animation: true,
        tooltip: {
          trigger: 'axis',
          formatter: (ps: any[]) => {
            const lines = ps.map((p: any) => `${p.marker} ${p.seriesName}: ${fmt(p.value)}`);
            return `${ps[0]?.axisValueLabel}<br/>${lines.join('<br/>')}`;
          },
        },
        legend: { data: ['Cobrado', 'Egresos', 'Utilidad Acum.'] },
        xAxis: { type: 'category', data: xAxisData },
        yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmt(v) } },
        series: [
          { name: 'Cobrado', type: 'bar', data: meses.map(m => m.cobrado), itemStyle: { color: '#52c41a' } },
          { name: 'Egresos', type: 'bar', data: meses.map(m => m.egresos), itemStyle: { color: '#f5222d' } },
          {
            name: 'Utilidad Acum.',
            type: 'line',
            data: utilidadAcum,
            itemStyle: { color: '#1677ff' },
            lineStyle: { width: 2 },
            symbol: 'circle',
          },
        ],
      };

  // ── Columnas tabla desglose por empresa ──────────────────────────────────
  const colsEmpresa: ColumnsType<EmpresaFinanciero> = [
    {
      title: 'Empresa',
      dataIndex: 'nombre_comercial',
      render: (v: string, _: EmpresaFinanciero, idx: number) => (
        <Space>
          <span style={{
            display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
            background: EMPRESA_COLORS[idx % EMPRESA_COLORS.length],
          }} />
          {v}
        </Space>
      ),
    },
    { title: 'Facturado',  dataIndex: 'facturado',  render: fmt, align: 'right' },
    { title: 'Cobrado',    dataIndex: 'cobrado',    render: fmt, align: 'right' },
    { title: 'Por Cobrar', dataIndex: 'por_cobrar', render: fmt, align: 'right' },
    { title: 'Egresos',    dataIndex: 'egresos',    render: fmt, align: 'right' },
    {
      title: 'Utilidad',
      dataIndex: 'utilidad',
      align: 'right',
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#52c41a' : '#f5222d', fontWeight: 500 }}>{fmt(v)}</span>
      ),
    },
    {
      title: 'Margen %',
      dataIndex: 'margen_pct',
      align: 'right',
      render: (v: number) => {
        const color = v >= 20 ? '#52c41a' : v >= 0 ? '#fa8c16' : '#f5222d';
        return <span style={{ color, fontWeight: 500 }}>{v.toFixed(1)}%</span>;
      },
    },
  ];

  // ── ECharts: Egresos por Categoría ───────────────────────────────────────
  const egresosCatOption = {
    animation: true,
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.name}: ${fmt(p.value)} (${p.data.pct?.toFixed(1) ?? 0}%)`,
    },
    series: [
      {
        name: 'Egresos',
        type: 'pie',
        radius: ['40%', '70%'],
        data: egresos.map((e: EgresoCatItem) => ({ name: e.name, value: e.value, pct: e.pct })),
        label: { show: true, formatter: '{b}: {d}%' },
      },
    ],
  };

  const egresosCatColumns: ColumnsType<EgresoCatItem> = [
    { title: 'Categoría', dataIndex: 'name' },
    { title: 'Monto', dataIndex: 'value', render: fmt, align: 'right' },
    { title: '%', dataIndex: 'pct', render: (v: number) => `${v.toFixed(1)}%`, align: 'right' },
  ];

  if (loading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* KPI cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<Space><FileTextOutlined />Total Facturado</Space>}
              value={kpis?.total_facturado ?? 0}
              formatter={v => fmt(Number(v))}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<Space><ArrowUpOutlined />Cobrado</Space>}
              value={kpis?.cobrado ?? 0}
              formatter={v => fmt(Number(v))}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<Space><ArrowDownOutlined />Egresos</Space>}
              value={kpis?.egresos ?? 0}
              formatter={v => fmt(Number(v))}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={
                <Space>
                  {(kpis?.utilidad ?? 0) >= 0
                    ? <RiseOutlined style={{ color: '#52c41a' }} />
                    : <FallOutlined style={{ color: '#f5222d' }} />}
                  Utilidad
                </Space>
              }
              value={kpis?.utilidad ?? 0}
              formatter={v => fmt(Number(v))}
              valueStyle={{ color: (kpis?.utilidad ?? 0) >= 0 ? '#52c41a' : '#f5222d' }}
              suffix={
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {' '}margen {kpis?.margen_pct?.toFixed(1)}%
                </Text>
              }
            />
          </Card>
        </Col>
      </Row>

      {/* Desglose por empresa — solo en modo "todas" */}
      {isAllEmpresas && (
        <Card
          title="Desglose por Empresa"
          loading={porEmpresaLoading}
        >
          <Table
            dataSource={porEmpresa}
            columns={colsEmpresa}
            rowKey="empresa_id"
            pagination={false}
            size="small"
            scroll={{ x: 700 }}
            summary={() => {
              if (!kpis) return null;
              return (
                <Table.Summary.Row style={{ fontWeight: 700, background: '#fafafa' }}>
                  <Table.Summary.Cell index={0}>Total</Table.Summary.Cell>
                  <Table.Summary.Cell index={1} align="right">{fmt(kpis.total_facturado)}</Table.Summary.Cell>
                  <Table.Summary.Cell index={2} align="right">{fmt(kpis.cobrado)}</Table.Summary.Cell>
                  <Table.Summary.Cell index={3} align="right">{fmt(kpis.por_cobrar)}</Table.Summary.Cell>
                  <Table.Summary.Cell index={4} align="right">{fmt(kpis.egresos)}</Table.Summary.Cell>
                  <Table.Summary.Cell index={5} align="right">
                    <span style={{ color: kpis.utilidad >= 0 ? '#52c41a' : '#f5222d' }}>{fmt(kpis.utilidad)}</span>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={6} align="right">
                    <span style={{ color: kpis.margen_pct >= 20 ? '#52c41a' : kpis.margen_pct >= 0 ? '#fa8c16' : '#f5222d' }}>
                      {kpis.margen_pct.toFixed(1)}%
                    </span>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              );
            }}
          />
        </Card>
      )}

      {/* Estado de Resultados */}
      <Card
        title="Estado de Resultados"
        extra={
          <Button
            icon={<DownloadOutlined />}
            size="small"
            onClick={handleExportCSV}
            disabled={!meses.length}
          >
            CSV
          </Button>
        }
      >
        <Table
          dataSource={meses}
          columns={columns}
          rowKey="periodo"
          pagination={false}
          size="small"
          scroll={{ x: 700 }}
          summary={summary}
        />
      </Card>

      {/* Flujo de Caja */}
      <Card title="Flujo de Caja">
        {meses.length ? (
          <ReactECharts option={flujoCajaOption} style={{ height: 320 }} />
        ) : (
          <Text type="secondary">Sin datos en el periodo seleccionado</Text>
        )}
      </Card>

      {/* Egresos por Categoría */}
      <Card title="Egresos por Categoría">
        {egresos.length ? (
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <ReactECharts option={egresosCatOption} style={{ height: 280 }} />
            </Col>
            <Col xs={24} md={12}>
              <Table
                dataSource={egresos}
                columns={egresosCatColumns}
                rowKey="name"
                pagination={false}
                size="small"
              />
            </Col>
          </Row>
        ) : (
          <Text type="secondary">Sin datos de egresos por categoría</Text>
        )}
      </Card>
    </div>
  );
};

// ─── Tab Ventas ──────────────────────────────────────────────────────────────

interface TabVentasProps {
  params: { fechaInicio: string; fechaFin: string; empresaId?: string; rfc?: string };
}

const FUNNEL_ETAPAS_MAIN = ['Borrador', 'Enviado', 'Aceptado', 'Facturado'];
const FUNNEL_ETAPAS_EXTRA = ['Rechazado', 'Caducado'];

const TabVentas: React.FC<TabVentasProps> = ({ params }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['reportes-ventas', params],
    queryFn: () => reportesService.getVentas(params),
  });

  if (isLoading) return <Skeleton active paragraph={{ rows: 8 }} />;

  const kpis = data?.kpis;
  const embudo: EmbudoItem[] = data?.embudo ?? [];
  const meses = data?.meses ?? [];

  const funnelMain = embudo.filter(e => FUNNEL_ETAPAS_MAIN.includes(e.etapa));
  const funnelExtra = embudo.filter(e => FUNNEL_ETAPAS_EXTRA.includes(e.etapa));

  const funnelOption = {
    animation: true,
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => {
        const item = funnelMain.find(e => e.etapa === p.name);
        return `${p.name}: ${item?.cantidad ?? 0} presupuestos<br/>${fmt(item?.monto ?? 0)}`;
      },
    },
    series: [
      {
        name: 'Embudo',
        type: 'funnel',
        left: '10%',
        width: '80%',
        label: { show: true, position: 'inside', formatter: '{b}' },
        data: funnelMain.map(e => ({ name: e.etapa, value: e.cantidad })),
        color: ['#1677ff', '#36cfc9', '#52c41a', '#722ed1'],
      },
    ],
  };

  const evolucionOption = {
    animation: true,
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        const lines = params.map((p: any) => `${p.marker} ${p.seriesName}: ${fmt(p.value)}`);
        return `${params[0]?.axisValueLabel}<br/>${lines.join('<br/>')}`;
      },
    },
    legend: { data: ['Cerrado', 'Pipeline'] },
    xAxis: {
      type: 'category',
      data: meses.map(m => fmtMonthShort(m.periodo)),
    },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmt(v) } },
    series: [
      {
        name: 'Cerrado',
        type: 'line',
        data: meses.map(m => m.monto_cerrado),
        itemStyle: { color: '#52c41a' },
        lineStyle: { color: '#52c41a' },
        symbol: 'circle',
      },
      {
        name: 'Pipeline',
        type: 'line',
        data: meses.map(m => m.monto_pipeline),
        itemStyle: { color: '#fa8c16' },
        lineStyle: { color: '#fa8c16' },
        symbol: 'circle',
      },
    ],
  };

  const conversionColor = (kpis?.tasa_conversion_pct ?? 0) >= 50 ? '#52c41a' : '#fa8c16';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* KPI cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<Space><FileTextOutlined />Total Presupuestos</Space>}
              value={kpis?.total_presupuestos ?? 0}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<Space><RiseOutlined />Tasa de Conversión</Space>}
              value={kpis?.tasa_conversion_pct ?? 0}
              precision={1}
              suffix="%"
              valueStyle={{ color: conversionColor }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<Space><DollarOutlined />Pipeline Abierto</Space>}
              value={kpis?.pipeline_abierto ?? 0}
              formatter={v => fmt(Number(v))}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={<Space><BarChartOutlined />Ticket Promedio</Space>}
              value={kpis?.ticket_promedio ?? 0}
              formatter={v => fmt(Number(v))}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Embudo */}
      <Card title="Embudo de Conversión">
        {funnelMain.length ? (
          <>
            <ReactECharts option={funnelOption} style={{ height: 320 }} />
            {funnelExtra.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {funnelExtra.map(e => (
                  <Tag key={e.etapa} color={e.etapa === 'Rechazado' ? 'error' : 'default'}>
                    {e.etapa}: {e.cantidad} ({fmt(e.monto)})
                  </Tag>
                ))}
              </div>
            )}
          </>
        ) : (
          <Text type="secondary">Sin datos de embudo</Text>
        )}
      </Card>

      {/* Evolución mensual */}
      <Card title="Evolución de Ventas">
        {meses.length ? (
          <ReactECharts option={evolucionOption} style={{ height: 300 }} />
        ) : (
          <Text type="secondary">Sin datos en el periodo seleccionado</Text>
        )}
      </Card>
    </div>
  );
};

// ─── Tab Clientes ────────────────────────────────────────────────────────────

interface TabClientesProps {
  params: { fechaInicio: string; fechaFin: string; empresaId?: string; rfc?: string };
}

const TabClientes: React.FC<TabClientesProps> = ({ params }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['reportes-clientes', params],
    queryFn: () => reportesService.getClientes(params),
  });

  if (isLoading) return <Skeleton active paragraph={{ rows: 8 }} />;

  const kpis = data?.kpis;
  const topClientes: TopCliente[] = data?.top_clientes ?? [];
  const meses = data?.meses ?? [];

  const topClientesColumns: ColumnsType<TopCliente & { idx: number }> = [
    { title: '#', dataIndex: 'idx', width: 40 },
    { title: 'Nombre Comercial', dataIndex: 'nombre_comercial' },
    { title: 'RFC', dataIndex: 'rfc', width: 120 },
    {
      title: 'Monto',
      dataIndex: 'monto',
      render: fmt,
      align: 'right',
      defaultSortOrder: 'descend',
      sorter: (a, b) => a.monto - b.monto,
    },
    { title: '# Facturas', dataIndex: 'facturas', align: 'right' },
    { title: 'Ticket Promedio', dataIndex: 'ticket_promedio', render: fmt, align: 'right' },
    {
      title: 'Última Factura',
      dataIndex: 'ultima_factura',
      render: (v: string | null) => v ? dayjs(v).format('DD/MM/YYYY') : '—',
    },
  ];

  const stackedBarOption = {
    animation: true,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['Nuevos', 'Recurrentes'] },
    xAxis: {
      type: 'category',
      data: meses.map(m => fmtMonthShort(m.periodo)),
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: 'Nuevos',
        type: 'bar',
        stack: 'total',
        data: meses.map(m => m.nuevos),
        itemStyle: { color: '#52c41a' },
      },
      {
        name: 'Recurrentes',
        type: 'bar',
        stack: 'total',
        data: meses.map(m => m.recurrentes),
        itemStyle: { color: '#1677ff' },
      },
    ],
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* KPI cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={<Space><TeamOutlined />Clientes Activos</Space>}
              value={kpis?.total_activos ?? 0}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={<Space><UserAddOutlined />Clientes Nuevos</Space>}
              value={kpis?.nuevos ?? 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Tooltip title="Sin factura en últimos 90 días">
              <Statistic
                title={
                  <Space>
                    <WarningOutlined />
                    En Riesgo
                    <WarningOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                  </Space>
                }
                value={kpis?.en_riesgo ?? 0}
                valueStyle={{ color: (kpis?.en_riesgo ?? 0) > 0 ? '#f5222d' : '#52c41a' }}
              />
            </Tooltip>
          </Card>
        </Col>
      </Row>

      {/* Top clientes */}
      <Card title="Top Clientes por Facturación">
        <Table
          dataSource={topClientes.slice(0, 15).map((c, i) => ({ ...c, idx: i + 1 }))}
          columns={topClientesColumns}
          rowKey="rfc"
          pagination={false}
          size="small"
          scroll={{ x: 800 }}
        />
      </Card>

      {/* Nuevos vs Recurrentes */}
      <Card title="Clientes Nuevos vs Recurrentes">
        {meses.length ? (
          <ReactECharts option={stackedBarOption} style={{ height: 300 }} />
        ) : (
          <Text type="secondary">Sin datos en el periodo seleccionado</Text>
        )}
      </Card>
    </div>
  );
};

// ─── Tab Cobranza ────────────────────────────────────────────────────────────

interface TabCobranzaProps {
  empresaId: string | undefined;
}

const TabCobranza: React.FC<TabCobranzaProps> = ({ empresaId }) => {
  const hasEmpresa = !!empresaId;

  const { data, isLoading } = useQuery<AgingReportResponse>({
    queryKey: ['aging-report', empresaId],
    queryFn: () => getAgingReport(empresaId),
    enabled: hasEmpresa,
  });

  if (!hasEmpresa) {
    return (
      <Alert
        type="info"
        showIcon
        message="Selecciona una empresa específica para ver el reporte de cartera."
        description="Este reporte requiere seleccionar una empresa individual, no un grupo RFC o la vista general."
        style={{ maxWidth: 600 }}
      />
    );
  }

  if (isLoading) return <Skeleton active paragraph={{ rows: 8 }} />;

  const items: ClienteAging[] = data?.items ?? [];
  const totalVencido = items.reduce(
    (acc, c) => acc + c.vencido_0_30 + c.vencido_31_60 + c.vencido_61_90 + c.vencido_mas_90,
    0
  );
  const totalPorVencer = items.reduce((acc, c) => acc + c.por_vencer, 0);
  const totalCartera = items.reduce((acc, c) => acc + c.total_deuda, 0);

  const agingColumns: ColumnsType<ClienteAging> = [
    { title: 'Cliente', dataIndex: 'nombre_cliente', ellipsis: true },
    { title: 'Por Vencer', dataIndex: 'por_vencer', render: fmt, align: 'right' },
    { title: '0–30 días', dataIndex: 'vencido_0_30', render: fmt, align: 'right' },
    { title: '31–60 días', dataIndex: 'vencido_31_60', render: fmt, align: 'right' },
    { title: '61–90 días', dataIndex: 'vencido_61_90', render: fmt, align: 'right' },
    {
      title: '>90 días',
      dataIndex: 'vencido_mas_90',
      align: 'right',
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#f5222d' : undefined }}>{fmt(v)}</span>
      ),
    },
    {
      title: 'Total',
      dataIndex: 'total_deuda',
      render: (v: number) => <strong>{fmt(v)}</strong>,
      align: 'right',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Vencido"
              value={totalVencido}
              formatter={v => fmt(Number(v))}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Por Vencer"
              value={totalPorVencer}
              formatter={v => fmt(Number(v))}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Cartera"
              value={totalCartera}
              formatter={v => fmt(Number(v))}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Antigüedad de Cartera">
        <Table
          dataSource={items}
          columns={agingColumns}
          rowKey="cliente_id"
          pagination={false}
          size="small"
          scroll={{ x: 900 }}
        />
      </Card>
    </div>
  );
};

// ─── Page ────────────────────────────────────────────────────────────────────

const ReportesPage: React.FC = () => {
  const { empresas, rfcGroups, isAdmin } = useEmpresaContext();

  // '__all__' = todas las empresas (sin filtro)
  const [selectorValue, setSelectorValue] = useState<string>('__all__');
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(11, 'month').startOf('month'),
    dayjs().startOf('month'),
  ]);
  const [activeTab, setActiveTab] = useState('financiero');

  // Derived params
  const rawSelector = selectorValue === '__all__' ? undefined : selectorValue;
  const empresaId = rawSelector && !rawSelector.startsWith('rfc:') ? rawSelector : undefined;
  const rfcFilter = rawSelector?.startsWith('rfc:') ? rawSelector.slice(4) : undefined;
  const fechaInicio = dateRange[0].format('YYYY-MM');
  const fechaFin = dateRange[1].format('YYYY-MM');
  const params = { fechaInicio, fechaFin, empresaId, rfc: rfcFilter };

  // Selector options
  const selectorOptions = [
    { label: 'General (todas)', value: '__all__' },
    ...(rfcGroups.length > 0
      ? [
          {
            label: <span style={{ fontSize: 11, fontWeight: 600 }}>Grupos RFC</span>,
            options: rfcGroups.map(g => ({
              label: `RFC ${g.rfc} (${g.empresas.length} emp.)`,
              value: `rfc:${g.rfc}`,
            })),
          },
        ]
      : []),
    {
      label: <span style={{ fontSize: 11, fontWeight: 600 }}>Empresas</span>,
      options: empresas.map(e => ({ label: e.nombre_comercial, value: e.id })),
    },
  ];

  const tabBarExtra = (
    <Space wrap>
      {isAdmin && (
        <Select
          value={selectorValue}
          onChange={setSelectorValue}
          options={selectorOptions}
          style={{ width: 260 }}
          placeholder="Empresa"
        />
      )}
      <RangePicker
        picker="month"
        value={dateRange}
        onChange={vals => {
          if (vals && vals[0] && vals[1]) {
            setDateRange([vals[0], vals[1]]);
          }
        }}
        disabledDate={current => {
          // Max 24-month range: disable months that are more than 24 months from start
          return current && current > dayjs().endOf('month');
        }}
        format="MMM YYYY"
        allowClear={false}
      />
    </Space>
  );

  const tabItems = [
    {
      key: 'financiero',
      label: (
        <Space>
          <BarChartOutlined />
          Financiero
        </Space>
      ),
      children: activeTab === 'financiero' ? <TabFinanciero params={params} isAllEmpresas={selectorValue === '__all__'} /> : null,
    },
    {
      key: 'ventas',
      label: (
        <Space>
          <RiseOutlined />
          Ventas
        </Space>
      ),
      children: activeTab === 'ventas' ? <TabVentas params={params} /> : null,
    },
    {
      key: 'clientes',
      label: (
        <Space>
          <TeamOutlined />
          Clientes
        </Space>
      ),
      children: activeTab === 'clientes' ? <TabClientes params={params} /> : null,
    },
    {
      key: 'cobranza',
      label: (
        <Space>
          <DollarOutlined />
          Cuentas por Cobrar
        </Space>
      ),
      children: activeTab === 'cobranza' ? <TabCobranza empresaId={empresaId} /> : null,
    },
  ];

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">
            <BarChartOutlined style={{ marginRight: 8 }} />
            Reportes
          </h1>
        </div>
      </div>

      <div className="app-content">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          tabBarExtraContent={tabBarExtra}
          items={tabItems}
          destroyInactiveTabPane={false}
        />
      </div>
    </>
  );
};

export default ReportesPage;
