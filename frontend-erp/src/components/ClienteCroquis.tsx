// src/components/ClienteCroquis.tsx
// Croquis (planos) del cliente para la empresa activa. Se pueden subir varios,
// general o por área. Patrón de adjuntos (modal de subida + tabla).
import React, { useCallback, useEffect, useState } from 'react';
import {
  Card, Button, Table, Space, Popconfirm, message, Tag, Modal, Form, Input,
  Upload, Empty, Tooltip,
} from 'antd';
import {
  UploadOutlined, DownloadOutlined, DeleteOutlined, PlusOutlined, PaperClipOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { clienteService, Croquis } from '@/services/clienteService';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import { formatDate } from '@/utils/formatDate';

interface Props {
  clienteId: string;
}

export const ClienteCroquis: React.FC<Props> = ({ clienteId }) => {
  const { selectedEmpresaId, empresas } = useEmpresaSelector();
  const empresaNombre = empresas.find((e) => e.id === selectedEmpresaId)?.nombre_comercial;

  const [items, setItems] = useState<Croquis[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [form] = Form.useForm();

  // Preview
  const [preview, setPreview] = useState<{ url: string; tipo: 'pdf' | 'imagen'; titulo: string } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const cargar = useCallback(async () => {
    if (!selectedEmpresaId) return;
    setLoading(true);
    try {
      setItems(await clienteService.listCroquis(clienteId, selectedEmpresaId));
    } catch {
      message.error('No se pudieron cargar los croquis');
    } finally {
      setLoading(false);
    }
  }, [clienteId, selectedEmpresaId]);

  useEffect(() => { cargar(); }, [cargar]);

  const abrir = () => {
    form.resetFields();
    setArchivo(null);
    setModalOpen(true);
  };

  const guardar = async () => {
    if (!selectedEmpresaId) { message.error('Selecciona una empresa'); return; }
    const v = await form.validateFields();
    if (!archivo) { message.error('Selecciona el archivo del croquis'); return; }
    setSaving(true);
    try {
      await clienteService.uploadCroquis(clienteId, archivo, {
        empresa_id: selectedEmpresaId,
        titulo: v.titulo || archivo.name,
        area: v.area,
        descripcion: v.descripcion,
      });
      message.success('Croquis subido');
      setModalOpen(false);
      await cargar();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? 'Error al subir el croquis');
    } finally {
      setSaving(false);
    }
  };

  const esImagen = (nombre: string) => /\.(jpe?g|png|webp|gif)$/i.test(nombre);

  const ver = async (c: Croquis) => {
    setPreviewLoading(true);
    try {
      const blob = await clienteService.downloadCroquis(clienteId, c.id);
      const url = window.URL.createObjectURL(blob);
      setPreview({ url, tipo: esImagen(c.archivo) ? 'imagen' : 'pdf', titulo: c.titulo });
    } catch {
      message.error('No se pudo abrir el croquis');
    } finally {
      setPreviewLoading(false);
    }
  };

  const cerrarPreview = () => {
    if (preview) window.URL.revokeObjectURL(preview.url);
    setPreview(null);
  };

  const descargar = async (c: Croquis) => {
    try {
      const blob = await clienteService.downloadCroquis(clienteId, c.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = c.titulo;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error('No se pudo descargar el croquis');
    }
  };

  const eliminar = async (c: Croquis) => {
    try {
      await clienteService.deleteCroquis(clienteId, c.id);
      message.success('Croquis eliminado');
      await cargar();
    } catch {
      message.error('No se pudo eliminar el croquis');
    }
  };

  const columns: ColumnsType<Croquis> = [
    { title: 'Título', dataIndex: 'titulo', key: 'titulo' },
    {
      title: 'Área', dataIndex: 'area', key: 'area', width: 180,
      render: (a: string) => a ? <Tag color="geekblue">{a}</Tag> : <Tag>General</Tag>,
    },
    { title: 'Descripción', dataIndex: 'descripcion', key: 'descripcion', render: (d: string) => d || '—' },
    { title: 'Subido', dataIndex: 'creado_en', key: 'creado_en', width: 150, render: (v: string) => formatDate(v) },
    {
      title: 'Acciones', key: 'acc', width: 150,
      render: (_, c) => (
        <Space>
          <Tooltip title="Ver"><Button type="link" icon={<EyeOutlined />} onClick={() => ver(c)} loading={previewLoading} /></Tooltip>
          <Tooltip title="Descargar"><Button type="link" icon={<DownloadOutlined />} onClick={() => descargar(c)} /></Tooltip>
          <Popconfirm title="¿Eliminar croquis?" onConfirm={() => eliminar(c)} okText="Sí" cancelText="No">
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={`Croquis / Planos${empresaNombre ? ` — ${empresaNombre}` : ''}`}
      size="small"
      style={{ marginBottom: 16 }}
      extra={
        <Tooltip title={!selectedEmpresaId ? 'Selecciona una empresa en la barra superior' : ''}>
          <Button type="primary" icon={<PlusOutlined />} onClick={abrir} disabled={!selectedEmpresaId}>
            Subir croquis
          </Button>
        </Tooltip>
      }
    >
      {!selectedEmpresaId ? (
        <Empty description="Selecciona una empresa en la barra superior" />
      ) : (
        <Table rowKey="id" size="small" loading={loading} columns={columns} dataSource={items}
          pagination={false} locale={{ emptyText: 'Sin croquis' }} scroll={{ x: 700 }} />
      )}

      <Modal
        title="Subir croquis"
        open={modalOpen} onCancel={() => setModalOpen(false)} onOk={guardar}
        confirmLoading={saving} okText="Subir" width={620} destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item label="Título" name="titulo" tooltip="Si lo dejas vacío se usa el nombre del archivo">
            <Input placeholder="Ej. Croquis general, Planta baja" />
          </Form.Item>
          <Form.Item label="Área" name="area" tooltip="Opcional; déjalo vacío para un croquis general">
            <Input placeholder="Ej. Cocina, Bodega" />
          </Form.Item>
          <Form.Item label="Descripción / notas" name="descripcion">
            <Input.TextArea rows={2} placeholder="Opcional" />
          </Form.Item>
          <Form.Item label="Archivo" required>
            <Upload
              accept=".pdf,.jpg,.jpeg,.png,.webp"
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

      {/* Modal de visualización */}
      <Modal
        title={preview?.titulo}
        open={!!preview}
        onCancel={cerrarPreview}
        footer={null}
        width="90%"
        style={{ top: 20, maxWidth: 1000 }}
        styles={{ body: { height: '80vh', padding: 0 } }}
        destroyOnClose
      >
        {preview && (
          preview.tipo === 'imagen' ? (
            <div style={{ width: '100%', height: '100%', overflow: 'auto', textAlign: 'center', background: '#f0f0f0' }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={preview.url} alt={preview.titulo} style={{ maxWidth: '100%' }} />
            </div>
          ) : (
            <iframe src={preview.url} title={preview.titulo} style={{ width: '100%', height: '100%', border: 'none' }} />
          )
        )}
      </Modal>
    </Card>
  );
};

export default ClienteCroquis;
