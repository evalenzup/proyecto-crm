// src/components/EmpresaPlantillaContrato.tsx
// Subir / descargar / eliminar la plantilla de contrato (.docx) de una empresa.
import React, { useState } from 'react';
import { Space, Button, Upload, Popconfirm, Tag, Typography, message } from 'antd';
import { UploadOutlined, DownloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { empresaService } from '@/services/empresaService';

const { Text } = Typography;

interface Props {
  empresaId: string;
  /** nombre de archivo actual de la plantilla, o null si no tiene */
  plantillaActual?: string | null;
}

export const EmpresaPlantillaContrato: React.FC<Props> = ({ empresaId, plantillaActual }) => {
  const [tiene, setTiene] = useState<boolean>(!!plantillaActual);
  const [busy, setBusy] = useState(false);

  const subir = async (file: File) => {
    setBusy(true);
    try {
      await empresaService.uploadPlantillaContrato(empresaId, file);
      message.success('Plantilla de contrato actualizada');
      setTiene(true);
    } catch (e: any) {
      if (!e?._handled) message.error(e?.response?.data?.detail ?? 'Error al subir la plantilla');
    } finally {
      setBusy(false);
    }
    return false;
  };

  const descargar = async () => {
    try {
      const blob = await empresaService.downloadPlantillaContrato(empresaId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `plantilla_contrato.docx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error('No se pudo descargar la plantilla');
    }
  };

  const eliminar = async () => {
    try {
      await empresaService.deletePlantillaContrato(empresaId);
      message.success('Plantilla eliminada');
      setTiene(false);
    } catch {
      message.error('No se pudo eliminar la plantilla');
    }
  };

  return (
    <div style={{ marginTop: 8 }}>
      <Space wrap align="center">
        <Text type="secondary">Plantilla de contrato (.docx):</Text>
        {tiene
          ? <Tag color="green">Configurada</Tag>
          : <Tag color="orange">Sin plantilla</Tag>}
        <Upload accept=".docx" showUploadList={false} beforeUpload={(f) => subir(f as File)}>
          <Button icon={<UploadOutlined />} loading={busy} size="small">
            {tiene ? 'Reemplazar' : 'Subir plantilla'}
          </Button>
        </Upload>
        {tiene && (
          <>
            <Button icon={<DownloadOutlined />} size="small" onClick={descargar}>Descargar</Button>
            <Popconfirm title="¿Eliminar plantilla?" onConfirm={eliminar} okText="Sí" cancelText="No">
              <Button icon={<DeleteOutlined />} size="small" danger />
            </Popconfirm>
          </>
        )}
      </Space>
      <div style={{ fontSize: 12, color: '#999', marginTop: 6 }}>
        Documento Word con los placeholders del contrato. Sin plantilla, no se pueden generar contratos para esta empresa.
      </div>
    </div>
  );
};

export default EmpresaPlantillaContrato;
