// src/components/ClienteEquipos.tsx
// Equipos de control instalados en el cliente, para la empresa activa.
// Captura con form dinámico según el tipo + alta masiva numerada.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Card, Button, Table, Space, Popconfirm, message, Tag, Modal, Form, Input,
  Select, Switch, InputNumber, DatePicker, Row, Col, Empty, Alert, Tooltip,
} from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, AppstoreAddOutlined, SettingOutlined } from '@ant-design/icons';
import Link from 'next/link';
import dayjs from 'dayjs';
import type { ColumnsType } from 'antd/es/table';
import { natCompare, boolCompare } from '@/utils/sorters';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import {
  equipoService, EquipoControl, TipoEquipo, EstadoEquipo, TipoEquipoCampo,
} from '@/services/equipoService';

interface Props {
  clienteId: string;
}

// Renderiza el input dinámico de un campo personalizado según su tipo de dato.
const CampoInput: React.FC<{ campo: TipoEquipoCampo }> = ({ campo }) => {
  switch (campo.tipo_dato) {
    case 'NUMERO':
      return <InputNumber style={{ width: '100%' }} />;
    case 'FECHA':
      return <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />;
    case 'BOOLEANO':
      return <Switch />;
    case 'LISTA':
      return <Select allowClear options={(campo.opciones || []).map((o) => ({ value: o, label: o }))} />;
    default:
      return <Input />;
  }
};

export const ClienteEquipos: React.FC<Props> = ({ clienteId }) => {
  const { selectedEmpresaId, empresas } = useEmpresaSelector();
  const empresaNombre = empresas.find((e) => e.id === selectedEmpresaId)?.nombre_comercial;

  const [equipos, setEquipos] = useState<EquipoControl[]>([]);
  const [tipos, setTipos] = useState<TipoEquipo[]>([]);
  const [estados, setEstados] = useState<EstadoEquipo[]>([]);
  const [loading, setLoading] = useState(false);

  // Modal individual
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<EquipoControl | null>(null);
  const [tipoSelId, setTipoSelId] = useState<string | undefined>(undefined);
  const [form] = Form.useForm();

  // Modal alta masiva
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkSaving, setBulkSaving] = useState(false);
  const [bulkTipoId, setBulkTipoId] = useState<string | undefined>(undefined);
  const [bulkForm] = Form.useForm();

  const tipoSel = useMemo(() => tipos.find((t) => t.id === tipoSelId), [tipos, tipoSelId]);
  const bulkTipo = useMemo(() => tipos.find((t) => t.id === bulkTipoId), [tipos, bulkTipoId]);

  const cargar = useCallback(async () => {
    if (!selectedEmpresaId) return;
    setLoading(true);
    try {
      const [eq, tp, es] = await Promise.all([
        equipoService.getEquipos({ cliente_id: clienteId, empresa_id: selectedEmpresaId, limit: 500 }),
        equipoService.getTipos(selectedEmpresaId, true),
        equipoService.getEstados(selectedEmpresaId, true),
      ]);
      setEquipos(eq.items);
      setTipos(tp);
      setEstados(es);
    } catch {
      message.error('No se pudieron cargar los equipos');
    } finally {
      setLoading(false);
    }
  }, [clienteId, selectedEmpresaId]);

  useEffect(() => { cargar(); }, [cargar]);

  // ── Helpers de valores dinámicos ──────────────────────────────────────────
  const valoresToForm = (campos: TipoEquipoCampo[], valores?: Record<string, unknown> | null) => {
    const out: Record<string, unknown> = {};
    campos.forEach((c) => {
      const v = valores?.[c.clave];
      out[c.clave] = c.tipo_dato === 'FECHA' && v ? dayjs(v as string) : v;
    });
    return out;
  };

  const formToValores = (campos: TipoEquipoCampo[], values: Record<string, any>) => {
    const out: Record<string, unknown> = {};
    campos.forEach((c) => {
      let v = values[c.clave];
      if (c.tipo_dato === 'FECHA' && v) v = (v as dayjs.Dayjs).format('YYYY-MM-DD');
      if (v !== undefined) out[c.clave] = v;
    });
    return out;
  };

  // ── Modal individual ──────────────────────────────────────────────────────
  const abrir = (eq?: EquipoControl) => {
    setEditing(eq ?? null);
    const tid = eq?.tipo_equipo_id ?? tipos[0]?.id;
    setTipoSelId(tid);
    const t = tipos.find((x) => x.id === tid);
    form.resetFields();
    form.setFieldsValue({
      tipo_equipo_id: tid,
      estado_id: eq?.estado_id ?? undefined,
      identificador: eq?.identificador,
      area: eq?.area,
      fecha_instalacion: eq?.fecha_instalacion ? dayjs(eq.fecha_instalacion) : undefined,
      notas: eq?.notas,
      activo: eq?.activo ?? true,
      ...(t ? valoresToForm(t.campos, eq?.valores) : {}),
    });
    setModalOpen(true);
  };

  const onChangeTipo = (id: string) => {
    setTipoSelId(id);
    // Limpia los valores de campos al cambiar de tipo
    const t = tipos.find((x) => x.id === id);
    const reset: Record<string, undefined> = {};
    tipos.forEach((tp) => tp.campos.forEach((c) => { reset[c.clave] = undefined; }));
    form.setFieldsValue({ ...reset, ...(t ? valoresToForm(t.campos, undefined) : {}) });
  };

  const guardar = async () => {
    if (!selectedEmpresaId || !tipoSel) { message.error('Selecciona un tipo de equipo'); return; }
    const v = await form.validateFields();
    const payload = {
      empresa_id: selectedEmpresaId,
      cliente_id: clienteId,
      tipo_equipo_id: v.tipo_equipo_id,
      estado_id: v.estado_id ?? null,
      identificador: v.identificador,
      area: v.area,
      fecha_instalacion: v.fecha_instalacion ? v.fecha_instalacion.format('YYYY-MM-DD') : null,
      notas: v.notas,
      activo: v.activo,
      valores: formToValores(tipoSel.campos, v),
    };
    setSaving(true);
    try {
      if (editing) {
        await equipoService.updateEquipo(editing.id, payload);
        message.success('Equipo actualizado');
      } else {
        await equipoService.createEquipo(payload);
        message.success('Equipo agregado');
      }
      setModalOpen(false);
      await cargar();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? 'Error al guardar el equipo');
    } finally {
      setSaving(false);
    }
  };

  const eliminar = async (eq: EquipoControl) => {
    try {
      await equipoService.deleteEquipo(eq.id);
      message.success('Equipo eliminado');
      await cargar();
    } catch {
      message.error('No se pudo eliminar el equipo');
    }
  };

  // ── Modal alta masiva ─────────────────────────────────────────────────────
  const abrirBulk = () => {
    const tid = tipos[0]?.id;
    setBulkTipoId(tid);
    bulkForm.resetFields();
    bulkForm.setFieldsValue({ tipo_equipo_id: tid, cantidad: 5, numero_inicial: 1, relleno_ceros: 2 });
    setBulkOpen(true);
  };

  const guardarBulk = async () => {
    if (!selectedEmpresaId || !bulkTipo) { message.error('Selecciona un tipo de equipo'); return; }
    const v = await bulkForm.validateFields();
    setBulkSaving(true);
    try {
      const creados = await equipoService.bulkCreate({
        empresa_id: selectedEmpresaId,
        cliente_id: clienteId,
        tipo_equipo_id: v.tipo_equipo_id,
        estado_id: v.estado_id ?? null,
        area: v.area,
        fecha_instalacion: v.fecha_instalacion ? v.fecha_instalacion.format('YYYY-MM-DD') : null,
        cantidad: v.cantidad,
        prefijo: v.prefijo,
        numero_inicial: v.numero_inicial,
        relleno_ceros: v.relleno_ceros,
        valores: formToValores(bulkTipo.campos, v),
      });
      message.success(`${creados.length} equipos creados`);
      setBulkOpen(false);
      await cargar();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? 'Error en el alta masiva');
    } finally {
      setBulkSaving(false);
    }
  };

  // ── Columnas ──────────────────────────────────────────────────────────────
  const columns: ColumnsType<EquipoControl> = [
    {
      title: 'ID', dataIndex: 'identificador', key: 'identificador', width: 110, render: (v) => v || '—',
      sorter: (a, b) => natCompare(a.identificador, b.identificador),
      defaultSortOrder: 'ascend',
    },
    { title: 'Tipo', dataIndex: 'tipo_equipo_nombre', key: 'tipo', width: 140, sorter: (a, b) => natCompare(a.tipo_equipo_nombre, b.tipo_equipo_nombre) },
    { title: 'Área / Ubicación', dataIndex: 'area', key: 'area', render: (v) => v || '—', sorter: (a, b) => natCompare(a.area, b.area) },
    {
      title: 'Estado', dataIndex: 'estado_nombre', key: 'estado', width: 120,
      render: (v) => v ? <Tag color="blue">{v}</Tag> : <span style={{ color: '#999' }}>—</span>,
      sorter: (a, b) => natCompare(a.estado_nombre, b.estado_nombre),
    },
    { title: 'Activo', dataIndex: 'activo', key: 'activo', width: 80, render: (a) => a ? <Tag color="green">Sí</Tag> : <Tag>No</Tag>, sorter: (a, b) => boolCompare(a.activo, b.activo) },
    {
      title: 'Acciones', key: 'acc', width: 100,
      render: (_, eq) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => abrir(eq)} />
          <Popconfirm title="¿Eliminar equipo?" onConfirm={() => eliminar(eq)} okText="Sí" cancelText="No">
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const sinTipos = !loading && tipos.length === 0;

  return (
    <Card
      title={`Equipos de control${empresaNombre ? ` — ${empresaNombre}` : ''}`}
      size="small"
      style={{ marginBottom: 16 }}
      extra={
        <Space>
          <Tooltip title="Configurar tipos y estados">
            <Link href="/equipos/configuracion"><Button size="small" icon={<SettingOutlined />}>Configurar</Button></Link>
          </Tooltip>
          <Button icon={<AppstoreAddOutlined />} onClick={abrirBulk} disabled={sinTipos}>Alta masiva</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => abrir()} disabled={sinTipos}>Agregar equipo</Button>
        </Space>
      }
    >
      {!selectedEmpresaId ? (
        <Empty description="Selecciona una empresa en la barra superior" />
      ) : sinTipos ? (
        <Alert
          type="info" showIcon
          message="Esta empresa no tiene tipos de equipo configurados"
          description={<>Primero define los tipos en <Link href="/equipos/configuracion">Configuración de Equipos</Link>.</>}
        />
      ) : (
        <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={equipos}
          pagination={false} locale={{ emptyText: 'Sin equipos registrados' }} scroll={{ x: 700 }} />
      )}

      {/* Modal individual */}
      <Modal
        title={editing ? 'Editar equipo' : 'Agregar equipo'}
        open={modalOpen} onCancel={() => setModalOpen(false)} onOk={guardar}
        confirmLoading={saving} okText="Guardar" width={680} destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item label="Tipo de equipo" name="tipo_equipo_id" rules={[{ required: true }]}>
                <Select onChange={onChangeTipo} options={tipos.map((t) => ({ value: t.id, label: t.nombre }))} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Estado" name="estado_id">
                <Select allowClear options={estados.map((e) => ({ value: e.id, label: e.nombre }))} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={8}>
              <Form.Item label="Identificador" name="identificador">
                <Input placeholder="Ej. C-01" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={10}>
              <Form.Item label="Área / Ubicación" name="area">
                <Input placeholder="Ej. Cocina, Almacén" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={6}>
              <Form.Item label="Instalación" name="fecha_instalacion">
                <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
              </Form.Item>
            </Col>
          </Row>

          {/* Campos dinámicos del tipo */}
          {tipoSel && tipoSel.campos.length > 0 && (
            <>
              <div style={{ fontWeight: 600, margin: '4px 0 8px' }}>Datos del equipo</div>
              <Row gutter={16}>
                {tipoSel.campos.map((c) => (
                  <Col xs={24} sm={12} key={c.clave}>
                    <Form.Item
                      label={c.etiqueta}
                      name={c.clave}
                      valuePropName={c.tipo_dato === 'BOOLEANO' ? 'checked' : 'value'}
                      rules={c.requerido ? [{ required: true, message: 'Requerido' }] : undefined}
                    >
                      <CampoInput campo={c} />
                    </Form.Item>
                  </Col>
                ))}
              </Row>
            </>
          )}

          <Row gutter={16}>
            <Col xs={24} sm={18}>
              <Form.Item label="Notas" name="notas">
                <Input.TextArea rows={2} placeholder="Opcional" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={6}>
              <Form.Item label="Activo" name="activo" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Modal alta masiva */}
      <Modal
        title="Alta masiva de equipos"
        open={bulkOpen} onCancel={() => setBulkOpen(false)} onOk={guardarBulk}
        confirmLoading={bulkSaving} okText="Crear" width={680} destroyOnClose
      >
        <Form form={bulkForm} layout="vertical">
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item label="Tipo de equipo" name="tipo_equipo_id" rules={[{ required: true }]}>
                <Select onChange={(id) => setBulkTipoId(id)} options={tipos.map((t) => ({ value: t.id, label: t.nombre }))} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Estado inicial" name="estado_id">
                <Select allowClear options={estados.map((e) => ({ value: e.id, label: e.nombre }))} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item label="Área / Ubicación" name="area">
                <Input placeholder="Ej. Perímetro" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Fecha de instalación" name="fecha_instalacion">
                <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={12} sm={6}>
              <Form.Item label="Cantidad" name="cantidad" rules={[{ required: true }]}>
                <InputNumber min={1} max={500} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={12} sm={6}>
              <Form.Item label="Prefijo" name="prefijo" tooltip="Ej. C-  →  C-01, C-02…">
                <Input placeholder="C-" />
              </Form.Item>
            </Col>
            <Col xs={12} sm={6}>
              <Form.Item label="N° inicial" name="numero_inicial">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={12} sm={6}>
              <Form.Item label="Relleno ceros" name="relleno_ceros" tooltip="2 → 01, 02…  (0 = sin relleno)">
                <InputNumber min={0} max={6} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          {/* Campos dinámicos (mismos valores para todos) */}
          {bulkTipo && bulkTipo.campos.length > 0 && (
            <>
              <div style={{ fontWeight: 600, margin: '4px 0 8px' }}>Datos comunes (se aplican a todos)</div>
              <Row gutter={16}>
                {bulkTipo.campos.map((c) => (
                  <Col xs={24} sm={12} key={c.clave}>
                    <Form.Item
                      label={c.etiqueta}
                      name={c.clave}
                      valuePropName={c.tipo_dato === 'BOOLEANO' ? 'checked' : 'value'}
                    >
                      <CampoInput campo={c} />
                    </Form.Item>
                  </Col>
                ))}
              </Row>
            </>
          )}
        </Form>
      </Modal>
    </Card>
  );
};

export default ClienteEquipos;
