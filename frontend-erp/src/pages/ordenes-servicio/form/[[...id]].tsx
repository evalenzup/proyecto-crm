'use client';
// pages/ordenes-servicio/form/[[...id]].tsx

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/router';
import { PageHeader } from '@/components/PageHeader';
import {
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Spin,
  Card,
  message,
  Row,
  Col,
  DatePicker,
  TimePicker,
  Typography,
  Tag,
  Space,
} from 'antd';
import { SaveOutlined, UserAddOutlined } from '@ant-design/icons';
import ClienteRapidoModal from '@/components/ClienteRapidoModal';
import debounce from 'lodash/debounce';
import dayjs from 'dayjs';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import ordenServicioService, {
  OrdenServicioOut,
  EstadoOS,
  PrioridadOS,
} from '@/services/ordenServicioService';
import { clienteService } from '@/services/clienteService';
import { tecnicoService } from '@/services/tecnicoService';
import { unidadService } from '@/services/unidadService';
import { servicioOperativoService } from '@/services/servicioOperativoService';

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

// ── Opciones ──────────────────────────────────────────────────────────────────

const ESTADOS: { value: EstadoOS; label: string; color: string }[] = [
  { value: 'PENDIENTE', label: 'Pendiente', color: 'default' },
  { value: 'ASIGNADO', label: 'Asignado', color: 'blue' },
  { value: 'EN_CAMINO', label: 'En camino', color: 'cyan' },
  { value: 'EN_PROGRESO', label: 'En progreso', color: 'processing' },
  { value: 'COMPLETADO', label: 'Completado', color: 'success' },
  { value: 'CANCELADO', label: 'Cancelado', color: 'error' },
  { value: 'REAGENDADO', label: 'Reagendado', color: 'warning' },
];

const PRIORIDADES: { value: PrioridadOS; label: string; color: string }[] = [
  { value: 'BAJA', label: 'Baja', color: 'green' },
  { value: 'MEDIA', label: 'Media', color: 'blue' },
  { value: 'ALTA', label: 'Alta', color: 'orange' },
  { value: 'URGENTE', label: 'Urgente', color: 'red' },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

// Convierte un id + lista de opciones en { value, label } para labelInValue.
// Retorna undefined si no encuentra el id (para que el fallback ?? pueda activarse).
const toLV = (id: string | null | undefined, opts: { value: string; label: string }[]) => {
  if (!id) return undefined;
  const found = opts.find((o) => o.value === id);
  return found ? { value: found.value, label: found.label } : undefined;
};

// ── Componente ────────────────────────────────────────────────────────────────

const OrdenServicioForm: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;
  const isNew = !id || id === 'nuevo';

  // Si viene ?fecha=YYYY-MM-DD desde la agenda (vista diaria), pre-seleccionar esa fecha
  const fechaFromQuery = (() => {
    const f = router.query.fecha;
    const s = Array.isArray(f) ? f[0] : f;
    return s && dayjs(s).isValid() ? dayjs(s) : null;
  })();

  const { selectedEmpresaId } = useEmpresaSelector();

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [record, setRecord] = useState<OrdenServicioOut | null>(null);

  // Opciones de selects
  const [clientes, setClientes] = useState<{ value: string; label: string }[]>([]);
  const [clientesBuscando, setClientesBuscando] = useState(false);
  const [loadingCliente, setLoadingCliente] = useState(false);
  const [modalClienteOpen, setModalClienteOpen] = useState(false);
  const [tecnicos, setTecnicos] = useState<{ value: string; label: string }[]>([]);
  const [unidades, setUnidades] = useState<{ value: string; label: string }[]>([]);
  const [servicios, setServicios] = useState<{ value: string; label: string }[]>([]);

  const empresaId = selectedEmpresaId ?? record?.empresa_id;

  // ── Búsqueda de clientes (server-side, debounced) ─────────────────────────
  const buscarClientes = useMemo(
    () =>
      debounce(async (q: string) => {
        if (!empresaId || !q || q.trim().length < 2) return;
        setClientesBuscando(true);
        try {
          const data = await clienteService.buscarClientes(q, empresaId, 'both', 20);
          setClientes(
            (data || []).map((c: any) => ({
              value: c.id,
              label: c.nombre_comercial ?? c.nombre_razon_social ?? c.id,
            })),
          );
        } catch {
          // silencioso
        } finally {
          setClientesBuscando(false);
        }
      }, 350),
    [empresaId],
  );

  // ── Auto-fill dirección y geolocalización al seleccionar cliente ─────────────
  const handleClienteChange = useCallback(async (option: { value: string; label: string } | null) => {
    if (!option?.value) {
      // Si se limpia la selección, limpiar los campos de ubicación
      form.setFieldsValue({ direccion_servicio: undefined, latitud: undefined, longitud: undefined });
      return;
    }

    // Solo auto-fill en nuevas órdenes para no pisar datos editados manualmente
    if (!isNew) return;

    setLoadingCliente(true);
    try {
      const c = await clienteService.getCliente(option.value);

      // Construir la dirección: prioridad → dirección de servicio, fallback → fiscal
      const calle      = c.serv_calle      || c.calle;
      const noExt      = c.serv_numero_exterior || c.numero_exterior;
      const noInt      = c.serv_numero_interior || c.numero_interior;
      const colonia    = c.serv_colonia    || c.colonia;
      const ciudad     = c.serv_ciudad     || c.ciudad;
      const estado     = c.serv_estado     || c.estado;
      const cp         = c.serv_codigo_postal || c.codigo_postal;
      const referencia = c.serv_referencia;

      const partes = [
        calle && noExt ? `${calle} #${noExt}${noInt ? ` Int. ${noInt}` : ''}` : calle,
        colonia,
        ciudad,
        estado,
        cp ? `C.P. ${cp}` : null,
        referencia || null,
      ].filter(Boolean);

      const direccion = partes.join(', ');

      form.setFieldsValue({
        direccion_servicio: direccion || undefined,
        latitud:  c.latitud  ?? undefined,
        longitud: c.longitud ?? undefined,
      });
    } catch {
      // Si falla la carga del cliente, no bloqueamos el flujo
    } finally {
      setLoadingCliente(false);
    }
  }, [form, isNew]);

  // ── Cliente creado desde el modal rápido ─────────────────────────────────────
  const handleClienteCreado = useCallback(
    ({ id: cliId, nombre_comercial }: { id: string; nombre_comercial: string }) => {
      const nuevaOpcion = { value: cliId, label: nombre_comercial };
      // Agrega la nueva opción al listado para que el Select la encuentre
      setClientes((prev) => [nuevaOpcion, ...prev]);
      // Selecciónala automáticamente en el form
      form.setFieldValue('cliente_id', nuevaOpcion);
      // Dispara el auto-fill de dirección (mismo flujo que al seleccionar uno existente)
      handleClienteChange(nuevaOpcion);
    },
    [form, handleClienteChange],
  );

  // ── Carga inicial ─────────────────────────────────────────────────────────────
  // Usamos labelInValue en los Select: el form guarda { value, label } en lugar
  // de solo el UUID, por lo que el label siempre está disponible sin depender
  // de que las opciones estén cargadas al momento de renderizar.

  const fetchAll = useCallback(async () => {
    if (!empresaId) return;
    setLoading(true);
    try {
      // Técnicos, unidades y servicios son listas manejables → cargar completas.
      // Clientes son >14k → solo cargamos el cliente actual; el resto usa búsqueda.
      const [tec, uni, srv] = await Promise.all([
        tecnicoService.getTecnicos({ empresa_id: empresaId, activo: true, limit: 200 }),
        unidadService.getUnidades({ empresa_id: empresaId, activo: true, limit: 200 }),
        servicioOperativoService.getServicios({ empresa_id: empresaId, limit: 200 }),
      ]);

      const tecOpts = tec.items.map((t: any) => ({ value: t.id, label: t.nombre_completo }));
      const uniOpts = uni.items.map((u: any) => ({ value: u.id, label: u.nombre }));
      const srvOpts = srv.items.map((s: any) => ({ value: s.id, label: s.nombre }));

      setTecnicos(tecOpts);
      setUnidades(uniOpts);
      setServicios(srvOpts);

      if (!isNew && id) {
        const data = await ordenServicioService.get(id);
        setRecord(data);

        // Para el cliente: la respuesta incluye el objeto `cliente` con nombre_comercial.
        // Pre-populamos cliOpts con solo ese cliente para que labelInValue lo encuentre.
        const cliNombre =
          (data as any).cliente?.nombre_comercial ??
          (data as any).cliente?.nombre_razon_social ??
          null;
        const cliOpts = data.cliente_id && cliNombre
          ? [{ value: String(data.cliente_id), label: cliNombre }]
          : [];
        setClientes(cliOpts);

        const cliLV = data.cliente_id && cliNombre
          ? { value: String(data.cliente_id), label: cliNombre }
          : (data.cliente_id ? { value: String(data.cliente_id), label: String(data.cliente_id) } : undefined);

        const tecLV = toLV(String(data.tecnico_id ?? ''), tecOpts)
          ?? (data.tecnico_id ? { value: String(data.tecnico_id), label: (data as any).tecnico?.nombre_completo ?? String(data.tecnico_id) } : undefined);
        const uniLV = toLV(String(data.unidad_id ?? ''), uniOpts)
          ?? (data.unidad_id ? { value: String(data.unidad_id), label: String(data.unidad_id) } : undefined);
        const srvLV = toLV(String(data.servicio_id ?? ''), srvOpts)
          ?? (data.servicio_id ? { value: String(data.servicio_id), label: String(data.servicio_id) } : undefined);

        form.setFieldsValue({
          cliente_id: cliLV,
          tecnico_id: tecLV,
          unidad_id: uniLV,
          servicio_id: srvLV,
          fecha_programada: data.fecha_programada ? dayjs(data.fecha_programada) : undefined,
          hora_inicio: data.hora_inicio ? dayjs(data.hora_inicio, 'HH:mm:ss') : undefined,
          hora_fin: data.hora_fin ? dayjs(data.hora_fin, 'HH:mm:ss') : undefined,
          duracion_minutos: data.duracion_minutos ?? undefined,
          estado: data.estado,
          prioridad: data.prioridad,
          direccion_servicio: data.direccion_servicio ?? undefined,
          precio_acordado: data.precio_acordado != null ? Number(data.precio_acordado) : undefined,
          notas_tecnico: data.notas_tecnico ?? undefined,
          notas_internas: data.notas_internas ?? undefined,
          notas_cierre: data.notas_cierre ?? undefined,
        });
      }
    } catch (e: any) {
      if (!isNew && id) {
        if (!e?._handled) message.error('No se pudo cargar la orden de servicio');
        router.push('/ordenes-servicio');
      }
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empresaId, id]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ── Guardar ─────────────────────────────────────────────────────────────────

  const handleSubmit = async (values: any) => {
    setSaving(true);
    try {
      // Con labelInValue, los valores de Select son { value, label } — extraemos solo value
      const getId = (v: any) => (v && typeof v === 'object' ? v.value : v) ?? null;

      const payload: any = {
        cliente_id: getId(values.cliente_id),
        tecnico_id: getId(values.tecnico_id),
        unidad_id: getId(values.unidad_id),
        servicio_id: getId(values.servicio_id),
        fecha_programada: values.fecha_programada
          ? values.fecha_programada.format('YYYY-MM-DD')
          : undefined,
        hora_inicio: values.hora_inicio ? values.hora_inicio.format('HH:mm:ss') : null,
        hora_fin: values.hora_fin ? values.hora_fin.format('HH:mm:ss') : null,
        duracion_minutos: values.duracion_minutos ?? null,
        estado: values.estado ?? 'PENDIENTE',
        prioridad: values.prioridad ?? 'MEDIA',
        direccion_servicio: values.direccion_servicio ?? null,
        precio_acordado: values.precio_acordado ?? null,
        notas_tecnico: values.notas_tecnico ?? null,
        notas_internas: values.notas_internas ?? null,
        notas_cierre: values.notas_cierre ?? null,
      };

      if (isNew) {
        await ordenServicioService.create(payload, empresaId ?? undefined);
        message.success('Orden creada correctamente');
      } else {
        const { cliente_id, ...updatePayload } = payload;
        await ordenServicioService.update(id!, updatePayload);
        message.success('Orden actualizada');
      }

      router.push('/ordenes-servicio');
    } catch (err: any) {
      if (!err?._handled) {
        const detail = err?.response?.data?.detail;
        message.error(detail ?? 'Error al guardar la orden');
      }
    } finally {
      setSaving(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <Spin spinning tip="Cargando...">
        <div style={{ minHeight: 200 }} />
      </Spin>
    );
  }

  return (
    <>
      <PageHeader title={isNew ? 'Nueva Orden de Servicio' : `Editar ${record?.folio_os ?? 'Orden'}`} />

      <div className="app-content">
        {record && (
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary" style={{ fontSize: '0.85em' }}>
              Creado: {new Date(record.creado_en).toLocaleString()} &nbsp;|&nbsp;
              Actualizado: {new Date(record.actualizado_en).toLocaleString()}
            </Text>
          </div>
        )}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          estado: 'PENDIENTE',
          prioridad: 'MEDIA',
          fecha_programada: fechaFromQuery ?? undefined,
        }}
      >
        {/* ── Sección: Datos principales ── */}
        <Card title="Datos Principales" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                name="cliente_id"
                label="Cliente"
                rules={[{ required: true, message: 'Selecciona un cliente' }]}
              >
                <Select
                  labelInValue
                  showSearch
                  placeholder="Escribe al menos 2 letras para buscar…"
                  filterOption={false}
                  onSearch={buscarClientes}
                  loading={clientesBuscando || loadingCliente}
                  options={clientes}
                  allowClear
                  notFoundContent={clientesBuscando ? 'Buscando…' : 'Sin resultados'}
                  onChange={handleClienteChange}
                  popupRender={(menu) => (
                    <>
                      {menu}
                      <div style={{ padding: '4px 8px 2px', borderTop: '1px solid #f0f0f0' }}>
                        <Button
                          type="link"
                          size="small"
                          icon={<UserAddOutlined />}
                          onClick={() => setModalClienteOpen(true)}
                          style={{ padding: '0 4px' }}
                        >
                          + Nuevo cliente
                        </Button>
                      </div>
                    </>
                  )}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="estado" label="Estado">
                <Select>
                  {ESTADOS.map((e) => (
                    <Option key={e.value} value={e.value}>
                      <Tag color={e.color}>{e.label}</Tag>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="prioridad" label="Prioridad">
                <Select>
                  {PRIORIDADES.map((p) => (
                    <Option key={p.value} value={p.value}>
                      <Tag color={p.color}>{p.label}</Tag>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item name="servicio_id" label="Tipo de Servicio">
                <Select
                  labelInValue
                  showSearch
                  placeholder="Seleccionar servicio…"
                  optionFilterProp="label"
                  options={servicios}
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="precio_acordado" label="Precio Acordado">
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  precision={2}
                  prefix="$"
                  placeholder="0.00"
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* ── Sección: Programación ── */}
        <Card title="Programación" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item
                name="fecha_programada"
                label="Fecha Programada"
                rules={[{ required: true, message: 'Selecciona una fecha' }]}
              >
                <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={5}>
              <Form.Item name="hora_inicio" label="Hora Inicio">
                <TimePicker format="HH:mm" style={{ width: '100%' }} minuteStep={15} />
              </Form.Item>
            </Col>
            <Col xs={24} md={5}>
              <Form.Item name="hora_fin" label="Hora Fin">
                <TimePicker format="HH:mm" style={{ width: '100%' }} minuteStep={15} />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="duracion_minutos" label="Duración (min)">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="Ej. 60" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* ── Sección: Asignación ── */}
        <Card title="Asignación" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item name="tecnico_id" label="Técnico Asignado">
                <Select
                  labelInValue
                  showSearch
                  placeholder="Seleccionar técnico…"
                  optionFilterProp="label"
                  options={tecnicos}
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="unidad_id" label="Unidad / Vehículo">
                <Select
                  labelInValue
                  showSearch
                  placeholder="Seleccionar unidad…"
                  optionFilterProp="label"
                  options={unidades}
                  allowClear
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* ── Sección: Ubicación ── */}
        <Card title="Ubicación del Servicio" style={{ marginBottom: 16 }}>
          <Form.Item name="direccion_servicio" label="Dirección">
            <TextArea rows={2} placeholder="Calle, número, colonia, ciudad…" />
          </Form.Item>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item name="latitud" label="Latitud">
                <InputNumber style={{ width: '100%' }} precision={7} placeholder="Ej. 32.5149" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="longitud" label="Longitud">
                <InputNumber style={{ width: '100%' }} precision={7} placeholder="Ej. -117.0382" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* ── Sección: Notas ── */}
        <Card title="Notas" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item name="notas_tecnico" label="Instrucciones al Técnico">
                <TextArea rows={3} placeholder="Instrucciones visibles para el técnico…" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="notas_internas" label="Notas Internas">
                <TextArea rows={3} placeholder="Notas solo visibles en el sistema…" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="notas_cierre" label="Notas de Cierre">
                <TextArea rows={3} placeholder="Se llenan al completar el servicio…" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* ── Botones ── */}
        <Form.Item style={{ textAlign: 'right', marginTop: 16 }}>
          <Space>
            <Button onClick={() => router.push('/ordenes-servicio')}>Cancelar</Button>
            <Button type="primary" htmlType="submit" loading={saving} icon={<SaveOutlined />}>
              {isNew ? 'Crear Orden' : 'Guardar Cambios'}
            </Button>
          </Space>
        </Form.Item>
      </Form>
      </div>

      {/* Modal para crear cliente rápido */}
      <ClienteRapidoModal
        open={modalClienteOpen}
        onClose={() => setModalClienteOpen(false)}
        onCreated={handleClienteCreado}
      />
    </>
  );
};

export default OrdenServicioForm;
