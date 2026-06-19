// pages/equipos/configuracion.tsx
// Configuración por empresa de los equipos de control:
//   - Tipos de equipo (con campos personalizados que definen el form dinámico)
//   - Estados de equipo
import React, { useCallback, useEffect, useState } from 'react';
import {
  Tabs, Table, Button, Space, Popconfirm, message, Tag, Modal, Form, Input,
  Select, Switch, InputNumber, Card, Empty, Tooltip,
} from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, MinusCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { PageHeader } from '@/components/PageHeader';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import {
  equipoService, TipoEquipo, EstadoEquipo, TipoDato,
} from '@/services/equipoService';

const TIPO_DATO_OPTS: { value: TipoDato; label: string }[] = [
  { value: 'TEXTO', label: 'Texto' },
  { value: 'NUMERO', label: 'Número' },
  { value: 'FECHA', label: 'Fecha' },
  { value: 'BOOLEANO', label: 'Sí/No' },
  { value: 'LISTA', label: 'Lista de opciones' },
];

const slugify = (s: string) =>
  (s || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');

const EquiposConfigPage: React.FC = () => {
  const { selectedEmpresaId, empresas } = useEmpresaSelector();
  const empresaNombre = empresas.find((e) => e.id === selectedEmpresaId)?.nombre_comercial;

  return (
    <>
      <PageHeader
        title="Configuración de Equipos"
        subtitle={empresaNombre ? `Empresa: ${empresaNombre}` : 'Selecciona una empresa en la barra superior'}
      />
      {!selectedEmpresaId ? (
        <Card><Empty description="Selecciona una empresa para configurar sus equipos" /></Card>
      ) : (
        <Tabs
          items={[
            { key: 'tipos', label: 'Tipos de equipo', children: <TiposTab empresaId={selectedEmpresaId} /> },
            { key: 'estados', label: 'Estados', children: <EstadosTab empresaId={selectedEmpresaId} /> },
          ]}
        />
      )}
    </>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// Tipos de equipo
// ════════════════════════════════════════════════════════════════════════════
const TiposTab: React.FC<{ empresaId: string }> = ({ empresaId }) => {
  const [tipos, setTipos] = useState<TipoEquipo[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<TipoEquipo | null>(null);
  const [form] = Form.useForm();

  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      setTipos(await equipoService.getTipos(empresaId));
    } catch {
      message.error('No se pudieron cargar los tipos de equipo');
    } finally {
      setLoading(false);
    }
  }, [empresaId]);

  useEffect(() => { cargar(); }, [cargar]);

  const abrir = (t?: TipoEquipo) => {
    setEditing(t ?? null);
    form.resetFields();
    form.setFieldsValue(
      t
        ? { nombre: t.nombre, descripcion: t.descripcion, activo: t.activo, campos: t.campos }
        : { activo: true, campos: [] }
    );
    setModalOpen(true);
  };

  const guardar = async () => {
    const v = await form.validateFields();
    const campos = (v.campos || []).map((c: any, i: number) => ({
      etiqueta: c.etiqueta,
      clave: c.clave?.trim() || slugify(c.etiqueta),
      tipo_dato: c.tipo_dato || 'TEXTO',
      opciones: c.tipo_dato === 'LISTA'
        ? (c.opciones || '').split(',').map((s: string) => s.trim()).filter(Boolean)
        : null,
      requerido: !!c.requerido,
      orden: i,
    }));
    // Validar claves únicas
    const claves = campos.map((c: any) => c.clave);
    if (new Set(claves).size !== claves.length) {
      message.error('Hay claves de campo repetidas');
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await equipoService.updateTipo(editing.id, {
          nombre: v.nombre, descripcion: v.descripcion, activo: v.activo, campos,
        });
        message.success('Tipo actualizado');
      } else {
        await equipoService.createTipo({
          empresa_id: empresaId, nombre: v.nombre, descripcion: v.descripcion, activo: v.activo, campos,
        });
        message.success('Tipo creado');
      }
      setModalOpen(false);
      await cargar();
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? 'Error al guardar el tipo');
    } finally {
      setSaving(false);
    }
  };

  const eliminar = async (t: TipoEquipo) => {
    try {
      await equipoService.deleteTipo(t.id);
      message.success('Tipo eliminado');
      await cargar();
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? 'No se pudo eliminar el tipo');
    }
  };

  const columns: ColumnsType<TipoEquipo> = [
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    {
      title: 'Campos', key: 'campos', width: 320,
      render: (_, t) => t.campos.length
        ? <Space wrap size={4}>{t.campos.map((c) => <Tag key={c.clave}>{c.etiqueta}{c.requerido ? ' *' : ''}</Tag>)}</Space>
        : <span style={{ color: '#999' }}>Sin campos</span>,
    },
    { title: 'Activo', dataIndex: 'activo', key: 'activo', width: 90, render: (a) => a ? <Tag color="green">Sí</Tag> : <Tag>No</Tag> },
    {
      title: 'Acciones', key: 'acc', width: 110,
      render: (_, t) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => abrir(t)} />
          <Popconfirm title="¿Eliminar este tipo?" onConfirm={() => eliminar(t)} okText="Sí" cancelText="No">
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      size="small"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => abrir()}>Nuevo tipo</Button>}
    >
      <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={tipos}
        pagination={false} locale={{ emptyText: 'Sin tipos de equipo' }} />

      <Modal
        title={editing ? 'Editar tipo de equipo' : 'Nuevo tipo de equipo'}
        open={modalOpen} onCancel={() => setModalOpen(false)} onOk={guardar}
        confirmLoading={saving} okText="Guardar" width={760} destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item label="Nombre" name="nombre" rules={[{ required: true, message: 'Requerido' }]}>
            <Input placeholder="Ej. Cebadero, Trampa, Extintor PQS" />
          </Form.Item>
          <Form.Item label="Descripción" name="descripcion">
            <Input placeholder="Opcional" />
          </Form.Item>
          <Form.Item label="Activo" name="activo" valuePropName="checked">
            <Switch />
          </Form.Item>

          <div style={{ fontWeight: 600, margin: '8px 0' }}>Campos personalizados</div>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
            Definen el formulario de captura de cada equipo de este tipo.
          </div>
          <Form.List name="campos">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...rest }) => (
                  <Card key={key} size="small" style={{ marginBottom: 8 }}
                    bodyStyle={{ padding: 12 }}>
                    <Space align="start" wrap style={{ width: '100%' }}>
                      <Form.Item {...rest} name={[name, 'etiqueta']} label="Etiqueta"
                        rules={[{ required: true, message: 'Requerido' }]} style={{ marginBottom: 8 }}>
                        <Input placeholder="Rodenticida" style={{ width: 180 }} />
                      </Form.Item>
                      <Form.Item {...rest} name={[name, 'clave']} label="Clave"
                        tooltip="Identificador interno; si lo dejas vacío se genera de la etiqueta"
                        style={{ marginBottom: 8 }}>
                        <Input placeholder="rodenticida" style={{ width: 150 }} />
                      </Form.Item>
                      <Form.Item {...rest} name={[name, 'tipo_dato']} label="Tipo de dato"
                        initialValue="TEXTO" style={{ marginBottom: 8 }}>
                        <Select options={TIPO_DATO_OPTS} style={{ width: 150 }} />
                      </Form.Item>
                      <Form.Item noStyle shouldUpdate>
                        {() =>
                          form.getFieldValue(['campos', name, 'tipo_dato']) === 'LISTA' ? (
                            <Form.Item {...rest} name={[name, 'opciones']} label="Opciones (coma)"
                              getValueFromEvent={(e) => e.target.value}
                              getValueProps={(val) => ({ value: Array.isArray(val) ? val.join(', ') : val })}
                              style={{ marginBottom: 8 }}>
                              <Input placeholder="Brodifacoum, Bromadiolona" style={{ width: 220 }} />
                            </Form.Item>
                          ) : null
                        }
                      </Form.Item>
                      <Form.Item {...rest} name={[name, 'requerido']} label="Requerido"
                        valuePropName="checked" initialValue={false} style={{ marginBottom: 8 }}>
                        <Switch />
                      </Form.Item>
                      <Tooltip title="Quitar campo">
                        <Button type="text" danger icon={<MinusCircleOutlined />}
                          onClick={() => remove(name)} style={{ marginTop: 30 }} />
                      </Tooltip>
                    </Space>
                  </Card>
                ))}
                <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add({ tipo_dato: 'TEXTO', requerido: false })}>
                  Agregar campo
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </Card>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// Estados de equipo
// ════════════════════════════════════════════════════════════════════════════
const EstadosTab: React.FC<{ empresaId: string }> = ({ empresaId }) => {
  const [estados, setEstados] = useState<EstadoEquipo[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<EstadoEquipo | null>(null);
  const [form] = Form.useForm();

  const cargar = useCallback(async () => {
    setLoading(true);
    try {
      setEstados(await equipoService.getEstados(empresaId));
    } catch {
      message.error('No se pudieron cargar los estados');
    } finally {
      setLoading(false);
    }
  }, [empresaId]);

  useEffect(() => { cargar(); }, [cargar]);

  const abrir = (e?: EstadoEquipo) => {
    setEditing(e ?? null);
    form.resetFields();
    form.setFieldsValue(e ? { nombre: e.nombre, orden: e.orden, activo: e.activo } : { activo: true, orden: estados.length });
    setModalOpen(true);
  };

  const guardar = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await equipoService.updateEstado(editing.id, v);
        message.success('Estado actualizado');
      } else {
        await equipoService.createEstado({ empresa_id: empresaId, ...v });
        message.success('Estado creado');
      }
      setModalOpen(false);
      await cargar();
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? 'Error al guardar el estado');
    } finally {
      setSaving(false);
    }
  };

  const eliminar = async (e: EstadoEquipo) => {
    try {
      await equipoService.deleteEstado(e.id);
      message.success('Estado eliminado');
      await cargar();
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? 'No se pudo eliminar');
    }
  };

  const columns: ColumnsType<EstadoEquipo> = [
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    { title: 'Orden', dataIndex: 'orden', key: 'orden', width: 90 },
    { title: 'Activo', dataIndex: 'activo', key: 'activo', width: 90, render: (a) => a ? <Tag color="green">Sí</Tag> : <Tag>No</Tag> },
    {
      title: 'Acciones', key: 'acc', width: 110,
      render: (_, e) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => abrir(e)} />
          <Popconfirm title="¿Eliminar este estado?" onConfirm={() => eliminar(e)} okText="Sí" cancelText="No">
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card size="small" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => abrir()}>Nuevo estado</Button>}>
      <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={estados}
        pagination={false} locale={{ emptyText: 'Sin estados' }} />
      <Modal title={editing ? 'Editar estado' : 'Nuevo estado'} open={modalOpen}
        onCancel={() => setModalOpen(false)} onOk={guardar} confirmLoading={saving} okText="Guardar" destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item label="Nombre" name="nombre" rules={[{ required: true, message: 'Requerido' }]}>
            <Input placeholder="Activo, Dañado, Extraviado…" />
          </Form.Item>
          <Form.Item label="Orden" name="orden">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="Activo" name="activo" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default EquiposConfigPage;
