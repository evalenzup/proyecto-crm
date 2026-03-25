// src/pages/reportes/index.tsx
import React, { useEffect, useState } from 'react';
import {
  Row, Col, Card, Statistic, Typography, Tooltip, Space,
  Select, Progress, Tag, Skeleton, Alert,
} from 'antd';
import {
  InfoCircleOutlined, RiseOutlined, FallOutlined, ClockCircleOutlined,
  TeamOutlined, PieChartOutlined, DollarOutlined,
} from '@ant-design/icons';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { dashboardService, ReportesMetrics } from '@/services/dashboardService';
import { empresaService, EmpresaOut } from '@/services/empresaService';
import { useAuth } from '@/context/AuthContext';
import { useFilterContext } from '@/context/FilterContext';

const { Title, Text } = Typography;

const fmt = (n: number) =>
  new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 }).format(n);

const ReportesPage: React.FC = () => {
  const { user } = useAuth();
  const { dashboard, setDashboard } = useFilterContext();
  const empresaId = dashboard.empresaId;

  const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
  const [data, setData] = useState<ReportesMetrics | null>(null);
  const [loading, setLoading] = useState(false);

  // Cargar empresas
  useEffect(() => {
    empresaService.getEmpresas().then(list => {
      setEmpresas(list);
      if (list.length > 0 && !empresaId) {
        setDashboard(prev => ({ ...prev, empresaId: list[0].id }));
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cargar métricas
  useEffect(() => {
    if (!empresaId) return;
    setLoading(true);
    dashboardService.getReportes({ empresaId })
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [empresaId]);

  const concentracionColor =
    (data?.concentracion_cartera_pct ?? 0) >= 40 ? '#ff4d4f' :
    (data?.concentracion_cartera_pct ?? 0) >= 25 ? '#faad14' : '#52c41a';

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">
            <PieChartOutlined style={{ marginRight: 8 }} />
            Reportes
          </h1>
        </div>
        <div className="app-page-header__right">
          {user?.rol === 'admin' && (
            <Select
              placeholder="Empresa"
              style={{ width: 240 }}
              allowClear
              value={empresaId}
              onChange={val => setDashboard(prev => ({ ...prev, empresaId: val }))}
              options={empresas.map(e => ({ label: e.nombre_comercial, value: e.id }))}
            />
          )}
        </div>
      </div>

      <div className="app-content">
        <Title level={4} style={{ marginTop: 16 }}>Financieros</Title>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>

          <Col xs={24} md={12} lg={6}>
            <Card loading={loading}>
              <Statistic
                title={
                  <Space>
                    <DollarOutlined />
                    Ticket Promedio (mes)
                    <Tooltip title="Valor promedio de cada factura timbrada este mes. Si baja, algo cambió en precios o clientes.">
                      <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                    </Tooltip>
                  </Space>
                }
                value={data?.ticket_promedio_mes ?? 0}
                formatter={v => fmt(Number(v))}
                valueStyle={{ color: '#1677ff' }}
              />
            </Card>
          </Col>

          <Col xs={24} md={12} lg={6}>
            <Card loading={loading}>
              {loading ? <Skeleton active paragraph={{ rows: 2 }} /> : (
                <>
                  <Space style={{ marginBottom: 8 }}>
                    {(data?.margen_bruto_pct ?? 0) >= 0
                      ? <RiseOutlined style={{ color: '#52c41a' }} />
                      : <FallOutlined style={{ color: '#ff4d4f' }} />}
                    <Text strong>Margen Bruto Estimado (mes)</Text>
                    <Tooltip title="(Ingresos cobrados − Egresos) ÷ Ingresos × 100. Estimado ya que los egresos pueden no corresponder exactamente a las ventas del mes.">
                      <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                    </Tooltip>
                  </Space>
                  <div style={{ fontSize: 28, fontWeight: 700, color: (data?.margen_bruto_pct ?? 0) >= 0 ? '#52c41a' : '#ff4d4f' }}>
                    {data?.margen_bruto_pct ?? 0}%
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Ingresos {fmt(data?.ingresos_mtd ?? 0)} · Egresos {fmt(data?.egresos_mtd ?? 0)}
                    </Text>
                  </div>
                </>
              )}
            </Card>
          </Col>

          <Col xs={24} md={12} lg={6}>
            <Card loading={loading}>
              <Statistic
                title={
                  <Space>
                    <ClockCircleOutlined />
                    Días Promedio de Cobro
                    <Tooltip title="Días promedio entre la fecha de emisión y la fecha de cobro real, en los últimos 90 días. Entre más bajo, mejor.">
                      <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                    </Tooltip>
                  </Space>
                }
                value={data?.dias_promedio_cobro ?? 0}
                precision={1}
                suffix="días"
                valueStyle={{
                  color: (data?.dias_promedio_cobro ?? 0) > 45
                    ? '#ff4d4f'
                    : (data?.dias_promedio_cobro ?? 0) > 30
                    ? '#faad14'
                    : '#52c41a',
                }}
              />
              {(data?.dias_promedio_cobro ?? 0) === 0 && !loading && (
                <Text type="secondary" style={{ fontSize: 12 }}>Sin cobros registrados en 90 días</Text>
              )}
            </Card>
          </Col>

        </Row>

        {/* ── De riesgo ───────────────────────────────────────────────── */}
        <Title level={4} style={{ marginTop: 16 }}>Riesgo</Title>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>

          <Col xs={24} md={12} lg={8}>
            <Card loading={loading} title={
              <Space>
                <PieChartOutlined />
                Concentración de Cartera (YTD)
                <Tooltip title="Porcentaje de los ingresos del año que proviene del cliente que más factura. Si supera el 40%, hay dependencia de un solo cliente.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }>
              {loading ? <Skeleton active paragraph={{ rows: 3 }} /> : (
                <>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 32, fontWeight: 700, color: concentracionColor }}>
                      {data?.concentracion_cartera_pct ?? 0}%
                    </span>
                    <Tag color={concentracionColor === '#ff4d4f' ? 'error' : concentracionColor === '#faad14' ? 'warning' : 'success'}>
                      {concentracionColor === '#ff4d4f' ? 'Riesgo alto' : concentracionColor === '#faad14' ? 'Atención' : 'Saludable'}
                    </Tag>
                  </div>
                  <Progress
                    percent={Math.min(data?.concentracion_cartera_pct ?? 0, 100)}
                    strokeColor={concentracionColor}
                    showInfo={false}
                    size="small"
                    style={{ marginBottom: 8 }}
                  />
                  <Text type="secondary">
                    Cliente top: <Text strong>{data?.concentracion_cartera_cliente ?? '—'}</Text>
                  </Text>
                  {(data?.concentracion_cartera_pct ?? 0) >= 40 && (
                    <Alert
                      type="warning"
                      showIcon
                      message="Dependencia alta de un solo cliente"
                      style={{ marginTop: 12, fontSize: 12 }}
                    />
                  )}
                </>
              )}
            </Card>
          </Col>

          <Col xs={24} md={12} lg={8}>
            <Card loading={loading}>
              <Statistic
                title={
                  <Space>
                    <TeamOutlined />
                    Clientes sin Actividad
                    <Tooltip title="Clientes que no han tenido ninguna factura timbrada en los últimos 90 días. Candidatos para reactivar.">
                      <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                    </Tooltip>
                  </Space>
                }
                value={data?.clientes_sin_actividad ?? 0}
                suffix="clientes"
                valueStyle={{
                  color: (data?.clientes_sin_actividad ?? 0) > 0 ? '#faad14' : '#52c41a',
                }}
              />
              {!loading && (data?.clientes_sin_actividad ?? 0) > 0 && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Sin factura en los últimos 90 días
                </Text>
              )}
            </Card>
          </Col>

        </Row>
      </div>
    </>
  );
};

export default ReportesPage;
