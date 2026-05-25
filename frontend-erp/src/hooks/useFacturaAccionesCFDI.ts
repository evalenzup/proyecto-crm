// Handles all CFDI actions: timbrar, cancel flow, SAT verify, PDF/XML download, preview modal
import { useState } from 'react';
import { message } from 'antd';
import type { FormInstance } from 'antd';
import * as svc from '@/services/facturaService';
import { normalizeHttpError } from '@/utils/httpError';
import { applyFormErrors } from '@/utils/formErrors';

type EstatusCFDI = 'BORRADOR' | 'TIMBRADA' | 'EN_CANCELACION' | 'CANCELADA';

interface Props {
  id: string | undefined;
  estatusCFDI: EstatusCFDI;
  setEstatusCFDI: (s: EstatusCFDI) => void;
  setFechaSolicitudCancelacion: (d: string | null) => void;
  form: FormInstance;
  rfcEmisor: string;
  motivosCancel: { value: string; label: string }[];
  cancelForm: FormInstance;
  fetchInitialData: () => Promise<void>;
}

export const useFacturaAccionesCFDI = ({
  id,
  estatusCFDI,
  setEstatusCFDI,
  setFechaSolicitudCancelacion,
  form,
  rfcEmisor,
  motivosCancel,
  cancelForm,
  fetchInitialData,
}: Props) => {
  const [accionLoading, setAccionLoading] = useState({
    timbrar: false,
    cancelar: false,
    verificarSat: false,
    revertir: false,
  });
  const [cancelSubmitting, setCancelSubmitting] = useState(false);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);

  // ── Timbrar ──────────────────────────────────────────────────────────────────
  const timbrarFactura = async () => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, timbrar: true }));
    try {
      await svc.timbrarFactura(id);
      message.success('Factura timbrada');
      await fetchInitialData();
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e) || 'No se pudo timbrar');
    } finally {
      setAccionLoading((s) => ({ ...s, timbrar: false }));
    }
  };

  // ── Cancel flow ──────────────────────────────────────────────────────────────
  const abrirModalCancelacion = () => {
    cancelForm.resetFields();
    cancelForm.setFieldsValue({ motivo: motivosCancel?.[0]?.value || '02', folio_sustitucion: undefined });
    setCancelModalOpen(true);
  };

  const submitCancel = async () => {
    if (!id) return;
    try {
      const vals = await cancelForm.validateFields();
      const motivo = String(vals.motivo || '');
      const folio = motivo === '01' ? (vals.folio_sustitucion || '').trim() || null : null;
      setCancelSubmitting(true);
      const data = await svc.cancelarFactura(id, motivo, folio || undefined);
      setEstatusCFDI(data.estatus || 'CANCELADA');
      message.success(data?.message || 'Solicitud de cancelación enviada');
      setCancelModalOpen(false);
    } catch (e: any) {
      if (!e?.errorFields) {
        applyFormErrors(e, cancelForm);
        if (!e?._handled) message.error(normalizeHttpError(e) || 'No se pudo cancelar');
      }
    } finally {
      setCancelSubmitting(false);
    }
  };

  // ── PDF preview / download ───────────────────────────────────────────────────
  const verPDF = async () => {
    if (!id) {
      message.info('Guarda la factura para generar la vista previa.');
      return;
    }
    try {
      const blob = estatusCFDI === 'BORRADOR' ? await svc.getPdfPreview(id) : await svc.getPdf(id);
      const url = window.URL.createObjectURL(blob);
      setPreviewPdfUrl(url);
      setPreviewModalOpen(true);
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e) || 'No se pudo abrir el PDF');
    }
  };

  const cerrarPreview = () => {
    setPreviewModalOpen(false);
    if (previewPdfUrl) { URL.revokeObjectURL(previewPdfUrl); setPreviewPdfUrl(null); }
  };

  const _safeFilename = (s: string) => s.replace(/[^a-zA-Z0-9._-]/g, '');

  const descargarPDF = async () => {
    if (!id) return;
    try {
      const blob = estatusCFDI === 'BORRADOR' ? await svc.getPdfPreview(id) : await svc.downloadPdf(id);
      const url = window.URL.createObjectURL(blob);
      const rfc = _safeFilename((rfcEmisor || 'RFC').toUpperCase().replace(/\s+/g, ''));
      const serie = _safeFilename((form.getFieldValue('serie') || 'S/N').toString().replace(/\s+/g, ''));
      const folio = _safeFilename((form.getFieldValue('folio') || id).toString().replace(/\s+/g, ''));
      const a = document.createElement('a');
      a.href = url; a.download = `${rfc}-factura-${serie}-${folio}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch (e: any) {
      const msg = await import('@/utils/httpError').then((m) => m.parseBlobError(e));
      message.error(msg || 'No se pudo descargar el PDF');
    }
  };

  const descargarXML = async () => {
    if (!id) return;
    try {
      const blob = await svc.downloadXml(id);
      const url = window.URL.createObjectURL(blob);
      const rfc = _safeFilename((rfcEmisor || 'RFC').toUpperCase().replace(/\s+/g, ''));
      const serie = _safeFilename((form.getFieldValue('serie') || 'S/N').toString().replace(/\s+/g, ''));
      const folio = _safeFilename((form.getFieldValue('folio') || id).toString().replace(/\s+/g, ''));
      const a = document.createElement('a');
      a.href = url; a.download = `${rfc}-factura-${serie}-${folio}.xml`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e) || 'No se pudo descargar el XML');
    }
  };

  // ── SAT verification / revert ────────────────────────────────────────────────
  const handleVerificarSAT = async () => {
    if (!id) return;
    setAccionLoading((p) => ({ ...p, verificarSat: true }));
    try {
      const result = await svc.verificarEstadoSAT(id);
      if (result.actualizado) {
        setEstatusCFDI(result.estatus_nuevo as EstatusCFDI);
        if (result.estatus_nuevo !== 'EN_CANCELACION') setFechaSolicitudCancelacion(null);
        message.success(`Estado actualizado: ${result.estatus_anterior} → ${result.estatus_nuevo}`);
      } else {
        message.info(`Sin cambios. SAT reporta: ${result.sat_estado} — ${result.sat_estatus_cancelacion || 'sin estatus de cancelación'}`);
      }
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e) || 'Error al consultar el SAT');
    } finally {
      setAccionLoading((p) => ({ ...p, verificarSat: false }));
    }
  };

  const handleRevertirCancelacion = async () => {
    if (!id) return;
    setAccionLoading((p) => ({ ...p, revertir: true }));
    try {
      await svc.revertirCancelacion(id);
      setEstatusCFDI('TIMBRADA');
      setFechaSolicitudCancelacion(null);
      message.success('Factura revertida a TIMBRADA correctamente');
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e) || 'Error al revertir la cancelación');
    } finally {
      setAccionLoading((p) => ({ ...p, revertir: false }));
    }
  };

  return {
    accionLoading,
    cancelSubmitting,
    cancelModalOpen, setCancelModalOpen,
    previewModalOpen, previewPdfUrl,
    timbrarFactura,
    abrirModalCancelacion, submitCancel,
    verPDF, cerrarPreview, descargarPDF, descargarXML,
    handleVerificarSAT, handleRevertirCancelacion,
  };
};
