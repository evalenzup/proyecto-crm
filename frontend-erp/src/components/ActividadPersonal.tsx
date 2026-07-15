// components/ActividadPersonal.tsx
// Reporte visual de actividad del personal (solo administradores).
import React, { useMemo, useRef, useState } from 'react';
import {
  Alert, Button, Card, Col, DatePicker, Empty, Progress, Row, Select, Space,
  Spin, Statistic, Table, Tag, Tooltip, Typography, message,
} from 'antd';
import { ReloadOutlined, FilePdfOutlined, InfoCircleOutlined } from '@ant-design/icons';
import dynamic from 'next/dynamic';
import dayjs, { Dayjs } from 'dayjs';
import {
  getActividad, type ActividadReporte, type ActividadUsuario,
} from '@/services/auditoriaService';
import { usuarioService } from '@/services/usuarioService';

const ReactECharts: any = dynamic(() => import('echarts-for-react'), { ssr: false });
const { RangePicker } = DatePicker;
const { Text } = Typography;

const DOW = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const HORA_INI = 8, HORA_FIN = 18;
const HORAS = Array.from({ length: HORA_FIN - HORA_INI }, (_, i) => HORA_INI + i);

// Paleta por usuario (consistente con el resto de la app)
const COLORS = ['#1677ff', '#52c41a', '#faad14', '#eb2f96', '#722ed1', '#13c2c2', '#fa541c', '#2f54eb'];

const coberturaColor = (v: number) => (v >= 60 ? '#52c41a' : v >= 35 ? '#faad14' : '#ff4d4f');

export const ActividadPersonal: React.FC = () => {
  const [usuarios, setUsuarios] = useState<{ label: string; value: string }[]>([]);
  const [seleccion, setSeleccion] = useState<string[]>([]);
  const [rango, setRango] = useState<[Dayjs, Dayjs]>([dayjs().startOf('month'), dayjs()]);
  const [data, setData] = useState<ActividadReporte | null>(null);
  const [loading, setLoading] = useState(false);
  const reporteRef = useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    usuarioService.getUsuarios()
      .then((us) => setUsuarios(us.map((u: any) => ({ value: u.id, label: `${u.nombre_completo || u.email}` }))))
      .catch(() => { /* interceptor notifica */ });
  }, []);

  const generar = async () => {
    if (!seleccion.length) { message.warning('Selecciona al menos un usuario'); return; }
    setLoading(true);
    try {
      const rep = await getActividad({
        usuario_ids: seleccion.join(','),
        fecha_desde: rango[0].format('YYYY-MM-DD'),
        fecha_hasta: rango[1].format('YYYY-MM-DD'),
        hora_ini: HORA_INI, hora_fin: HORA_FIN,
      });
      setData(rep);
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo generar el reporte');
    } finally {
      setLoading(false);
    }
  };

  const exportarPDF = () => {
    if (!reporteRef.current) return;
    const html = reporteRef.current.innerHTML;
    const win = window.open('', '_blank', 'width=1100,height=800');
    if (!win) { message.warning('Permite ventanas emergentes para exportar el PDF'); return; }
    win.document.write(`<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"/>
      <title>Actividad del personal ${rango[0].format('DD-MM-YYYY')} a ${rango[1].format('DD-MM-YYYY')}</title>
      <style>
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1a1a1a;padding:24px;}
        h1{font-size:20px;color:#0a5c91;margin:0 0 4px;} .sub{color:#666;font-size:12px;margin-bottom:16px;}
        .ant-card{border:1px solid #eee;border-radius:8px;margin-bottom:12px;padding:12px;}
        table{width:100%;border-collapse:collapse;font-size:12px;} th,td{border:1px solid #eee;padding:6px 8px;text-align:left;}
        canvas{max-width:100%;}
        @media print{@page{size:A4;margin:1cm;}}
      </style></head><body>
      <h1>Actividad del personal en el sistema</h1>
      <div class="sub">Periodo: ${rango[0].format('DD/MM/YYYY')} — ${rango[1].format('DD/MM/YYYY')} · Horario laboral 08:00–18:00 · Generado ${dayjs().format('DD/MM/YYYY HH:mm')}</div>
      ${html}
      <script>window.onload=()=>{setTimeout(()=>{window.print();},400);}<\/script>
      </body></html>`);
    win.document.close();
  };

  const maxTotal = useMemo(
    () => Math.max(1, ...(data?.usuarios || []).map((u) => u.total)),
    [data]
  );

  // Gráfica comparativa (barras horizontales)
  const barOption = useMemo(() => {
    const us = data?.usuarios || [];
    return {
      grid: { left: 8, right: 24, top: 10, bottom: 10, containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: us.map((u) => u.nombre).reverse(), axisLabel: { fontSize: 11 } },
      tooltip: { trigger: 'axis' },
      series: [{
        type: 'bar',
        data: us.map((u, i) => ({ value: u.total, itemStyle: { color: COLORS[i % COLORS.length] } })).reverse(),
        label: { show: true, position: 'right', fontSize: 11 },
        barMaxWidth: 22,
      }],
    };
  }, [data]);

  const lineOption = useMemo(() => {
    const us = data?.usuarios || [];
    // eje X = fechas del rango
    const fechas: string[] = [];
    if (data) {
      let d = dayjs(data.rango.desde);
      const fin = dayjs(data.rango.hasta);
      while (d.isBefore(fin) || d.isSame(fin, 'day')) { fechas.push(d.format('YYYY-MM-DD')); d = d.add(1, 'day'); }
    }
    return {
      grid: { left: 8, right: 16, top: 30, bottom: 24, containLabel: true },
      tooltip: { trigger: 'axis' },
      legend: { top: 0, type: 'scroll' },
      xAxis: { type: 'category', data: fechas.map((f) => dayjs(f).format('DD/MM')), axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value' },
      series: us.map((u, i) => {
        const map = Object.fromEntries(u.por_dia.map((p) => [p.fecha, p.total]));
        return {
          name: u.nombre, type: 'line', smooth: true, showSymbol: false,
          itemStyle: { color: COLORS[i % COLORS.length] },
          data: fechas.map((f) => map[f] || 0),
        };
      }),
    };
  }, [data]);

  const heatOption = (u: ActividadUsuario) => {
    const cells = u.heatmap.map((h) => [HORAS.indexOf(h.hora), h.dow, h.total]);
    const max = Math.max(1, ...u.heatmap.map((h) => h.total));
    return {
      grid: { left: 8, right: 8, top: 10, bottom: 24, containLabel: true },
      tooltip: {
        formatter: (p: any) => `${DOW[p.data[1]]} ${HORAS[p.data[0]]}:00 — ${p.data[2]} acc.`,
      },
      xAxis: { type: 'category', data: HORAS.map((h) => `${h}`), splitArea: { show: true }, axisLabel: { fontSize: 9 } },
      yAxis: { type: 'category', data: DOW, splitArea: { show: true }, axisLabel: { fontSize: 9 } },
      visualMap: {
        min: 0, max, calculable: false, show: false,
        inRange: { color: ['#eef6ff', '#1677ff', '#003a8c'] },
      },
      series: [{
        type: 'heatmap', data: cells, label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,.3)' } },
      }],
    };
  };

  return (
    <div>
      <Alert
        type="info" showIcon icon={<InfoCircleOutlined />} style={{ marginBottom: 16 }}
        message="Mide la actividad registrada en el sistema (creación/edición de registros, facturación, pagos, órdenes, etc.). No incluye consultas ni trabajo fuera del sistema."
      />

      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          mode="multiple" allowClear style={{ minWidth: 320 }}
          placeholder="Selecciona los usuarios a evaluar…"
          value={seleccion} onChange={setSeleccion}
          options={usuarios} optionFilterProp="label" maxTagCount="responsive"
        />
        <RangePicker
          value={rango as any} format="DD/MM/YYYY"
          onChange={(r) => r && setRango(r as [Dayjs, Dayjs])}
          allowClear={false}
        />
        <Button type="primary" icon={<ReloadOutlined />} onClick={generar} loading={loading}>Generar</Button>
        {data && <Button icon={<FilePdfOutlined />} onClick={exportarPDF}>Exportar PDF</Button>}
      </Space>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
      ) : !data ? (
        <Empty description="Selecciona usuarios y un periodo, luego genera el reporte" />
      ) : data.usuarios.length === 0 ? (
        <Empty description="Sin actividad en el periodo seleccionado" />
      ) : (
        <div ref={reporteRef}>
          {/* Tarjetas por usuario */}
          <Row gutter={[12, 12]}>
            {data.usuarios.map((u, i) => (
              <Col xs={24} sm={12} lg={8} key={u.usuario_id}>
                <Card size="small" styles={{ body: { padding: 14 } }}
                  style={{ borderTop: `3px solid ${COLORS[i % COLORS.length]}` }}>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>{u.nombre}</div>
                  <Text type="secondary" style={{ fontSize: 12 }}>{u.email} · {u.rol}</Text>
                  <Row gutter={8} style={{ marginTop: 10 }}>
                    <Col span={12}><Statistic title="Acciones" value={u.total} valueStyle={{ fontSize: 20 }} /></Col>
                    <Col span={12}>
                      <div style={{ fontSize: 12, color: '#888' }}>Cobertura horario</div>
                      <Progress percent={u.cobertura_horario} size="small" strokeColor={coberturaColor(u.cobertura_horario)} />
                    </Col>
                  </Row>
                  <div style={{ fontSize: 12, color: '#555', marginTop: 6 }}>
                    <div>Días activos: <strong>{u.dias_activos}</strong> / {u.dias_rango}</div>
                    <div>Jornada aprox: <strong>{u.primera_accion_prom || '—'}</strong> a <strong>{u.ultima_accion_prom || '—'}</strong></div>
                    <div>Más frecuente: <Tag color={COLORS[i % COLORS.length]}>{u.accion_top || '—'}</Tag></div>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>

          {/* Comparativo + resultados */}
          <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
            <Col xs={24} lg={12}>
              <Card size="small" title="Comparativo de actividad (total de acciones)">
                <ReactECharts option={barOption} style={{ height: Math.max(180, data.usuarios.length * 46) }} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card size="small" title="Actividad por día">
                <ReactECharts option={lineOption} style={{ height: 260 }} />
              </Card>
            </Col>
          </Row>

          {/* Resultados clave (productividad) */}
          <Card size="small" title="Resultados clave" style={{ marginTop: 12 }}>
            <Table
              rowKey="usuario_id" size="small" pagination={false}
              dataSource={data.usuarios}
              columns={[
                { title: 'Usuario', dataIndex: 'nombre', key: 'nombre', render: (v, _r, i) => <span><Tag color={COLORS[i % COLORS.length]} /> {v}</span> },
                { title: 'Fact. timbradas', key: 'ft', align: 'right', render: (_, r) => r.resultados.facturas_timbradas },
                { title: 'Pagos', key: 'pg', align: 'right', render: (_, r) => r.resultados.pagos },
                { title: 'Órdenes creadas', key: 'oc', align: 'right', render: (_, r) => r.resultados.ordenes_creadas },
                { title: 'Órdenes completadas', key: 'ok', align: 'right', render: (_, r) => r.resultados.ordenes_completadas },
                { title: 'Certificados', key: 'ce', align: 'right', render: (_, r) => r.resultados.certificados },
                { title: 'Clientes', key: 'cl', align: 'right', render: (_, r) => r.resultados.clientes },
              ]}
            />
          </Card>

          {/* Mapa de calor por usuario */}
          <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
            {data.usuarios.map((u) => (
              <Col xs={24} md={12} key={u.usuario_id}>
                <Card size="small" title={<span>Cuándo trabaja — {u.nombre} <Tooltip title="Concentración de acciones por día de semana y hora (8–18)"><InfoCircleOutlined style={{ color: '#aaa' }} /></Tooltip></span>}>
                  <ReactECharts option={heatOption(u)} style={{ height: 220 }} />
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      )}
    </div>
  );
};

export default ActividadPersonal;
