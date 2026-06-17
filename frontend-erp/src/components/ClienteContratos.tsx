// src/components/ClienteContratos.tsx
// Contratos del cliente: listado + alta/edición con precarga + generar y descargar (docx/pdf).
// Se muestra en el form del cliente (modo edición).
import React, { useEffect, useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Modal, Form, Row, Col, Input, InputNumber,
  DatePicker, Select, message, Popconfirm,
} from 'antd';
import { PlusOutlined, FilePdfOutlined, FileWordOutlined, ThunderboltOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { contratoService, Contrato } from '@/services/contratoService';
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
    setEditing(null);
    form.resetFields();
    try {
      const pre = await contratoService.precarga(clienteId);
      setEmpresaId(pre.empresa_id);
      setTecnicos(pre.tecnicos_disponibles.map((t) => ({ id: t.id, nombre: t.nombre })));
      form.setFieldsValue({
        precio_combo: pre.servicios?.combo,
        certificado_folio: undefined,
      });
    } catch {
      setTecnicos([]);
    }
    setModalOpen(true);
  };

  const abrirEditar = async (c: Contrato) => {
    setEditing(c);
    try {
      const pre = await contratoService.precarga(clienteId);
      setEmpresaId(pre.empresa_id);
      setTecnicos(pre.tecnicos_disponibles.map((t) => ({ id: t.id, nombre: t.nombre })));
    } catch { /* noop */ }
    form.setFieldsValue({
      numero_contrato: c.numero_contrato,
      fecha_contrato: c.fecha_contrato ? dayjs(c.fecha_contrato) : null,
      vigencia: c.vigencia_desde && c.vigencia_hasta ? [dayjs(c.vigencia_desde), dayjs(c.vigencia_hasta)] : null,
      certificado_folio: c.certificado_folio,
      precio_fumigacion: c.servicios?.fumigacion,
      precio_sanitizacion: c.servicios?.sanitizacion,
      precio_combo: c.servicios?.combo,
      personal_asignado: c.personal_asignado || [],
      exclusiones: c.exclusiones,
      notas: c.notas,
    });
    setModalOpen(true);
  };

  const guardar = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      const payload: Partial<Contrato> = {
        cliente_id: clienteId,
        empresa_id: empresaId || undefined,
        numero_contrato: v.numero_contrato || null,
        fecha_contrato: v.fecha_contrato ? v.fecha_contrato.format('YYYY-MM-DD') : null,
        vigencia_desde: v.vigencia?.[0] ? v.vigencia[0].format('YYYY-MM-DD') : null,
        vigencia_hasta: v.vigencia?.[1] ? v.vigencia[1].format('YYYY-MM-DD') : null,
        certificado_folio: v.certificado_folio || null,
        servicios: {
          ...(v.precio_fumigacion != null ? { fumigacion: v.precio_fumigacion } : {}),
          ...(v.precio_sanitizacion != null ? { sanitizacion: v.precio_sanitizacion } : {}),
          ...(v.precio_combo != null ? { combo: v.precio_combo } : {}),
        },
        personal_asignado: v.personal_asignado || [],
        exclusiones: v.exclusiones || null,
        notas: v.notas || null,
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
      if (e?.errorFields) return; // validación
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
    {
      title: 'Folio / No.',
      key: 'numero',
      render: (_: unknown, c: Contrato) => c.numero_contrato || '—',
      width: 120,
    },
    {
      title: 'Vigencia',
      key: 'vigencia',
      render: (_: unknown, c: Contrato) =>
        c.vigencia_desde && c.vigencia_hasta
          ? `${c.vigencia_desde} → ${c.vigencia_hasta}`
          : '—',
    },
    {
      title: 'Estado',
      dataIndex: 'estado',
      key: 'estado',
      width: 110,
      render: (e: string) => <Tag color={ESTADO_COLOR[e] ?? 'default'}>{e}</Tag>,
    },
    {
      title: 'Creado',
      dataIndex: 'creado_en',
      key: 'creado_en',
      width: 150,
      render: (v: string) => formatDate(v),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 230,
      render: (_: unknown, c: Contrato) => (
        <Space wrap>
          <Button size="small" icon={<EditOutlined />} onClick={() => abrirEditar(c)} />
          <Button
            size="small"
            icon={<ThunderboltOutlined />}
            loading={generandoId === c.id}
            onClick={() => generar(c)}
          >
            Generar
          </Button>
          {c.archivo_pdf && (
            <Button size="small" icon={<FilePdfOutlined />} onClick={() => descargar(c, 'pdf')} />
          )}
          {c.archivo_docx && (
            <Button size="small" icon={<FileWordOutlined />} onClick={() => descargar(c, 'docx')} />
          )}
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
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={contratos}
        pagination={false}
        locale={{ emptyText: 'Sin contratos' }}
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
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col xs={24} sm={8}>
              <Form.Item label="No. de contrato" name="numero_contrato">
                <Input placeholder="Opcional" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item label="Folio certificado" name="certificado_folio">
                <Input placeholder="Ej. 5262" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item label="Fecha de firma" name="fecha_contrato">
                <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="Vigencia" name="vigencia">
            <DatePicker.RangePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder={['Desde', 'Hasta']} />
          </Form.Item>
          <Row gutter={16}>
            <Col xs={24} sm={8}>
              <Form.Item label="Precio fumigación" name="precio_fumigacion">
                <InputNumber min={0} precision={2} prefix="$" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item label="Precio sanitización" name="precio_sanitizacion">
                <InputNumber min={0} precision={2} prefix="$" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item label="Precio combo" name="precio_combo" tooltip="Fumigación + sanitización en una exhibición">
                <InputNumber min={0} precision={2} prefix="$" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="Personal asignado" name="personal_asignado">
            <Select
              mode="multiple"
              placeholder="Técnicos asignados al contrato"
              options={tecnicos.map((t) => ({ value: t.id, label: t.nombre }))}
            />
          </Form.Item>
          <Form.Item label="Exclusiones" name="exclusiones">
            <Input.TextArea rows={2} placeholder="Servicios excluidos (opcional)" />
          </Form.Item>
          <Form.Item label="Notas" name="notas">
            <Input.TextArea rows={2} placeholder="Notas internas (opcional)" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default ClienteContratos;
