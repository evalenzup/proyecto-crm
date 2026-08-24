// src/components/VisorPdfModal.tsx
'use client';

/**
 * Muestra un PDF del sistema dentro de un modal.
 *
 * No se puede abrir la ruta en una pestaña nueva: el endpoint va protegido y el
 * navegador no manda el token en una navegación normal, así que respondía 401.
 * Aquí se descarga con la sesión, se arma un blob y ése es el que se muestra.
 */

import React from 'react';
import { Alert, Button, Modal, Spin, Space } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import api from '@/lib/axios';

interface Props {
  /** Ruta del API, por ejemplo "/conciliacion/{id}/pdf". null = cerrado. */
  url: string | null;
  titulo: string;
  /** Nombre con el que se guarda si decide descargarlo. */
  nombreArchivo: string;
  onClose: () => void;
}

export const VisorPdfModal: React.FC<Props> = ({ url, titulo, nombreArchivo, onClose }) => {
  const [blobUrl, setBlobUrl] = React.useState<string | null>(null);
  const [cargando, setCargando] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!url) return;
    let vigente = true;
    let creado: string | null = null;

    setCargando(true);
    setError(null);
    api.get(url, { responseType: 'blob' })
      .then(({ data }) => {
        if (!vigente) return;
        creado = window.URL.createObjectURL(
          new Blob([data], { type: 'application/pdf' }),
        );
        setBlobUrl(creado);
      })
      .catch((e: any) => {
        if (!vigente) return;
        setError(e?.response?.status === 404
          ? 'El archivo ya no está disponible en el servidor.'
          : 'No se pudo abrir el documento.');
      })
      .finally(() => vigente && setCargando(false));

    return () => {
      vigente = false;
      // Se libera la memoria del blob al cerrar
      if (creado) window.URL.revokeObjectURL(creado);
      setBlobUrl(null);
    };
  }, [url]);

  const descargar = () => {
    if (!blobUrl) return;
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = nombreArchivo;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <Modal
      open={!!url}
      title={titulo}
      onCancel={onClose}
      width="90vw"
      style={{ top: 24, maxWidth: 1100 }}
      styles={{ body: { padding: 0, height: 'calc(100vh - 180px)' } }}
      footer={
        <Space>
          <Button icon={<DownloadOutlined />} onClick={descargar} disabled={!blobUrl}>
            Descargar
          </Button>
          <Button type="primary" onClick={onClose}>Cerrar</Button>
        </Space>
      }
      destroyOnClose
    >
      {cargando && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                      height: '100%' }}>
          <Spin size="large" tip="Abriendo el documento…" />
        </div>
      )}
      {error && <Alert type="error" showIcon message={error} style={{ margin: 16 }} />}
      {blobUrl && !error && (
        <iframe
          src={blobUrl}
          title={titulo}
          style={{ width: '100%', height: '100%', border: 'none' }}
        />
      )}
    </Modal>
  );
};

export default VisorPdfModal;
