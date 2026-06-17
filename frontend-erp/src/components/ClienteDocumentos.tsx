// src/components/ClienteDocumentos.tsx
// Sección de documentos adjuntos del cliente (contrato firmado, identificación, etc.)
// Se muestra solo en modo edición (requiere cliente id).
import React, { useEffect, useState } from 'react';
import { Card, Upload, Button, Select, Table, Space, Popconfirm, message, Tag } from 'antd';
import { UploadOutlined, DownloadOutlined, DeleteOutlined } from '@ant-design/icons';
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
  const [uploading, setUploading] = useState(false);
  const [tipo, setTipo] = useState('CONTRATO');

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

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await clienteService.uploadDocumento(clienteId, file, tipo, file.name);
      message.success('Documento subido');
      await cargar();
    } catch (e: any) {
      if (!e?._handled) message.error(e?.response?.data?.detail ?? 'Error al subir el documento');
    } finally {
      setUploading(false);
    }
    return false; // evita el upload automático de antd
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
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      width: 150,
      render: (t: string) => <Tag color={TIPO_COLOR[t] ?? 'default'}>{t}</Tag>,
    },
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    {
      title: 'Subido',
      dataIndex: 'creado_en',
      key: 'creado_en',
      width: 160,
      render: (v: string) => formatDate(v),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 120,
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
    <Card title="Documentos / Contrato" size="small" style={{ marginBottom: 16 }}>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select value={tipo} onChange={setTipo} style={{ width: 200 }} options={TIPOS} />
        <Upload accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx" showUploadList={false} beforeUpload={(f) => handleUpload(f as File)}>
          <Button icon={<UploadOutlined />} loading={uploading}>Subir documento</Button>
        </Upload>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={docs}
        pagination={false}
        locale={{ emptyText: 'Sin documentos' }}
      />
    </Card>
  );
};

export default ClienteDocumentos;
