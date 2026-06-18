// src/components/ClienteDocumentos.tsx
// Documentos adjuntos del cliente. La subida es vía modal: tipo + archivo, y
// para contratos se capturan número y vigencia. Solo en modo edición.
import React, { useEffect, useState } from 'react';
import {
  Card, Button, Select, Table, Space, Popconfirm, message, Tag, Modal, Form,
  Input, DatePicker, Upload, Row, Col,
} from 'antd';
import { UploadOutlined, DownloadOutlined, DeleteOutlined, PlusOutlined, PaperClipOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { clienteService, ClienteDocumento } from '@/services/clienteService';
import { formatDate } from '@/utils/formatDate';

const TIPOS = [
  { value: 'CONTRATO', label: 'Contrato' },
  { value: 'IDENTIFICACION', label: 'Identificación' },
  { value: 'CONSTANCIA_FISCAL', label: 'Constancia fiscal' },
  { value: 'OTRO', label: 'Otro' },
];

const TIPO_COLOR: Record<string, string> = {
  CONTRATO: 'blue',
  IDENTIFICACION: 'green',
  CONSTANCIA_FISCAL: 'gold',
  OTRO: 'default',
};

interface Props {
  clienteId: string;
}

export const ClienteDocumentos: React.FC<Props> = ({ clienteId }) => {
  const [docs, setDocs] = useState<ClienteDocumento[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [form] = Form.useForm();
  const tipoSel = Form.useWatch('tipo', form);

  const cargar = async () => {
    setLoading(true);
    try {
      setDocs(await clienteService.listDocumentos(clienteId));
    } catch {
      message.error('No se pudieron cargar los documentos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (clienteId) cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteId]);

  const abrirModal = () => {
    form.resetFields();
    form.setFieldsValue({ tipo: 'CONTRATO' });
    setArchivo(null);
    setModalOpen(true);
  };

  const guardar = async () => {
    const v = await form.validateFields();
    if (!archivo) { message.error('Selecciona el archivo a subir'); return; }
    setSaving(true);
    try {
      await clienteService.uploadDocumento(clienteId, archivo, {
        tipo: v.tipo,
        nombre: v.nombre || archivo.name,
        numero: v.numero,
        vigencia_desde: v.vigencia?.[0]?.format('YYYY-MM-DD'),
        vigencia_hasta: v.vigencia?.[1]?.format('YYYY-MM-DD'),
        notas: v.notas,
      });
      message.success('Documento subido');
      setModalOpen(false);
      await cargar();
    } catch (e: any) {
      if (e?.errorFields) return;
      if (!e?._handled) message.error(e?.response?.data?.detail ?? 'Error al subir el documento');
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async (doc: ClienteDocumento) => {
    try {
      const blob = await clienteService.downloadDocumento(clienteId, doc.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = doc.nombre;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error('No se pudo descargar el documento');
    }
  };

  const handleDelete = async (doc: ClienteDocumento) => {
    try {
      await clienteService.deleteDocumento(clienteId, doc.id);
      message.success('Documento eliminado');
      await cargar();
    } catch {
      message.error('No se pudo eliminar el documento');
    }
  };

  const columns = [
    {
      title: 'Tipo', dataIndex: 'tipo', key: 'tipo', width: 140,
      render: (t: string) => <Tag color={TIPO_COLOR[t] ?? 'default'}>{t}</Tag>,
    },
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    { title: 'No.', dataIndex: 'numero', key: 'numero', width: 90, render: (n: string) => n || '—' },
    {
      title: 'Vigencia', key: 'vigencia', width: 180,
      render: (_: unknown, d: ClienteDocumento) =>
        d.vigencia_desde || d.vigencia_hasta
          ? `${d.vigencia_desde ?? '—'} → ${d.vigencia_hasta ?? '—'}`
          : '—',
    },
    { title: 'Subido', dataIndex: 'creado_en', key: 'creado_en', width: 150, render: (v: string) => formatDate(v) },
    {
      title: 'Acciones', key: 'acciones', width: 110,
      render: (_: unknown, doc: ClienteDocumento) => (
        <Space>
          <Button type="link" icon={<DownloadOutlined />} onClick={() => handleDownload(doc)} />
          <Popconfirm title="¿Eliminar documento?" onConfirm={() => handleDelete(doc)} okText="Sí" cancelText="No">
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="Documentos / Contrato"
      size="small"
      style={{ marginBottom: 16 }}
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={abrirModal}>Subir documento</Button>}
    >
      <Table
        rowKey="id" size="small" loading={loading} columns={columns}
        dataSource={docs} pagination={false} locale={{ emptyText: 'Sin documentos' }}
      />

      <Modal
        title="Subir documento"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={guardar}
        confirmLoading={saving}
        okText="Subir"
        width={620}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item label="Tipo de documento" name="tipo" rules={[{ required: true }]}>
                <Select options={TIPOS} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Nombre / descripción" name="nombre" tooltip="Si lo dejas vacío se usa el nombre del archivo">
                <Input placeholder="Opcional" />
              </Form.Item>
            </Col>
          </Row>

          {tipoSel === 'CONTRATO' && (
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item label="No. de contrato" name="numero">
                  <Input placeholder="Ej. C-001" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={16}>
                <Form.Item label="Vigencia" name="vigencia">
                  <DatePicker.RangePicker style={{ width: '100%' }} format="DD/MM/YYYY" placeholder={['Desde', 'Hasta']} />
                </Form.Item>
              </Col>
            </Row>
          )}

          {tipoSel === 'CONTRATO' && (
            <Form.Item label="Notas" name="notas">
              <Input.TextArea rows={2} placeholder="Observaciones (opcional)" />
            </Form.Item>
          )}

          <Form.Item label="Archivo" required>
            <Upload
              accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx"
              showUploadList={true}
              maxCount={1}
              beforeUpload={(f) => { setArchivo(f as File); return false; }}
              onRemove={() => setArchivo(null)}
            >
              <Button icon={<UploadOutlined />}>Seleccionar archivo</Button>
            </Upload>
            {archivo && <div style={{ marginTop: 6, fontSize: 12, color: '#999' }}><PaperClipOutlined /> {archivo.name}</div>}
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default ClienteDocumentos;
