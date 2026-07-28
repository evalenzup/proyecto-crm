'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Tabs, Table, Button, Space, Tag, Modal, Form, Select, DatePicker, InputNumber,
  Input, message, Popconfirm, Tooltip, Typography, TimePicker,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ScheduleOutlined, WarningOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { PageHeader } from '@/components/PageHeader';
import { useEmpresaContext } from '@/context/EmpresaContext';
import { clienteService } from '@/services/clienteService';
import { tecnicoService } from '@/services/tecnicoService';
import { servicioOperativoService } from '@/services/servicioOperativoService';
import { certificadoService } from '@/services/certificadoService';
import {
  PlanServicio, PlanServicioInput, Periodicidad, PERIODICIDAD_LABELS,
  PlanTableroRow, PeriodoTablero, EstatusPeriodo,
  listarPlanes, crearPlan, actualizarPlan, eliminarPlan, obtenerTablero, programarServicio,
} from '@/services/planServicioService';
import { normalizeHttpError } from '@/utils/httpError';

const { Text } = Typography;

const ESTATUS_TAG: Record<EstatusPeriodo, { color: string; label: string }> = {
  SIN_PROGRAMAR: { color: 'default', label: 'Sin programar' },
  PROGRAMADA: { color: 'processing', label: 'Programada' },
  COMPLETADA: { color: 'success', label: 'Completada' },
  CANCELADA: { color: 'error', label: 'Cancelada' },
};

type Opt = { label: string; value: string };

const ContratosServicioPage: React.FC = () => {
  const { selectedEmpresaId } = useEmpresaContext();

  // Catálogos para selects
  const [tecnicos, setTecnicos] = useState<Opt[]>([]);
  const [servicios, setServicios] = useState<Opt[]>([]);
  const [clienteOpts, setClienteOpts] = useState<Opt[]>([]);

  useEffect(() => {
    if (!selectedEmpresaId) return;
    tecnicoService.getTecnicos({ empresa_id: selectedEmpresaId, activo: true, limit: 200 })
      .then((r) => setTecnicos(r.items.map((t) => ({ label: t.nombre_completo, value: t.id }))))
      .catch(() => {});
    servicioOperativoService.getServicios({ empresa_id: selectedEmpresaId, activo: true, limit: 200 })
      .then((r) => setServicios(r.items.map((s) => ({ label: s.nombre, value: s.id }))))
      .catch(() => {});
  }, [selectedEmpresaId]);

  const buscarClientes = useCallback(async (q: string) => {
    if (!selectedEmpresaId || q.length < 2) return;
    try {
      const res = await clienteService.buscarClientes(q, selectedEmpresaId, 'both', 15);
      setClienteOpts(res.map((c) => ({ label: c.nombre_comercial || c.nombre_razon_social, value: c.id })));
    } catch { /* silencioso */ }
  }, [selectedEmpresaId]);

  return (
    <>
      <PageHeader title="Contratos de servicio" />
      <div className="app-content">
        {!selectedEmpresaId ? (
          <Text type="secondary">Selecciona una empresa para ver sus contratos.</Text>
        ) : (
          <Tabs
            defaultActiveKey="tablero"
            items={[
              {
                key: 'tablero',
                label: <span><ScheduleOutlined /> Tablero</span>,
                children: <TableroTab empresaId={selectedEmpresaId} tecnicos={tecnicos} />,
              },
              {
                key: 'planes',
                label: 'Planes',
                children: (
                  <PlanesTab
                    empresaId={selectedEmpresaId}
                    tecnicos={tecnicos}
                    servicios={servicios}
                    clienteOpts={clienteOpts}
                    buscarClientes={buscarClientes}
                  />
                ),
              },
            ]}
          />
        )}
      </div>
    </>
  );
};

// ─── Pestaña: Tablero ─────────────────────────────────────────────────────────
const TableroTab: React.FC<{ empresaId: string; tecnicos: Opt[] }> = ({ empresaId, tecnicos }) => {
  const [mes, setMes] = useState<Dayjs>(dayjs());
  const [rows, setRows] = useState<PlanTableroRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [prog, setProg] = useState<{ plan: PlanTableroRow; periodo: PeriodoTablero } | null>(null);

  const cargar = useCallback(() => {
    setLoading(true);
    obtenerTablero(empresaId, mes.year(), mes.month() + 1)
      .then((t) => setRows(t.planes))
      .catch((e) => message.error(normalizeHttpError(e)))
      .finally(() => setLoading(false));
  }, [empresaId, mes]);

  useEffect(() => { cargar(); }, [cargar]);

  const columns = [
    {
      title: 'Cliente', dataIndex: 'cliente_nombre', key: 'cliente',
      render: (v: string, r: PlanTableroRow) => (
        <Space direction="vertical" size={0}>
          <span>
            {v}{' '}
            {r.por_vencer && (
              <Tooltip title={`Vigencia termina el ${r.vigencia_hasta}`}>
                <Tag icon={<WarningOutlined />} color="warning">Por vencer</Tag>
              </Tooltip>
            )}
          </span>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {PERIODICIDAD_LABELS[r.periodicidad]}{r.servicio_nombre ? ` · ${r.servicio_nombre}` : ''}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Servicios del mes', key: 'periodos',
      render: (_: unknown, r: PlanTableroRow) => (
        <Space wrap>
          {r.periodos.map((p, i) => {
            const t = ESTATUS_TAG[p.estatus];
            const fecha = dayjs(p.fecha_tentativa).format('DD/MMM');
            if (p.estatus === 'SIN_PROGRAMAR') {
              return (
                <Button key={i} size="small" type="dashed" icon={<PlusOutlined />}
                  onClick={() => setProg({ plan: r, periodo: p })}>
                  {fecha} · Programar
                </Button>
              );
            }
            return (
              <Tag key={i} color={t.color}>
                {fecha} · {t.label}{p.orden_folio ? ` (${p.orden_folio})` : ''}
              </Tag>
            );
          })}
        </Space>
      ),
    },
    {
      title: 'Precio', dataIndex: 'precio_pactado', key: 'precio', width: 110, align: 'right' as const,
      render: (v: number | null) => v != null ? `$${Number(v).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '—',
    },
  ];

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <DatePicker picker="month" value={mes} onChange={(v) => v && setMes(v)} allowClear={false} />
        <Button onClick={cargar}>Actualizar</Button>
      </Space>
      <Table
        rowKey="plan_id" size="small" loading={loading} columns={columns} dataSource={rows}
        pagination={false}
        locale={{ emptyText: 'No hay contratos con servicios este mes.' }}
      />
      <ProgramarModal
        open={!!prog}
        data={prog}
        tecnicos={tecnicos}
        onClose={() => setProg(null)}
        onDone={() => { setProg(null); cargar(); }}
      />
    </>
  );
};

const ProgramarModal: React.FC<{
  open: boolean;
  data: { plan: PlanTableroRow; periodo: PeriodoTablero } | null;
  tecnicos: Opt[];
  onClose: () => void;
  onDone: () => void;
}> = ({ open, data, tecnicos, onClose, onDone }) => {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && data) {
      form.setFieldsValue({ fecha: dayjs(data.periodo.fecha_tentativa), hora: null, tecnico_id: undefined });
    }
  }, [open, data, form]);

  const submit = async () => {
    const v = await form.validateFields();
    if (!data) return;
    setSaving(true);
    try {
      await programarServicio(data.plan.plan_id, {
        fecha: (v.fecha as Dayjs).format('YYYY-MM-DD'),
        hora_inicio: v.hora ? (v.hora as Dayjs).format('HH:mm') : undefined,
        tecnico_id: v.tecnico_id || undefined,
      });
      message.success('Servicio programado. Se creó la orden de servicio.');
      onDone();
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onCancel={onClose} onOk={submit} confirmLoading={saving}
      title={data ? `Programar servicio — ${data.plan.cliente_nombre}` : 'Programar'}
      okText="Crear orden">
      <Form form={form} layout="vertical">
        <Form.Item name="fecha" label="Fecha del servicio" rules={[{ required: true }]}>
          <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
        </Form.Item>
        <Form.Item name="hora" label="Hora de inicio (opcional)">
          <TimePicker style={{ width: '100%' }} format="HH:mm" minuteStep={15} />
        </Form.Item>
        <Form.Item name="tecnico_id" label="Técnico (opcional)">
          <Select allowClear options={tecnicos} placeholder="Usar el del plan" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

// ─── Pestaña: Planes (CRUD) ───────────────────────────────────────────────────
const PlanesTab: React.FC<{
  empresaId: string;
  tecnicos: Opt[];
  servicios: Opt[];
  clienteOpts: Opt[];
  buscarClientes: (q: string) => void;
}> = ({ empresaId, tecnicos, servicios, clienteOpts, buscarClientes }) => {
  const [planes, setPlanes] = useState<PlanServicio[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<PlanServicio | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [certificados, setCertificados] = useState<Opt[]>([]);
  const clienteSel = Form.useWatch('cliente_id', form);

  // Cargar los certificados del cliente seleccionado para poder ligarlos.
  useEffect(() => {
    if (!modalOpen || !clienteSel) { setCertificados([]); return; }
    certificadoService.list({ empresa_id: empresaId, cliente_id: clienteSel, limit: 100 })
      .then((r) => setCertificados(r.items.map((c) => ({
        value: c.id,
        label: `Folio ${c.folio} · ${c.tipo === 'SANITIZACION' ? 'Sanitización' : 'Plaguicidas'} · ${dayjs(c.fecha).format('DD/MM/YYYY')}`,
      }))))
      .catch(() => setCertificados([]));
  }, [modalOpen, clienteSel, empresaId]);

  const cargar = useCallback(() => {
    setLoading(true);
    listarPlanes({ empresa_id: empresaId })
      .then(setPlanes)
      .catch((e) => message.error(normalizeHttpError(e)))
      .finally(() => setLoading(false));
  }, [empresaId]);

  useEffect(() => { cargar(); }, [cargar]);

  const abrirNuevo = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ periodicidad: 'MENSUAL', activo: true, vigencia_desde: dayjs() });
    setModalOpen(true);
  };

  const abrirEditar = (p: PlanServicio) => {
    setEditing(p);
    form.setFieldsValue({
      cliente_id: p.cliente_id,
      servicio_id: p.servicio_id || undefined,
      tecnico_id: p.tecnico_id || undefined,
      periodicidad: p.periodicidad,
      dia_preferido: p.dia_preferido || undefined,
      precio_pactado: p.precio_pactado || undefined,
      vigencia_desde: p.vigencia_desde ? dayjs(p.vigencia_desde) : undefined,
      vigencia_hasta: p.vigencia_hasta ? dayjs(p.vigencia_hasta) : undefined,
      certificado_id: p.certificado_id || undefined,
      notas: p.notas || undefined,
      activo: p.activo,
    });
    // pre-cargar la opción del cliente actual
    if (p.cliente_nombre) buscarClientes(p.cliente_nombre);
    setModalOpen(true);
  };

  const guardar = async () => {
    const v = await form.validateFields();
    setSaving(true);
    const payload: PlanServicioInput = {
      empresa_id: empresaId,
      cliente_id: v.cliente_id,
      servicio_id: v.servicio_id || null,
      tecnico_id: v.tecnico_id || null,
      periodicidad: v.periodicidad as Periodicidad,
      dia_preferido: v.dia_preferido ?? null,
      precio_pactado: v.precio_pactado ?? null,
      vigencia_desde: (v.vigencia_desde as Dayjs).format('YYYY-MM-DD'),
      vigencia_hasta: v.vigencia_hasta ? (v.vigencia_hasta as Dayjs).format('YYYY-MM-DD') : null,
      certificado_id: v.certificado_id || null,
      notas: v.notas || null,
      activo: v.activo,
    };
    try {
      if (editing) await actualizarPlan(editing.id, payload);
      else await crearPlan(payload);
      message.success(editing ? 'Plan actualizado' : 'Plan creado');
      setModalOpen(false);
      cargar();
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e));
    } finally {
      setSaving(false);
    }
  };

  const borrar = async (id: string) => {
    try {
      await eliminarPlan(id);
      message.success('Plan eliminado');
      cargar();
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e));
    }
  };

  const columns = [
    { title: 'Cliente', dataIndex: 'cliente_nombre', key: 'cliente' },
    {
      title: 'Periodicidad', dataIndex: 'periodicidad', key: 'per', width: 120,
      render: (v: Periodicidad) => PERIODICIDAD_LABELS[v],
    },
    { title: 'Día', dataIndex: 'dia_preferido', key: 'dia', width: 60, render: (v: number) => v || '—' },
    { title: 'Servicio', dataIndex: 'servicio_nombre', key: 'srv', render: (v: string) => v || '—' },
    { title: 'Técnico', dataIndex: 'tecnico_nombre', key: 'tec', render: (v: string) => v || '—' },
    {
      title: 'Certificado', dataIndex: 'certificado_folio', key: 'cert', width: 100,
      render: (v: number | null) => v != null ? <Tag color="blue">Folio {v}</Tag> : '—',
    },
    {
      title: 'Precio', dataIndex: 'precio_pactado', key: 'precio', width: 110, align: 'right' as const,
      render: (v: number | null) => v != null ? `$${Number(v).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '—',
    },
    {
      title: 'Vigencia', key: 'vig', width: 180,
      render: (_: unknown, r: PlanServicio) =>
        `${dayjs(r.vigencia_desde).format('DD/MM/YY')} → ${r.vigencia_hasta ? dayjs(r.vigencia_hasta).format('DD/MM/YY') : 'indef.'}`,
    },
    {
      title: 'Estado', dataIndex: 'activo', key: 'activo', width: 90,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? 'Activo' : 'Inactivo'}</Tag>,
    },
    {
      title: '', key: 'acc', width: 90,
      render: (_: unknown, r: PlanServicio) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => abrirEditar(r)} />
          <Popconfirm title="¿Eliminar este plan?" onConfirm={() => borrar(r.id)} okText="Sí" cancelText="No">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Button type="primary" icon={<PlusOutlined />} onClick={abrirNuevo} style={{ marginBottom: 12 }}>
        Nuevo plan
      </Button>
      <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={planes} pagination={{ pageSize: 20 }} />

      <Modal open={modalOpen} onCancel={() => setModalOpen(false)} onOk={guardar} confirmLoading={saving}
        title={editing ? 'Editar plan de servicio' : 'Nuevo plan de servicio'} okText="Guardar" width={560}>
        <Form form={form} layout="vertical">
          <Form.Item name="cliente_id" label="Cliente" rules={[{ required: true }]}>
            <Select showSearch filterOption={false} onSearch={buscarClientes} options={clienteOpts}
              placeholder="Buscar cliente (mín. 2 letras)" notFoundContent="Escribe para buscar" />
          </Form.Item>
          <Space style={{ display: 'flex' }} align="start">
            <Form.Item name="periodicidad" label="Periodicidad" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select options={Object.entries(PERIODICIDAD_LABELS).map(([value, label]) => ({ value, label }))} />
            </Form.Item>
            <Form.Item name="dia_preferido" label="Día preferido (1-31)" style={{ flex: 1 }}
              tooltip="Día del mes de la visita. En quincenal se usa ese día y +15.">
              <InputNumber min={1} max={31} style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Space style={{ display: 'flex' }} align="start">
            <Form.Item name="vigencia_desde" label="Vigencia desde" rules={[{ required: true }]} style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
            </Form.Item>
            <Form.Item name="vigencia_hasta" label="Vigencia hasta (opcional)" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
            </Form.Item>
          </Space>
          <Form.Item name="servicio_id" label="Servicio (opcional)">
            <Select allowClear options={servicios} placeholder="Servicio a realizar" />
          </Form.Item>
          <Form.Item name="tecnico_id" label="Técnico habitual (opcional)">
            <Select allowClear options={tecnicos} placeholder="Técnico asignado" />
          </Form.Item>
          <Form.Item name="precio_pactado" label="Precio pactado (opcional)">
            <InputNumber min={0} style={{ width: '100%' }} prefix="$" precision={2} />
          </Form.Item>
          <Form.Item name="certificado_id" label="Certificado de fumigación (opcional)"
            tooltip="Liga el plan al certificado del cliente. Selecciona primero el cliente.">
            <Select
              allowClear
              options={certificados}
              placeholder={clienteSel ? 'Selecciona un certificado del cliente' : 'Primero elige el cliente'}
              disabled={!clienteSel}
              notFoundContent="Este cliente no tiene certificados registrados"
            />
          </Form.Item>
          <Form.Item name="notas" label="Notas">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="activo" label="Estado" initialValue={true}>
            <Select options={[{ value: true, label: 'Activo' }, { value: false, label: 'Inactivo' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default ContratosServicioPage;
