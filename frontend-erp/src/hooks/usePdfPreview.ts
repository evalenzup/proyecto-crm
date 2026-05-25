// Shared hook: PDF preview modal state used by useFacturasList and usePagosList
import { useState } from 'react';

export const usePdfPreview = <TRow = unknown>() => {
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);
  const [previewRow, setPreviewRow] = useState<TRow | null>(null);

  const openPreview = (blob: Blob, row: TRow) => {
    const url = window.URL.createObjectURL(blob);
    setPreviewPdfUrl(url);
    setPreviewRow(row);
    setPreviewModalOpen(true);
  };

  const cerrarPreview = () => {
    setPreviewModalOpen(false);
    setPreviewRow(null);
    if (previewPdfUrl) {
      window.URL.revokeObjectURL(previewPdfUrl);
      setPreviewPdfUrl(null);
    }
  };

  return { previewModalOpen, previewPdfUrl, previewRow, openPreview, cerrarPreview };
};
