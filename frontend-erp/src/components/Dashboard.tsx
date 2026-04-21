// src/components/Dashboard.tsx
import React, { useEffect, useMemo, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Typography, Tooltip, Space, Skeleton, DatePicker, Button, Switch, Tag } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, InfoCircleOutlined, CalendarOutlined, WarningOutlined, FileTextOutlined, ClockCircleOutlined, CheckCircleOutlined, StopOutlined, RiseOutlined, FallOutlined, TeamOutlined, PieChartOutlined as PieChartIcon, DollarOutlined, ApartmentOutlined } from '@ant-design/icons';
import { useRouter } from 'next/router';
import { dashboardService, IngresosEgresosOut, EgresoCategoriaMetric, AlertasMetrics, ReportesMetrics } from '@/services/dashboardService';
import { getAgingReport } from '@/services/cobranzaService';
import { AgingReportResponse } from '@/types/cobranza';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import dynamic from 'next/dynamic';

const ReactECharts = dynamic(() => import('echarts-for-react'), {
  ssr: false,
  loading: () => <Skeleton active paragraph={{ rows: 8 }} style={{ height: 360, padding: 20 }} />,
});

import dayjs, { Dayjs } from 'dayjs';

const currency = (n: number, ccy: string) =>
  new Intl.NumberFormat('es-MX', { style: 'currency', currency: ccy || 'MXN', maximumFractionDigits: 2 }).format(
    Number.isFinite(n) ? n : 0
  );

export const Dashboard: React.FC = () => {
  const router = useRouter();
  const [cardsData, setCardsData] = useState<IngresosEgresosOut | null>(null);
  const [egresosCatData, setEgresosCatData] = useState<EgresoCategoriaMetric[]>([]);
  const [agingData, setAgingData] = useState<AgingReportResponse | null>(null);
  const [trendData, setTrendData] = useState<IngresosEgresosOut | null>(null);
  const [alertas, setAlertas] = useState<AlertasMetrics | null>(null);
  const [reportes, setReportes] = useState<ReportesMetrics | null>(null);
  const [loadingFinance, setLoadingFinance] = useState(false);

  const [selectedMonth, setSelectedMonth] = useState<Dayjs | null>(dayjs());

  // Empresa global del sidebar
  const { selectedEmpresaId, rfcGroups } = useEmpresaSelector();

  // RFC group selector local al dashboard
  // Si la empresa seleccionada pertenece a un grupo RFC, mostramos la opción de agrupar
  const [useRfcGroup, setUseRfcGroup] = useState(false);
  const currentRfcGroup = rfcGroups.find(g =>
    g.empresas.some(e => e.id === selectedEmpresaId)
  );
  // Reset useRfcGroup if the selected empresa no longer belongs to a group
  useEffect(() => {
    if (!currentRfcGroup) setUseRfcGroup(false);
  }, [currentRfcGroup]);

  const empresaId = useRfcGroup ? undefined : selectedEmpresaId;
  const rfcFilter = useRfcGroup && currentRfcGroup ? currentRfcGroup.rfc : undefined;
  // Guard: need either empresaId or rfc to fetch data
  const hasFilter = !!(empresaId || rfcFilter);

  // 2. Fetch Finance Metrics (Cards - Filtered by Date)
  useEffect(() => {
    if (!hasFilter) return;

    let mounted = true;
    setLoadingFinance(true);

    const date = selectedMonth || dayjs();
    const year = date.year();
    const month = date.month() + 1;

    dashboardService.getIngresosEgresos({ months: 12, empresaId, rfc: rfcFilter, year, month })
      .then((res) => {
        if (mounted) setCardsData(res);
      })
      .finally(() => {
        if (mounted) setLoadingFinance(false);
      });

    dashboardService.getEgresosPorCategoria({ year, month, empresaId, rfc: rfcFilter })
      .then(res => {
        if (mounted) setEgresosCatData(res);
      })
      .catch(console.error);

    // Fetch Aging Data — soporta empresa individual y grupo RFC
    getAgingReport(empresaId, rfcFilter)
      .then(res => {
        if (mounted) setAgingData(res);
      })
      .catch(console.error);

    // Fetch alertas KPIs
    dashboardService.getAlertas({ empresaId, rfc: rfcFilter })
      .then(res => { if (mounted) setAlertas(res); })
      .catch(console.error);

    // Fetch reportes KPIs
    dashboardService.getReportes({ empresaId, rfc: rfcFilter })
      .then(res => { if (mounted) setReportes(res); })
      .catch(console.error);

    return () => {
      mounted = false;
    };
  }, [empresaId, rfcFilter, selectedMonth]);

  // 3. Fetch Finance Trend (Chart/Table - Always last 12 months relative to NOW)
  useEffect(() => {
    if (!hasFilter) return;

    let mounted = true;
    // We can share loading state or have separate. Sharing is fine for now.

    dashboardService.getIngresosEgresos({ months: 12, empresaId, rfc: rfcFilter }) // No year/month params = current time window
      .then((res) => {
        if (mounted) setTrendData(res);
      })
      .catch(console.error);

    return () => {
      mounted = false;
    };
  }, [empresaId, rfcFilter]);

  const ccy = trendData?.currency || 'MXN';

  const chartSeries = useMemo(() => {
    return (trendData?.series || []).map((s) => ({
      period: s.period,
      ingresos: s.ingresos || 0,
      egresos: s.egresos || 0,
      diff: (s.ingresos || 0) - (s.egresos || 0),
    }));
  }, [trendData]);

  const chartOption = useMemo(() => {
    const categories = chartSeries.map((s) => s.period);
    const ingresos = chartSeries.map((s) => s.ingresos);
    const egresos = chartSeries.map((s) => s.egresos);
    const porCobrar = (trendData?.series || []).map((s) => (s.por_cobrar ?? 0));
    const porPagar = (trendData?.series || []).map((s) => (s.por_pagar ?? 0));
    const diff = chartSeries.map((s) => s.diff);
    return {
      animation: true,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        valueFormatter: (v: any) => currency(Number(v), ccy),
      },
      legend: {
        data: ['Ingresos', 'Egresos', 'Por cobrar', 'Por pagar', 'Diferencia'],
      },
      grid: { left: 16, right: 16, top: 40, bottom: 40, containLabel: true },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: { interval: 0, rotate: categories.length > 10 ? 45 : 0 },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (val: number) => currencyFormatter(val, ccy),
        },
        splitLine: { lineStyle: { color: '#f0f0f0' } },
      },
      series: [
        {
          name: 'Ingresos',
          type: 'bar',
          data: ingresos,
          itemStyle: { color: '#52c41a' },
          barGap: '10%',
          barCategoryGap: '30%'
        },
        {
          name: 'Egresos',
          type: 'bar',
          data: egresos,
          itemStyle: { color: '#f5222d' },
        },
        {
          name: 'Por cobrar',
          type: 'bar',
          data: porCobrar,
          itemStyle: { color: '#faad14' },
        },
        {
          name: 'Por pagar',
          type: 'bar',
          data: porPagar,
          itemStyle: { color: '#722ed1' },
        },
        {
          name: 'Diferencia',
          type: 'line',
          smooth: true,
          data: diff,
          itemStyle: { color: '#1677ff' },
          markLine: {
            symbol: 'none',
            label: { show: true, formatter: '0' },
            data: [{ yAxis: 0 }],
            lineStyle: { color: '#999', type: 'dashed' },
          },
        },
      ],
      dataZoom: [
        { type: 'inside' },
        { type: 'slider', height: 16, bottom: 6 },
      ],
    } as const;
  }, [chartSeries, ccy, trendData?.series]);

  const pieOption = useMemo(() => {
    return {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          return `${params.name}: ${currency(params.value, ccy)} (${params.percent}%)`;
        }
      },
      legend: {
        top: '5%',
        left: 'center'
      },
      series: [
        {
          name: 'Egresos por Categoría',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data: egresosCatData.map(item => ({ value: item.value, name: item.name }))
        }
      ]
    };
  }, [egresosCatData, ccy]);

  const agingPieOption = useMemo(() => {
    if (!agingData) return {};
    const pieData = [
      { value: agingData.items.reduce((sum, item) => sum + item.por_vencer, 0) || 0, name: 'Por Vencer', itemStyle: { color: '#87d068' } },
      { value: agingData.items.reduce((sum, item) => sum + item.vencido_0_30, 0) || 0, name: '0-30 Días', itemStyle: { color: '#faad14' } },
      { value: agingData.items.reduce((sum, item) => sum + item.vencido_31_60, 0) || 0, name: '31-60 Días', itemStyle: { color: '#fa8c16' } },
      { value: agingData.items.reduce((sum, item) => sum + item.vencido_61_90, 0) || 0, name: '61-90 Días', itemStyle: { color: '#fa541c' } },
      { value: agingData.items.reduce((sum, item) => sum + item.vencido_mas_90, 0) || 0, name: '> 90 Días', itemStyle: { color: '#f5222d' } },
    ].filter(i => i.value > 0);

    return {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          return `${params.name}: ${currency(params.value, ccy)} (${params.percent}%)`;
        }
      },
      legend: {
        top: '5%',
        left: 'center'
      },
      series: [
        {
          name: 'Cartera Por Cobrar',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data: pieData
        }
      ]
    };
  }, [agingData, ccy]);

  return (
    <Row gutter={[16, 16]}>
      {/* Filtros */}
      <Col span={24} style={{ display: 'flex', justifyContent: 'flex-end', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        {currentRfcGroup && (
          <Tooltip title={`Agrega los datos de: ${currentRfcGroup.empresas.map(e => e.nombre_comercial).join(', ')}`}>
            <Space size={8}>
              <ApartmentOutlined style={{ color: useRfcGroup ? '#1677ff' : 'rgba(0,0,0,0.45)' }} />
              <span style={{ fontSize: 13 }}>Grupo RFC {currentRfcGroup.rfc}</span>
              <Switch
                size="small"
                checked={useRfcGroup}
                onChange={setUseRfcGroup}
              />
              {useRfcGroup && (
                <Tag color="blue" style={{ margin: 0 }}>
                  {currentRfcGroup.empresas.length} empresas
                </Tag>
              )}
            </Space>
          </Tooltip>
        )}
        <DatePicker
          picker="month"
          value={selectedMonth}
          onChange={(val) => setSelectedMonth(val)}
          format="MMMM YYYY"
          allowClear={false}
          style={{ width: 200 }}
          placeholder="Seleccionar Mes"
          suffixIcon={<CalendarOutlined />}
        />
      </Col>

      {/* Sección de Ventas y Presupuestos - COMENTADA POR SOLICITUD
      <Col span={24}>
        <Typography.Title level={4}>Ventas y Presupuestos</Typography.Title>
      </Col>

      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Tasa de Conversión
                <Tooltip title="Porcentaje de presupuestos que han sido Aceptados o Facturados del total creado.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={presupuestosData?.conversion_rate ?? 0}
            suffix="%"
            precision={1}
            valueStyle={{ color: '#1890ff' }}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Pipeline (Por cerrar)
                <Tooltip title="Suma total de los presupuestos que están en estado Borrador o Enviado.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={presupuestosData?.pipeline_amount ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#faad14' }}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Ventas Perdidas
                <Tooltip title="Suma total de los presupuestos que fueron Rechazados o Caducaron.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={presupuestosData?.lost_sales_amount ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#ff4d4f' }}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Ticket Promedio
                <Tooltip title="Valor promedio de venta de los presupuestos Aceptados o Facturados.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={presupuestosData?.avg_ticket ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#52c41a' }}
          />
        </Card>
      </Col>
      */}

      {/* ── Alertas ── */}
      {alertas && (alertas.borradores_sin_timbrar > 0 || alertas.proximas_a_vencer_7_dias > 0 || alertas.facturas_timbradas_hoy >= 0 || alertas.tasa_cancelacion_mes > 0) && (
        <>
          <Col span={24}>
            <Typography.Title level={4} style={{ marginTop: 16 }}>Alertas</Typography.Title>
          </Col>

          {alertas && alertas.borradores_sin_timbrar > 0 && (
            <Col xs={24} md={12} lg={6}>
              <Card loading={loadingFinance}>
                <Statistic
                  title={
                    <Space>
                      <FileTextOutlined style={{ color: '#fa8c16' }} />
                      <span>Facturas sin timbrar</span>
                      <Tooltip title="Facturas guardadas como borrador que aún no se han enviado al SAT.">
                        <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                      </Tooltip>
                    </Space>
                  }
                  value={alertas?.borradores_sin_timbrar ?? 0}
                  valueStyle={{ color: '#fa8c16' }}
                  suffix={
                    <Button type="link" size="small" style={{ color: '#fa8c16', padding: '0 4px' }}
                      onClick={() => router.push('/facturas')}>
                      Ver →
                    </Button>
                  }
                />
              </Card>
            </Col>
          )}

          {alertas && alertas.proximas_a_vencer_7_dias > 0 && (
            <Col xs={24} md={12} lg={6}>
              <Card loading={loadingFinance}>
                <Statistic
                  title={
                    <Space>
                      <ClockCircleOutlined style={{ color: '#ff4d4f' }} />
                      <span>Facturas por vencer (7 días)</span>
                      <Tooltip title="Facturas timbradas sin pagar cuya fecha de vencimiento cae en los próximos 7 días.">
                        <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                      </Tooltip>
                    </Space>
                  }
                  value={alertas?.proximas_a_vencer_7_dias ?? 0}
                  valueStyle={{ color: '#ff4d4f' }}
                  suffix={
                    <Button type="link" size="small" style={{ color: '#ff4d4f', padding: '0 4px' }}
                      onClick={() => router.push('/cobranza')}>
                      Ver →
                    </Button>
                  }
                />
              </Card>
            </Col>
          )}

          {alertas && alertas.facturas_timbradas_hoy >= 0 && (
            <Col xs={24} md={12} lg={6}>
              <Card loading={loadingFinance}>
                <Statistic
                  title={
                    <Space>
                      <CheckCircleOutlined style={{ color: '#52c41a' }} />
                      <span>Facturas timbradas hoy</span>
                      <Tooltip title="Facturas enviadas al SAT el día de hoy (hora Tijuana).">
                        <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                      </Tooltip>
                    </Space>
                  }
                  value={alertas.facturas_timbradas_hoy}
                  valueStyle={{ color: '#52c41a' }}
                  suffix={
                    <Button type="link" size="small" style={{ color: '#52c41a', padding: '0 4px' }}
                      onClick={() => router.push('/facturas')}>
                      Ver →
                    </Button>
                  }
                />
              </Card>
            </Col>
          )}

          {alertas && alertas.tasa_cancelacion_mes > 0 && (
            <Col xs={24} md={12} lg={6}>
              <Card loading={loadingFinance}>
                <Statistic
                  title={
                    <Space>
                      <StopOutlined style={{ color: alertas.tasa_cancelacion_mes >= 10 ? '#ff4d4f' : '#faad14' }} />
                      <span>Facturas canceladas este mes</span>
                      <Tooltip title="Porcentaje de facturas emitidas este mes que fueron canceladas. Si supera el 10% puede indicar un problema operativo.">
                        <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                      </Tooltip>
                    </Space>
                  }
                  value={alertas.tasa_cancelacion_mes}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: alertas.tasa_cancelacion_mes >= 10 ? '#ff4d4f' : '#faad14' }}
                />
              </Card>
            </Col>
          )}
        </>
      )}

      <Col span={24}>
        <Typography.Title level={4} style={{ marginTop: 16 }}>Finanzas</Typography.Title>
      </Col>

      {/* ── 4 tarjetas combinadas MTD + YTD ── */}
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                <ArrowUpOutlined style={{ color: '#3f8600' }} />
                Ingresos
                <Tooltip title="Total de facturas cobradas. El valor principal es del mes seleccionado; el acumulado muestra lo del año.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={cardsData?.mtd?.ingresos ?? 0}
            formatter={v => currency(Number(v), ccy)}
            valueStyle={{ color: '#3f8600' }}
          />
          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              Año: <strong>{currency(cardsData?.ytd?.ingresos ?? 0, ccy)}</strong>
            </Typography.Text>
          </div>
        </Card>
      </Col>

      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                <ArrowDownOutlined style={{ color: '#cf1322' }} />
                Egresos
                <Tooltip title="Total de gastos pagados. El valor principal es del mes seleccionado; el acumulado muestra lo del año.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={cardsData?.mtd?.egresos ?? 0}
            formatter={v => currency(Number(v), ccy)}
            valueStyle={{ color: '#cf1322' }}
          />
          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              Año: <strong>{currency(cardsData?.ytd?.egresos ?? 0, ccy)}</strong>
            </Typography.Text>
          </div>
        </Card>
      </Col>

      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Por cobrar
                <Tooltip title="Monto pendiente de cobro. El valor principal es del mes seleccionado; el acumulado muestra lo del año.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={cardsData?.mtd?.por_cobrar ?? 0}
            formatter={v => currency(Number(v), ccy)}
            valueStyle={{ color: '#faad14' }}
          />
          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              Año: <strong>{currency(cardsData?.ytd?.por_cobrar ?? 0, ccy)}</strong>
            </Typography.Text>
          </div>
        </Card>
      </Col>

      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                <FileTextOutlined style={{ color: '#1677ff' }} />
                Total facturado
                <Tooltip title="Suma de todas las facturas timbradas del mes (cobradas + por cobrar). Refleja el volumen real de ventas emitidas.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={cardsData?.mtd?.total_facturado ?? 0}
            formatter={v => currency(Number(v), ccy)}
            valueStyle={{ color: '#1677ff' }}
          />
          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              Año: <strong>{currency(cardsData?.ytd?.total_facturado ?? 0, ccy)}</strong>
            </Typography.Text>
          </div>
        </Card>
      </Col>

      {/* ── KPIs Analíticos — fila 1: 3 métricas numéricas ── */}
      <Col xs={24} md={12} lg={8}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                <DollarOutlined />
                Ticket Promedio (mes)
                <Tooltip title="Valor promedio de cada factura timbrada este mes.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={reportes?.ticket_promedio_mes ?? 0}
            formatter={v => new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 }).format(Number(v))}
            valueStyle={{ color: '#1677ff' }}
          />
        </Card>
      </Col>

      <Col xs={24} md={12} lg={8}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                {(reportes?.margen_bruto_pct ?? 0) >= 0
                  ? <RiseOutlined style={{ color: '#52c41a' }} />
                  : <FallOutlined style={{ color: '#ff4d4f' }} />}
                Margen Bruto Estimado (mes)
                <Tooltip title="(Ingresos cobrados − Egresos) ÷ Ingresos × 100.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={reportes?.margen_bruto_pct ?? 0}
            precision={1}
            suffix="%"
            valueStyle={{ color: (reportes?.margen_bruto_pct ?? 0) >= 0 ? '#52c41a' : '#ff4d4f' }}
          />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 }).format(reportes?.ingresos_mtd ?? 0)} ingresos · {new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 }).format(reportes?.egresos_mtd ?? 0)} egresos
          </Typography.Text>
        </Card>
      </Col>

      <Col xs={24} md={12} lg={8}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                <ClockCircleOutlined />
                Días Promedio de Cobro
                <Tooltip title="Días promedio entre emisión y cobro real (últimos 90 días). Entre más bajo, mejor.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={reportes?.dias_promedio_cobro ?? 0}
            precision={1}
            suffix="días"
            valueStyle={{
              color: (reportes?.dias_promedio_cobro ?? 0) > 45 ? '#ff4d4f'
                : (reportes?.dias_promedio_cobro ?? 0) > 30 ? '#faad14'
                : '#52c41a',
            }}
          />
        </Card>
      </Col>

      {/* ── KPIs Analíticos — fila 2: 2 tarjetas más amplias ── */}
      <Col xs={24} md={12} lg={12}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                <TeamOutlined />
                Clientes sin Actividad
                <Tooltip title="Clientes sin factura timbrada en los últimos 90 días.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={reportes?.clientes_sin_actividad ?? 0}
            suffix="clientes"
            valueStyle={{ color: (reportes?.clientes_sin_actividad ?? 0) > 0 ? '#faad14' : '#52c41a' }}
          />
          {!loadingFinance && (reportes?.clientes_sin_actividad ?? 0) > 0 && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              Sin factura en los últimos 90 días
            </Typography.Text>
          )}
        </Card>
      </Col>

      <Col xs={24} md={12} lg={12}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                <PieChartIcon />
                Concentración Cartera (YTD)
                <Tooltip title="% de ingresos del año que concentra el cliente principal. Más de 40% indica dependencia.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={reportes?.concentracion_cartera_pct ?? 0}
            precision={1}
            suffix="%"
            valueStyle={{
              color: (reportes?.concentracion_cartera_pct ?? 0) >= 40 ? '#ff4d4f'
                : (reportes?.concentracion_cartera_pct ?? 0) >= 25 ? '#faad14'
                : '#52c41a',
            }}
          />
          {reportes?.concentracion_cartera_cliente && reportes.concentracion_cartera_cliente !== '—' && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {reportes.concentracion_cartera_cliente}
              {reportes.concentracion_cartera_cliente_comercial &&
               reportes.concentracion_cartera_cliente_comercial !== '—' &&
               reportes.concentracion_cartera_cliente_comercial !== reportes.concentracion_cartera_cliente && (
                <span> ({reportes.concentracion_cartera_cliente_comercial})</span>
              )}
            </Typography.Text>
          )}
        </Card>
      </Col>

      <Col span={24}>
        <Card loading={loadingFinance}>
          <Typography.Title level={5} style={{ marginBottom: 16 }}>
            Tendencia últimos 12 meses (MXN)
          </Typography.Title>
          {chartSeries.length ? (
            <ReactECharts option={chartOption as any} style={{ width: '100%', height: 360 }} notMerge lazyUpdate />
          ) : (
            <Typography.Text type="secondary">Sin datos para graficar</Typography.Text>
          )}
        </Card>
      </Col>

      <Col span={24} md={12}>
        <Card loading={loadingFinance}>
          <Typography.Title level={5} style={{ marginBottom: 16 }}>
            Egresos por Categoría ({selectedMonth?.format('MMMM') || 'Mes Actual'})
          </Typography.Title>
          {egresosCatData.length ? (
            <ReactECharts option={pieOption} style={{ width: '100%', height: 360 }} notMerge lazyUpdate />
          ) : (
            <div style={{ height: 360, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Typography.Text type="secondary">Sin datos</Typography.Text>
            </div>
          )}
        </Card>
      </Col>

      <Col span={24} md={12}>
        <Card loading={loadingFinance}>
          <Typography.Title level={5} style={{ marginBottom: 16 }}>
            Cartera Por Cobrar ({ccy})
          </Typography.Title>
          {agingData ? (
            <ReactECharts option={agingPieOption} style={{ width: '100%', height: 360 }} notMerge lazyUpdate />
          ) : (
            <div style={{ height: 360, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Typography.Text type="secondary">Sin datos</Typography.Text>
            </div>
          )}
        </Card>
      </Col>

      <Col span={24}>
        <Card loading={loadingFinance}>
          <Typography.Title level={5} style={{ marginBottom: 16 }}>
            Detalle mensual (MXN)
          </Typography.Title>
          <Table
            size="small"
            pagination={false}
            dataSource={(trendData?.series || []).map((r) => ({ key: r.period, ...r }))}
            columns={[
              { title: 'Periodo', dataIndex: 'period', key: 'period' },
              {
                title: 'Ingresos',
                dataIndex: 'ingresos',
                key: 'ingresos',
                align: 'right' as const,
                render: (v: number) => currency(v, ccy),
              },
              {
                title: 'Egresos',
                dataIndex: 'egresos',
                key: 'egresos',
                align: 'right' as const,
                render: (v: number) => currency(v, ccy),
              },
              {
                title: 'Por cobrar',
                dataIndex: 'por_cobrar',
                key: 'por_cobrar',
                align: 'right' as const,
                render: (v: number) => currency(v || 0, ccy),
              },
              {
                title: 'Por pagar',
                dataIndex: 'por_pagar',
                key: 'por_pagar',
                align: 'right' as const,
                render: (v: number) => currency(v || 0, ccy),
              },
              {
                title: 'Resultado',
                key: 'resultado',
                align: 'right' as const,
                render: (_: any, r: any) => currency((r.ingresos || 0) - (r.egresos || 0), ccy),
              },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
};

// helpers
const currencyFormatter = (n: number, ccy: string) =>
  new Intl.NumberFormat('es-MX', { style: 'currency', currency: ccy || 'MXN', maximumFractionDigits: 0 }).format(
    Number.isFinite(n) ? n : 0
  );

