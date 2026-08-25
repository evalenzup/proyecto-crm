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
  CheckOutlined, LinkOutlined, PlusOutlined, SearchOutlined, UndoOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import conciliacionService, {
  Area, ConciliacionDetalle, EgresoEnlazado, FacturaEnlazada, MovimientoBancario,
  Sugerencia,
} from '@/services/conciliacionService';
import { useEmpresaContext } from '@/context/EmpresaContext';
import api from '@/lib/axios';
import VisorPdfModal from '@/components/VisorPdfModal';

const { Text } = Typography;

/** Los importes llegan del API como texto (Decimal serializado), y llamar
 *  toLocaleString sobre un string lo devuelve tal cual: por eso salía
 *  "1296.000000" en vez de "$1,296.00". Se convierte antes de formatear. */
const dinero = (n?: number | string | null) => {
  if (n == null || n === '') return '';
  const v = typeof n === 'number' ? n : Number(n);
  return Number.isFinite(v)
    ? v.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })
    : '';
};

type Filtro = 'todos' | 'pendientes' | 'conciliados' | 'depositos' | 'retiros' | 'sugeridos';

/** Forma común de una factura o un egreso, para que el modal sirva para ambos. */
interface ItemEnlazable {
  id: string;
  etiqueta: string;
  detalle: string;
  empresa?: string;
  monto: number;
  /** Sólo en los gastos: ruta de su comprobante. */
  archivo?: string | null;
  /** Sólo en las facturas: complemento que documenta el cobro, si es PPD. */
  complemento?: { id: string; folio: string } | null;
}

const COLOR_CONFIANZA: Record<string, string> = {
  alta: 'green', media: 'gold', baja: 'default',
};

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
  const [sugs, setSugs] = React.useState<Record<string, Sugerencia[]>>({});
  const [cargandoSugs, setCargandoSugs] = React.useState(false);
  const [verPdf, setVerPdf] = React.useState(false);
  const [verTodas, setVerTodas] = React.useState<Record<string, boolean>>({});
  // Documento que se está revisando (factura o comprobante del gasto)
  const [doc, setDoc] = React.useState<{ url: string; titulo: string; nombre: string } | null>(null);

  /** Abre el comprobante para revisarlo sin salir de la conciliación: es
   *  justo cuando la sugerencia es dudosa que uno quiere verlo.
   *
   *  En una factura PPD el documento que vale es el complemento de pago, no la
   *  factura: la factura sólo dice que se va a cobrar en parcialidades. En una
   *  PUE no hay complemento y la factura es la que cuenta. */
  const verDocumento = (
    tipo: 'factura' | 'egreso' | 'pago', id: string, etiqueta: string,
    archivo?: string | null,
  ) => {
    const url = conciliacionService.urlDocumento(tipo, id, archivo);
    if (!url) {
      // El mensaje nombra el documento: cuando sólo decía "ese gasto" no había
      // forma de saber desde dónde se había pedido.
      message.info(`El gasto «${etiqueta}» no tiene comprobante cargado en el sistema.`);
      return;
    }
    const titulos: Record<string, string> = {
      factura: `Factura ${etiqueta}`,
      pago: `Complemento de pago ${etiqueta}`,
      egreso: `Comprobante · ${etiqueta}`,
    };
    setDoc({
      url,
      titulo: titulos[tipo] ?? etiqueta,
      nombre: `${etiqueta.replace(/[^\w-]+/g, '_')}.pdf`,
    });
  };


  // Modal de facturas
  const [movActivo, setMovActivo] = React.useState<MovimientoBancario | null>(null);
  const [q, setQ] = React.useState('');
  const [resultados, setResultados] = React.useState<ItemEnlazable[]>([]);
  const [elegidas, setElegidas] = React.useState<ItemEnlazable[]>([]);
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

  // Las sugerencias llegan aparte: la tabla aparece de inmediato y ellas después.
  React.useEffect(() => {
    if (typeof id !== 'string') return;
    setCargandoSugs(true);
    conciliacionService.sugerencias(id, selectedEmpresaId ?? undefined)
      .then(setSugs)
      .catch(() => {})
      .finally(() => setCargandoSugs(false));
  }, [id, selectedEmpresaId]);

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

  /** Deshace la conciliación de un movimiento para poder corregirlo. */
  const deshacer = async (mov: MovimientoBancario) => {
    setGuardando(mov.id);
    try {
      const nuevo = await conciliacionService.limpiarMovimiento(mov.id);
      setConc((c) => c && {
        ...c, movimientos: c.movimientos.map((m) => (m.id === nuevo.id ? nuevo : m)),
      });
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo deshacer');
    } finally {
      setGuardando(null);
    }
  };

  /** Acepta una candidata sin abrir la ventana: es el caso más común. */
  const aceptar = async (mov: MovimientoBancario, s: Sugerencia) => {
    setGuardando(mov.id);
    try {
      // Un complemento no se enlaza como tal: lo que va al comentario son los
      // folios de las facturas que cubre, que es lo que espera la contadora.
      const nuevo = s.tipo === 'egreso'
        ? await conciliacionService.enlazarEgresos(mov.id, [s.id])
        : await conciliacionService.enlazarFacturas(
            mov.id,
            s.tipo === 'complemento' ? (s.facturas ?? []).map((f) => f.id) : [s.id],
          );
      setConc((c) => c && {
        ...c, movimientos: c.movimientos.map((m) => (m.id === nuevo.id ? nuevo : m)),
      });
      // La sugerencia no se borra: si se deshace el enlace tiene que volver a
      // estar ahí. Sólo se oculta mientras el movimiento esté conciliado.
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo enlazar');
    } finally {
      setGuardando(null);
    }
  };

  // ── Facturas ───────────────────────────────────────────────────────────────

  /** El mismo modal sirve para los dos lados: facturas en los depósitos,
   *  egresos en los retiros. Se normalizan a una forma común para no duplicar
   *  toda la pantalla. */
  const esRetiro = (m: MovimientoBancario | null) => !!m && m.retiro != null;

  const comoItem = (x: FacturaEnlazada | EgresoEnlazado): ItemEnlazable =>
    'folio' in x
      ? { id: x.id, etiqueta: x.folio, detalle: x.cliente_nombre ?? '—',
          empresa: x.empresa_nombre ?? undefined, monto: Number(x.total),
          complemento: x.complementos?.[0] ?? null }
      : { id: x.id, etiqueta: (x.proveedor || 'Gasto').slice(0, 24),
          detalle: x.descripcion ?? '—', empresa: x.empresa_nombre ?? undefined,
          monto: Number(x.monto), archivo: x.archivo_pdf };

  const abrirFacturas = (mov: MovimientoBancario) => {
    setMovActivo(mov);
    setElegidas((mov.retiro != null ? mov.egresos : mov.facturas).map(comoItem));
    setQ('');
    setResultados([]);
  };

  // Se espera a que deje de teclear: una consulta por letra hacía que la
  // lista brincara y llegara tarde. 300 ms es lo que tarda una pausa natural.
  const temporizador = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const buscar = (texto: string) => {
    setQ(texto);
    if (temporizador.current) clearTimeout(temporizador.current);
    if (!texto.trim()) { setResultados([]); setBuscando(false); return; }

    setBuscando(true);
    temporizador.current = setTimeout(async () => {
      try {
        const emp = selectedEmpresaId ?? undefined;
        const datos = esRetiro(movActivo)
          ? await conciliacionService.buscarEgresos(texto, emp)
          : await conciliacionService.buscarFacturas(texto, emp);
        setResultados(datos.map(comoItem));
      } catch { /* el interceptor ya avisa */ } finally {
        setBuscando(false);
      }
    }, 300);
  };

  React.useEffect(() => () => {
    if (temporizador.current) clearTimeout(temporizador.current);
  }, []);

  const agregar = (f: ItemEnlazable) => {
    if (elegidas.some((x) => x.id === f.id)) return;
    setElegidas((e) => [...e, f]);
  };

  const quitar = (fid: string) => setElegidas((e) => e.filter((x) => x.id !== fid));

  const guardarFacturas = async () => {
    if (!movActivo) return;
    try {
      const ids = elegidas.map((f) => f.id);
      const nuevo = esRetiro(movActivo)
        ? await conciliacionService.enlazarEgresos(movActivo.id, ids)
        : await conciliacionService.enlazarFacturas(movActivo.id, ids);
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
      if (filtro === 'sugeridos' && !sugs[m.id]) return false;
      if (texto) {
        const heno = `${m.concepto} ${m.comentario ?? ''}`.toLowerCase();
        if (!heno.includes(texto)) return false;
      }
      return true;
    });
  }, [conc, filtro, busqueda, sugs]);

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
          disabled={m.facturas.length > 0 || m.egresos.length > 0}
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
      title: 'Facturas / Gastos', key: 'facturas', width: 300,
      render: (_: unknown, m: MovimientoBancario) => {
        const enlazados = m.retiro != null ? m.egresos.length : m.facturas.length;
        const dif = enlazados ? m.suma_facturas - (m.deposito ?? m.retiro ?? 0) : 0;
        const candidatas = sugs[m.id] ?? [];
        return (
          <Space direction="vertical" size={3} style={{ width: '100%' }}>
            <Button size="small" icon={<LinkOutlined />} onClick={() => abrirFacturas(m)} block>
              {enlazados
                ? `${enlazados} ${m.retiro != null ? 'gasto' : 'factura'}${enlazados > 1 ? 's' : ''}`
                : (m.retiro != null ? 'Buscar gastos' : 'Buscar facturas')}
            </Button>

            {enlazados > 0 && (
              <Text style={{ fontSize: 11 }} type={Math.abs(dif) < 0.01 ? 'success' : 'warning'}>
                {dinero(m.suma_facturas)}
                {Math.abs(dif) >= 0.01 && ` · dif ${dinero(dif)}`}
              </Text>
            )}

            {/* Cada folio es su propio botón que abre el PDF, y aceptar tiene el
                suyo aparte. Antes toda la fila aceptaba y el ojito iba dentro,
                así que al querer ver el documento se aceptaba sin querer. */}
            {enlazados === 0 && (verTodas[m.id] ? candidatas : candidatas.slice(0, 1)).map((s) => (
              <div
                key={s.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4, width: '100%',
                  padding: '3px 4px', border: '1px solid #f0f0f0', borderRadius: 6,
                }}
              >
                <Tooltip title={`Ver ${s.tipo === 'complemento' ? 'el complemento' : s.tipo === 'factura' ? 'la factura' : 'el comprobante'} ${s.folio}`}>
                  <Tag
                    color={COLOR_CONFIANZA[s.confianza]}
                    style={{ marginInlineEnd: 0, cursor: 'pointer' }}
                    onClick={() => (
                      s.tipo === 'complemento' ? verDocumento('pago', s.id, s.folio)
                      : s.tipo === 'factura' ? verDocumento('factura', s.id, s.folio)
                      : verDocumento('egreso', s.id, s.folio, s.archivo_pdf)
                    )}
                  >
                    {s.folio.length > 18 ? `${s.folio.slice(0, 18)}…` : s.folio}
                  </Tag>
                </Tooltip>

                {/* Las facturas que cubre el complemento, cada una con su PDF */}
                {s.tipo === 'complemento' && (s.facturas ?? []).map((f) => (
                  <Tooltip key={f.id} title={`Ver la factura ${f.folio}`}>
                    <Tag
                      style={{ marginInlineEnd: 0, cursor: 'pointer' }}
                      onClick={() => verDocumento('factura', f.id, f.folio)}
                    >
                      {f.folio}
                    </Tag>
                  </Tooltip>
                ))}

                {s.tipo !== 'complemento' && (
                  <span style={{ fontSize: 11, color: '#888' }}>{dinero(s.total)}</span>
                )}

                <span style={{ flex: 1 }} />

                <Tooltip title={`Aceptar · ${s.origen}`}>
                  <Button
                    type="primary"
                    ghost
                    size="small"
                    icon={<CheckOutlined />}
                    loading={guardando === m.id}
                    onClick={() => aceptar(m, s)}
                  />
                </Tooltip>
              </div>
            ))}

            {enlazados === 0 && candidatas.length > 1 && (
              <Button
                type="link"
                size="small"
                style={{ padding: 0, height: 18, fontSize: 11 }}
                onClick={() => setVerTodas((v) => ({ ...v, [m.id]: !v[m.id] }))}
              >
                {verTodas[m.id]
                  ? 'ocultar'
                  : `ver ${candidatas.length - 1} opción${candidatas.length > 2 ? 'es' : ''} más`}
              </Button>
            )}
          </Space>
        );
      },
    },
    {
      title: '', key: 'ok', width: 76, align: 'center' as const,
      render: (_: unknown, m: MovimientoBancario) => {
        if (guardando === m.id) return <Spin size="small" />;
        if (!m.conciliado) return null;
        return (
          <Space size={2}>
            <CheckCircleFilled style={{ color: '#52c41a' }} />
            <Tooltip title="Deshacer para corregirlo">
              <Button
                type="text"
                size="small"
                icon={<UndoOutlined />}
                onClick={() => deshacer(m)}
              />
            </Tooltip>
          </Space>
        );
      },
    },
  ];

  const totalElegidas = elegidas.reduce((s, f) => s + f.monto, 0);
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
              <Button icon={<FilePdfOutlined />} onClick={() => setVerPdf(true)}>
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
                { label: `Con sugerencia (${Object.keys(sugs).length})`, value: 'sugeridos' },
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
        title={esRetiro(movActivo) ? 'Gastos de este cargo' : 'Facturas de este depósito'}
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
              placeholder={esRetiro(movActivo)
                ? 'Escribe el proveedor o la descripción del gasto'
                : 'Escribe el folio (1585, A-1585) o el nombre del cliente'}
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
                    style={{
                      display: 'flex', gap: 8, alignItems: 'center', padding: '6px 10px',
                      borderBottom: '1px solid #fafafa',
                      opacity: elegidas.some((x) => x.id === f.id) ? 0.45 : 1,
                    }}
                  >
                    <Tooltip title="Ver el documento">
                      <Tag
                        color="blue"
                        style={{ marginInlineEnd: 0, cursor: 'pointer' }}
                        onClick={() => (esRetiro(movActivo)
                          ? verDocumento('egreso', f.id, f.etiqueta, f.archivo)
                          : verDocumento('factura', f.id, f.etiqueta))}
                      >
                        {f.etiqueta}
                      </Tag>
                    </Tooltip>
                    {f.complemento && (
                      <Tooltip title="Ver el complemento de pago">
                        <Tag
                          color="purple"
                          style={{ marginInlineEnd: 0, cursor: 'pointer' }}
                          onClick={() => verDocumento('pago', f.complemento!.id, f.complemento!.folio)}
                        >
                          {f.complemento.folio}
                        </Tag>
                      </Tooltip>
                    )}
                    <span style={{ flex: 1, fontSize: 13 }}>{f.detalle}</span>
                    <Text type="secondary" style={{ fontSize: 11 }}>{f.empresa}</Text>
                    <strong>{dinero(f.monto)}</strong>
                    <Button
                      size="small" type="primary" ghost icon={<PlusOutlined />}
                      disabled={elegidas.some((x) => x.id === f.id)}
                      onClick={() => agregar(f)}
                    >
                      Agregar
                    </Button>
                  </div>
                ))}
              </div>
            )}

            <Text strong style={{ display: 'block', marginBottom: 6 }}>
              {esRetiro(movActivo) ? 'Gastos de este cargo' : 'Facturas de este depósito'}
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
                    <Tooltip title="Ver el documento">
                      <Tag
                        color="blue"
                        style={{ marginInlineEnd: 0, cursor: 'pointer' }}
                        onClick={() => (esRetiro(movActivo)
                          ? verDocumento('egreso', f.id, f.etiqueta, f.archivo)
                          : verDocumento('factura', f.id, f.etiqueta))}
                      >
                        {f.etiqueta}
                      </Tag>
                    </Tooltip>
                    {f.complemento && (
                      <Tooltip title="Ver el complemento de pago">
                        <Tag
                          color="purple"
                          style={{ marginInlineEnd: 0, cursor: 'pointer' }}
                          onClick={() => verDocumento('pago', f.complemento!.id, f.complemento!.folio)}
                        >
                          {f.complemento.folio}
                        </Tag>
                      </Tooltip>
                    )}
                    <span style={{ flex: 1, fontSize: 13 }}>{f.detalle}</span>
                    <strong>{dinero(f.monto)}</strong>
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

      <VisorPdfModal
        url={verPdf ? conciliacionService.urlPdf(conc.id) : null}
        titulo={`Estado de cuenta · ${dayjs(conc.periodo_inicio).format('MMMM YYYY')}`}
        nombreArchivo={`estado-cuenta-${dayjs(conc.periodo_inicio).format('YYYY-MM')}.pdf`}
        onClose={() => setVerPdf(false)}
      />

      <VisorPdfModal
        url={doc?.url ?? null}
        titulo={doc?.titulo ?? ''}
        nombreArchivo={doc?.nombre ?? ''}
        onClose={() => setDoc(null)}
      />

      <style jsx global>{`
        .fila-conciliada > td { background: #f6ffed !important; }
      `}</style>
    </>
  );
};

export default ConciliacionDetallePage;
