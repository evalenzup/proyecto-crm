// components/AcuseCancelacionModal.tsx
// Muestra el acuse de cancelación del SAT (PDF) en un modal, con opciones para
// descargar el PDF o el XML oficial. Reutilizable desde la lista y el detalle.
import React, { useEffect, useState, useCallback } from 'react';
import { Modal, Button, Spin, message } from 'antd';
import { FilePdfOutlined, FileExcelOutlined } from '@ant-design/icons';
import { downloadAcuseCancelacion } from '@/services/facturaService';

interface Props {
  facturaId: string | null;
  serie?: string | null;
  folio?: number | string | null;
  open: boolean;
  onClose: () => void;
  /** Descargador del acuse. Por defecto el de facturas; los complementos de
   *  pago inyectan el suyo para reutilizar este mismo modal. */
  fetchAcuse?: (id: string, fmt: 'pdf' | 'xml') => Promise<Blob>;
  /** Prefijo del nombre de archivo (una factura y un pago pueden compartir serie-folio). */
  etiqueta?: string;
}

export const AcuseCancelacionModal: React.FC<Props> = ({
  facturaId, serie, folio, open, onClose,
  fetchAcuse = downloadAcuseCancelacion,
  etiqueta = 'acuse_cancelacion',
}) => {
  const [loading, setLoading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const nombreBase = `${etiqueta}_${serie ?? ''}-${folio ?? facturaId ?? ''}`;

  const cargar = useCallback(async () => {
    if (!facturaId) return;
    setLoading(true);
    setError(null);
    try {
      const blob = await fetchAcuse(facturaId, 'pdf');
      setPdfUrl(window.URL.createObjectURL(blob));
    } catch (e: any) {
      // El interceptor ya muestra el toast; aquí dejamos el detalle en el modal.
      setError(e?.response?.data?.error?.detail || e?.response?.data?.detail || 'No se pudo obtener el acuse del SAT.');
    } finally {
      setLoading(false);
    }
  }, [facturaId, fetchAcuse]);

  useEffect(() => {
    if (open) cargar();
    return () => {
      setPdfUrl((prev) => {
        if (prev) window.URL.revokeObjectURL(prev);
        return null;
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, facturaId]);

  const descargar = (fmt: 'pdf' | 'xml') => async () => {
    if (!facturaId) return;
    try {
      const blob = await fetchAcuse(facturaId, fmt);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${nombreBase}.${fmt}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo descargar el acuse');
    }
  };

  return (
    <Modal
      title="Acuse de cancelación (SAT)"
      open={open}
      onCancel={onClose}
      width="90%"
      style={{ top: 20 }}
      styles={{ body: { height: '78vh', padding: 0 } }}
      destroyOnHidden
      footer={[
        <Button key="close" onClick={onClose}>Cerrar</Button>,
        <Button key="xml" icon={<FileExcelOutlined />} onClick={descargar('xml')} disabled={!pdfUrl}>
          Descargar XML
        </Button>,
        <Button key="pdf" type="primary" icon={<FilePdfOutlined />} onClick={descargar('pdf')} disabled={!pdfUrl}>
          Descargar PDF
        </Button>,
      ]}
    >
      {loading ? (
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
          <Spin size="large" />
          <span style={{ color: '#888' }}>Obteniendo acuse del SAT…</span>
        </div>
      ) : error ? (
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, textAlign: 'center', color: '#cf1322' }}>
          {error}
        </div>
      ) : pdfUrl ? (
        <iframe src={pdfUrl} title="Acuse de cancelación" style={{ width: '100%', height: '100%', border: 'none' }} />
      ) : null}
    </Modal>
  );
};

export default AcuseCancelacionModal;
