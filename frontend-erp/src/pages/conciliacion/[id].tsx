// src/pages/conciliacion/[id].tsx
'use client';

/**
 * La mesa de trabajo de la conciliación.
 *
 * Se ve como el Excel que ya usa: mismas columnas, mismo orden, los movimientos
 * tal como vienen del banco. Sobre eso se editan las dos que ella agrega —
 * comentario y área— sin abrir ventanas: clic en la celda, escribe, se guarda.
 *
 * El sistema no adivina qué factura corresponde a qué depósito. Ofrece la
 * búsqueda por folio y la suma de control; quien decide es ella. Si la suma de
 * las facturas no cuadra con el depósito se avisa, pero no se impide guardar:
 * a veces la diferencia es real y no nos toca bloquearla.
 */

import React from 'react';
import { useRouter } from 'next/router';
import { PageHeader } from '@/components/PageHeader';
import {
  Alert, Button, Card, Input, Modal, Progress, Segmented, Select, Space,
  Spin, Table, Tag, Tooltip, Typography, message,
} from 'antd';
import {
  ArrowLeftOutlined, CheckCircleFilled, FileExcelOutlined, FilePdfOutlined,
  LinkOutlined, SearchOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import conciliacionService, {
  Area, ConciliacionDetalle, FacturaEnlazada, MovimientoBancario,
} from '@/services/conciliacionService';
import { useEmpresaContext } from '@/context/EmpresaContext';
import api from '@/lib/axios';

const { Text } = Typography;

const dinero = (n?: number | null) =>
  n == null ? '' : n.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });

type Filtro = 'todos' | 'pendientes' | 'conciliados' | 'depositos' | 'retiros';

const ConciliacionDetallePage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const { selectedEmpresaId } = useEmpresaContext();

  const [conc, setConc] = React.useState<ConciliacionDetalle | null>(null);
  const [areas, setAreas] = React.useState<Area[]>([]);
  const [cargando, setCargando] = React.useState(true);
  const [filtro, setFiltro] = React.useState<Filtro>('todos');
  const [busqueda, setBusqueda] = React.useState('');
  const [guardando, setGuardando] = React.useState<string | null>(null);

  // Modal de facturas
  const [movActivo, setMovActivo] = React.useState<MovimientoBancario | null>(null);
  const [q, setQ] = React.useState('');
  const [resultados, setResultados] = React.useState<FacturaEnlazada[]>([]);
  const [elegidas, setElegidas] = React.useState<FacturaEnlazada[]>([]);
  const [buscando, setBuscando] = React.useState(false);

  const cargar = React.useCallback(async () => {
    if (typeof id !== 'string') return;
    setCargando(true);
    try {
      setConc(await conciliacionService.obtener(id));
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo cargar la conciliación');
    } finally {
      setCargando(false);
    }
  }, [id]);

  React.useEffect(() => { cargar(); }, [cargar]);
  React.useEffect(() => { conciliacionService.areas().then(setAreas).catch(() => {}); }, []);

  /** Guarda un cambio de celda sin recargar toda la tabla. */
  const guardar = async (
    mov: MovimientoBancario,
    cambios: { comentario?: string | null; area?: string | null; conciliado?: boolean },
  ) => {
    setGuardando(mov.id);
    try {
      const nuevo = await conciliacionService.actualizarMovimiento(mov.id, cambios);
      setConc((c) => c && {
        ...c,
        movimientos: c.movimientos.map((m) => (m.id === nuevo.id ? nuevo : m)),
      });
    } catch (e: any) {
      if (!e?._handled) {
        message.error(e?.response?.data?.error?.detail ?? 'No se pudo guardar');
      }
      cargar();
    } finally {
      setGuardando(null);
    }
  };

  // ── Facturas ───────────────────────────────────────────────────────────────

  const abrirFacturas = (mov: MovimientoBancario) => {
    setMovActivo(mov);
    setElegidas(mov.facturas);
    setQ('');
    setResultados([]);
  };

  const buscar = async (texto: string) => {
    setQ(texto);
    if (!texto.trim()) { setResultados([]); return; }
    setBuscando(true);
    try {
      setResultados(await conciliacionService.buscarFacturas(texto, selectedEmpresaId ?? undefined));
    } catch { /* el interceptor ya avisa */ } finally {
      setBuscando(false);
    }
  };

  const agregar = (f: FacturaEnlazada) => {
    if (elegidas.some((x) => x.id === f.id)) return;
    setElegidas((e) => [...e, f]);
  };

  const quitar = (fid: string) => setElegidas((e) => e.filter((x) => x.id !== fid));

  const guardarFacturas = async () => {
    if (!movActivo) return;
    try {
      const nuevo = await conciliacionService.enlazarFacturas(
        movActivo.id, elegidas.map((f) => f.id));
      setConc((c) => c && {
        ...c,
        movimientos: c.movimientos.map((m) => (m.id === nuevo.id ? nuevo : m)),
      });
      setMovActivo(null);
      message.success('Facturas guardadas');
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudieron guardar las facturas');
    }
  };

  // ── Vista ──────────────────────────────────────────────────────────────────

  const visibles = React.useMemo(() => {
    if (!conc) return [];
    const texto = busqueda.trim().toLowerCase();
    return conc.movimientos.filter((m) => {
      if (filtro === 'pendientes' && m.conciliado) return false;
      if (filtro === 'conciliados' && !m.conciliado) return false;
      if (filtro === 'depositos' && m.deposito == null) return false;
      if (filtro === 'retiros' && m.retiro == null) return false;
      if (texto) {
        const heno = `${m.concepto} ${m.comentario ?? ''}`.toLowerCase();
        if (!heno.includes(texto)) return false;
      }
      return true;
    });
  }, [conc, filtro, busqueda]);

  const descargar = async (url: string, nombre: string) => {
    try {
      const { data } = await api.get(url, { responseType: 'blob' });
      const href = window.URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = href; a.download = nombre;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(href);
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo descargar');
    }
  };

  if (cargando || !conc) {
    return <div style={{ textAlign: 'center', padding: 64 }}><Spin size="large" /></div>;
  }

  const pct = conc.total_movimientos
    ? Math.round((conc.conciliados / conc.total_movimientos) * 100) : 0;
  const pendientes = conc.total_movimientos - conc.conciliados;

  const columnas = [
    {
      title: 'Fecha', dataIndex: 'fecha', width: 96, fixed: 'left' as const,
      render: (f: string) => dayjs(f).format('DD/MM/YYYY'),
    },
    {
      title: 'Descripción', dataIndex: 'concepto', width: 380,
      render: (t: string) => (
        <Tooltip title={t} styles={{ root: { maxWidth: 520 } }}>
          <div style={{
            fontSize: 12, lineHeight: 1.35, maxHeight: 34, overflow: 'hidden',
          }}>{t}</div>
        </Tooltip>
      ),
    },
    {
      title: 'Depósitos', dataIndex: 'deposito', width: 120, align: 'right' as const,
      render: (v: number | null) => v == null ? <Text type="secondary">—</Text>
        : <span style={{ color: '#389e0d', fontWeight: 500 }}>{dinero(v)}</span>,
    },
    {
      title: 'Retiros', dataIndex: 'retiro', width: 120, align: 'right' as const,
      render: (v: number | null) => v == null ? <Text type="secondary">—</Text>
        : <span style={{ color: '#cf1322', fontWeight: 500 }}>{dinero(v)}</span>,
    },
    {
      title: 'Comentarios', key: 'comentario', width: 280,
      render: (_: unknown, m: MovimientoBancario) => (
        <Input.TextArea
          key={`${m.id}-${m.comentario ?? ''}`}
          defaultValue={m.comentario ?? ''}
          autoSize={{ minRows: 1, maxRows: 3 }}
          size="small"
          placeholder={m.deposito != null ? 'Folios o nota…' : 'Qué fue este gasto…'}
          disabled={m.facturas.length > 0}
          onBlur={(e) => {
            const v = e.target.value.trim();
            if (v !== (m.comentario ?? '')) {
              guardar(m, { comentario: v || null, conciliado: !!v });
            }
          }}
        />
      ),
    },
    {
      title: 'Área', key: 'area', width: 130,
      render: (_: unknown, m: MovimientoBancario) => (
        <Select
          mode="multiple"
          size="small"
          style={{ width: '100%' }}
          placeholder="—"
          value={m.area ? m.area.split(',') : []}
          options={areas.map((a) => ({ label: `${a.clave} · ${a.nombre}`, value: a.clave }))}
          onChange={(v: string[]) => guardar(m, { area: v.length ? v.join(',') : null })}
          maxTagCount="responsive"
        />
      ),
    },
    {
      title: 'Facturas', key: 'facturas', width: 220,
      render: (_: unknown, m: MovimientoBancario) => {
        const dif = m.facturas.length ? m.suma_facturas - (m.deposito ?? m.retiro ?? 0) : 0;
        return (
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Button size="small" icon={<LinkOutlined />} onClick={() => abrirFacturas(m)} block>
              {m.facturas.length ? `${m.facturas.length} factura${m.facturas.length > 1 ? 's' : ''}` : 'Buscar facturas'}
            </Button>
            {m.facturas.length > 0 && (
              <Text style={{ fontSize: 11 }} type={Math.abs(dif) < 0.01 ? 'success' : 'warning'}>
                {dinero(m.suma_facturas)}
                {Math.abs(dif) >= 0.01 && ` · dif ${dinero(dif)}`}
              </Text>
            )}
          </Space>
        );
      },
    },
    {
      title: '', key: 'ok', width: 44, align: 'center' as const,
      render: (_: unknown, m: MovimientoBancario) =>
        guardando === m.id ? <Spin size="small" />
          : m.conciliado ? <CheckCircleFilled style={{ color: '#52c41a' }} /> : null,
    },
  ];

  const totalElegidas = elegidas.reduce((s, f) => s + Number(f.total), 0);
  const importeMov = movActivo ? (movActivo.deposito ?? movActivo.retiro ?? 0) : 0;
  const difModal = totalElegidas - importeMov;

  return (
    <>
      <PageHeader
        title={`Conciliación · ${dayjs(conc.periodo_inicio).format('MMMM YYYY')}`}
        extra={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/conciliacion')}>
              Volver
            </Button>
            {conc.tiene_archivo && (
              <Button
                icon={<FilePdfOutlined />}
                onClick={() => descargar(conciliacionService.urlPdf(conc.id),
                  `estado-cuenta-${dayjs(conc.periodo_inicio).format('YYYY-MM')}.pdf`)}
              >
                Estado de cuenta
              </Button>
            )}
            <Button
              type="primary"
              icon={<FileExcelOutlined />}
              onClick={() => descargar(conciliacionService.urlExcel(conc.id),
                `conciliacion-${dayjs(conc.periodo_inicio).format('YYYY-MM')}.xlsx`)}
            >
              Exportar para la contadora
            </Button>
          </Space>
        }
      />

      <div className="app-content">
        <Card size="small" variant="borderless" styles={{ body: { padding: 12 } }}
              style={{ marginBottom: 8 }}>
          <Space wrap align="center" style={{ width: '100%' }}>
            <div style={{ minWidth: 220 }}>
              <Progress percent={pct} size="small" status={pct === 100 ? 'success' : 'active'} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {conc.conciliados} de {conc.total_movimientos} · faltan {pendientes}
              </Text>
            </div>
            <Segmented
              value={filtro}
              onChange={(v) => setFiltro(v as Filtro)}
              options={[
                { label: 'Todos', value: 'todos' },
                { label: `Pendientes (${pendientes})`, value: 'pendientes' },
                { label: 'Conciliados', value: 'conciliados' },
                { label: 'Depósitos', value: 'depositos' },
                { label: 'Retiros', value: 'retiros' },
              ]}
            />
            <Input
              placeholder="Buscar en la descripción o el comentario…"
              prefix={<SearchOutlined />}
              allowClear
              style={{ width: 320 }}
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              Saldo {dinero(conc.saldo_inicial)} → {dinero(conc.saldo_final)}
            </Text>
          </Space>
        </Card>

        <Card size="small" variant="borderless" styles={{ body: { padding: 0 } }}>
          <Table<MovimientoBancario>
            rowKey="id"
            dataSource={visibles}
            columns={columnas}
            size="small"
            scroll={{ x: 1500, y: 'calc(100vh - 330px)' }}
            pagination={false}
            rowClassName={(m) => (m.conciliado ? 'fila-conciliada' : '')}
          />
        </Card>
      </div>

      {/* Buscar y elegir facturas */}
      <Modal
        open={!!movActivo}
        title="Facturas de este movimiento"
        onCancel={() => setMovActivo(null)}
        onOk={guardarFacturas}
        okText="Guardar"
        cancelText="Cancelar"
        width={760}
        destroyOnClose
      >
        {movActivo && (
          <>
            <Alert
              type="info"
              style={{ marginBottom: 12 }}
              message={
                <Space split="·" wrap>
                  <span>{dayjs(movActivo.fecha).format('DD/MM/YYYY')}</span>
                  <strong>{dinero(movActivo.deposito ?? movActivo.retiro)}</strong>
                  <span style={{ fontSize: 12 }}>{movActivo.concepto.slice(0, 90)}</span>
                </Space>
              }
            />

            <Input
              autoFocus
              placeholder="Escribe el folio (1585, A-1585) o el nombre del cliente"
              prefix={<SearchOutlined />}
              allowClear
              value={q}
              onChange={(e) => buscar(e.target.value)}
              style={{ marginBottom: 8 }}
            />

            {buscando ? (
              <div style={{ textAlign: 'center', padding: 16 }}><Spin /></div>
            ) : resultados.length > 0 && (
              <div style={{ maxHeight: 200, overflow: 'auto', marginBottom: 12,
                            border: '1px solid #f0f0f0', borderRadius: 6 }}>
                {resultados.map((f) => (
                  <div
                    key={f.id}
                    onClick={() => agregar(f)}
                    style={{
                      display: 'flex', gap: 8, alignItems: 'center', padding: '6px 10px',
                      cursor: 'pointer', borderBottom: '1px solid #fafafa',
                      opacity: elegidas.some((x) => x.id === f.id) ? 0.45 : 1,
                    }}
                  >
                    <Tag color="blue" style={{ marginInlineEnd: 0 }}>{f.folio}</Tag>
                    <span style={{ flex: 1, fontSize: 13 }}>{f.cliente_nombre ?? '—'}</span>
                    <Text type="secondary" style={{ fontSize: 11 }}>{f.empresa_nombre}</Text>
                    <strong>{dinero(Number(f.total))}</strong>
                  </div>
                ))}
              </div>
            )}

            <Text strong style={{ display: 'block', marginBottom: 6 }}>
              Facturas de este movimiento
            </Text>
            {elegidas.length === 0 ? (
              <Text type="secondary">
                Ninguna todavía. Búscalas arriba y da clic para agregarlas.
              </Text>
            ) : (
              <>
                {elegidas.map((f) => (
                  <div key={f.id} style={{
                    display: 'flex', gap: 8, alignItems: 'center', padding: '4px 0',
                  }}>
                    <Tag color="blue" style={{ marginInlineEnd: 0 }}>{f.folio}</Tag>
                    <span style={{ flex: 1, fontSize: 13 }}>{f.cliente_nombre ?? '—'}</span>
                    <strong>{dinero(Number(f.total))}</strong>
                    <Button size="small" type="text" danger onClick={() => quitar(f.id)}>
                      Quitar
                    </Button>
                  </div>
                ))}
                <div style={{ borderTop: '1px solid #f0f0f0', marginTop: 8, paddingTop: 8 }}>
                  <Space split="·">
                    <span>Suma <strong>{dinero(totalElegidas)}</strong></span>
                    <span>Movimiento <strong>{dinero(importeMov)}</strong></span>
                    <Text type={Math.abs(difModal) < 0.01 ? 'success' : 'warning'}>
                      {Math.abs(difModal) < 0.01 ? 'Cuadra' : `Diferencia ${dinero(difModal)}`}
                    </Text>
                  </Space>
                  {Math.abs(difModal) >= 0.01 && (
                    <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
                      Puedes guardarlo así: a veces el depósito trae una diferencia real.
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </Modal>

      <style jsx global>{`
        .fila-conciliada > td { background: #f6ffed !important; }
      `}</style>
    </>
  );
};

export default ConciliacionDetallePage;
