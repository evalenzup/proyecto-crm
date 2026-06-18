// src/components/ClienteContratos.tsx
// Contratos del cliente: listado + alta/edición con campos DINÁMICOS según los
// placeholders de la plantilla de la empresa + generar y descargar (docx/pdf).
import React, { useEffect, useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Modal, Form, Row, Col, Input, InputNumber,
  Select, message, Popconfirm, Alert,
} from 'antd';
import { PlusOutlined, FilePdfOutlined, FileWordOutlined, ThunderboltOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { contratoService, Contrato, CampoPlantilla } from '@/services/contratoService';
import { formatDate } from '@/utils/formatDate';

const ESTADO_COLOR: Record<string, string> = { BORRADOR: 'default', GENERADO: 'blue', FIRMADO: 'green' };

interface Props {
  clienteId: string;
}

export const ClienteContratos: React.FC<Props> = ({ clienteId }) => {
  const [contratos, setContratos] = useState<Contrato[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Contrato | null>(null);
  const [saving, setSaving] = useState(false);
  const [generandoId, setGenerandoId] = useState<string | null>(null);
  const [tecnicos, setTecnicos] = useState<{ id: string; nombre: string }[]>([]);
  const [empresaId, setEmpresaId] = useState<string | null>(null);
  const [campos, setCampos] = useState<CampoPlantilla[]>([]);
  const [form] = Form.useForm();

  const cargar = async () => {
    setLoading(true);
    try {
      setContratos(await contratoService.list(clienteId));
    } catch {
      message.error('No se pudieron cargar los contratos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (clienteId) cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteId]);

  const abrirNuevo = async () => {
    let pre;
    try {
      pre = await contratoService.precarga(clienteId);
    } catch {
      message.error('No se pudo preparar el contrato');
      return;
    }
    if (!pre.tiene_plantilla) {
      message.warning('Esta empresa no tiene plantilla de contrato. Súbela primero en la configuración de la empresa.');
      return;
    }
    setEditing(null);
    form.resetFields();
    setEmpresaId(pre.empresa_id);
    setCampos(pre.campos);
    setTecnicos(pre.tecnicos_disponibles.map((t) => ({ id: t.id, nombre: t.nombre })));
    setModalOpen(true);
  };

  const abrirEditar = async (c: Contrato) => {
    let pre;
    try {
      pre = await contratoService.precarga(clienteId);
    } catch {
      message.error('No se pudo preparar el contrato');
      return;
    }
    if (!pre.tiene_plantilla) {
      message.warning('Esta empresa no tiene plantilla de contrato configurada.');
      return;
    }
    setEditing(c);
    setEmpresaId(pre.empresa_id);
    setCampos(pre.campos);
    setTecnicos(pre.tecnicos_disponibles.map((t) => ({ id: t.id, nombre: t.nombre })));
    // Cargar valores: metadata + datos dinámicos (prefijo d_ para no chocar)
    const valores: Record<string, any> = {
      numero_contrato: c.numero_contrato,
      personal_asignado: c.personal_asignado || [],
    };
    for (const campo of pre.campos) {
      valores[`d_${campo.name}`] = (c.datos || {})[campo.name];
    }
    form.setFieldsValue(valores);
    setModalOpen(true);
  };

  const guardar = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      const datos: Record<string, any> = {};
      for (const campo of campos) {
        const val = v[`d_${campo.name}`];
        if (val !== undefined && val !== null && val !== '') datos[campo.name] = val;
      }
      const payload: Partial<Contrato> = {
        cliente_id: clienteId,
        empresa_id: empresaId || undefined,
        numero_contrato: v.numero_contrato || null,
        datos,
        personal_asignado: v.personal_asignado || [],
      };
      if (editing) {
        await contratoService.update(editing.id, payload);
        message.success('Contrato actualizado');
      } else {
        if (!empresaId) { message.error('El cliente no tiene empresa asociada'); setSaving(false); return; }
        await contratoService.create(payload);
        message.success('Contrato creado');
      }
      setModalOpen(false);
      await cargar();
    } catch (e: any) {
      if (e?.errorFields) return;
      if (!e?._handled) message.error(e?.response?.data?.detail ?? 'Error al guardar el contrato');
    } finally {
      setSaving(false);
    }
  };

  const generar = async (c: Contrato) => {
    setGenerandoId(c.id);
    try {
      await contratoService.generar(c.id);
      message.success('Documento generado');
      await cargar();
    } catch (e: any) {
      if (!e?._handled) message.error(e?.response?.data?.detail ?? 'Error al generar el documento');
    } finally {
      setGenerandoId(null);
    }
  };

  const descargar = async (c: Contrato, fmt: 'pdf' | 'docx') => {
    try {
      const blob = await contratoService.descargar(c.id, fmt);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `contrato_${c.numero_contrato || c.id}.${fmt}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error('No se pudo descargar el documento');
    }
  };

  const eliminar = async (c: Contrato) => {
    try {
      await contratoService.remove(c.id);
      message.success('Contrato eliminado');
      await cargar();
    } catch {
      message.error('No se pudo eliminar el contrato');
    }
  };

  const columns = [
    { title: 'Folio / No.', key: 'numero', render: (_: unknown, c: Contrato) => c.numero_contrato || '—', width: 120 },
    {
      title: 'Estado', dataIndex: 'estado', key: 'estado', width: 110,
      render: (e: string) => <Tag color={ESTADO_COLOR[e] ?? 'default'}>{e}</Tag>,
    },
    { title: 'Creado', dataIndex: 'creado_en', key: 'creado_en', width: 160, render: (v: string) => formatDate(v) },
    {
      title: 'Acciones', key: 'acciones', width: 240,
      render: (_: unknown, c: Contrato) => (
        <Space wrap>
          <Button size="small" icon={<EditOutlined />} onClick={() => abrirEditar(c)} />
          <Button size="small" icon={<ThunderboltOutlined />} loading={generandoId === c.id} onClick={() => generar(c)}>
            Generar
          </Button>
          {c.archivo_pdf && <Button size="small" icon={<FilePdfOutlined />} onClick={() => descargar(c, 'pdf')} />}
          {c.archivo_docx && <Button size="small" icon={<FileWordOutlined />} onClick={() => descargar(c, 'docx')} />}
          <Popconfirm title="¿Eliminar contrato?" onConfirm={() => eliminar(c)} okText="Sí" cancelText="No">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="Contratos"
      size="small"
      style={{ marginBottom: 16 }}
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={abrirNuevo}>Nuevo contrato</Button>}
    >
      <Table
        rowKey="id" size="small" loading={loading} columns={columns}
        dataSource={contratos} pagination={false} locale={{ emptyText: 'Sin contratos' }}
      />

      <Modal
        title={editing ? 'Editar contrato' : 'Nuevo contrato'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={guardar}
        confirmLoading={saving}
        okText="Guardar"
        width={720}
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="Los campos se toman de la plantilla de contrato de la empresa. Los datos del cliente y del prestador se llenan automáticamente."
        />
        <Form form={form} layout="vertical">
          <Form.Item label="No. de contrato" name="numero_contrato">
            <Input placeholder="Opcional" style={{ maxWidth: 280 }} />
          </Form.Item>

          <Row gutter={16}>
            {campos.map((campo) => (
              <Col xs={24} sm={12} key={campo.name}>
                <Form.Item label={campo.label} name={`d_${campo.name}`}>
                  {campo.tipo === 'numero'
                    ? <InputNumber min={0} precision={2} prefix="$" style={{ width: '100%' }} />
                    : <Input />}
                </Form.Item>
              </Col>
            ))}
          </Row>

          <Form.Item label="Personal asignado" name="personal_asignado" tooltip="Técnicos que aparecen en la tabla del contrato">
            <Select
              mode="multiple"
              placeholder="Técnicos asignados al contrato"
              options={tecnicos.map((t) => ({ value: t.id, label: t.nombre }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default ClienteContratos;
