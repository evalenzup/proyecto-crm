//frontend-erp/src/hooks/useFacturaForm.ts
// Composition hook: assembles useFacturaCatalogos + useFacturaConceptos + useFacturaAccionesCFDI
// plus the integration logic (initial data load, empresa/cliente handlers, save).

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useRouter } from 'next/router';
import { Form, message } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import debounce from 'lodash/debounce';
import * as svc from '@/services/facturaService';
import { normalizeHttpError } from '@/utils/httpError';
import { normalizeISOToUTC } from '@/utils/formatDate';
import { applyFormErrors } from '@/utils/formErrors';
import { useEmpresaSelector } from './useEmpresaSelector';
import { useFacturaCatalogos } from './useFacturaCatalogos';
import { useFacturaConceptos } from './useFacturaConceptos';
import { useFacturaAccionesCFDI } from './useFacturaAccionesCFDI';

type EstatusCFDI = 'BORRADOR' | 'TIMBRADA' | 'EN_CANCELACION' | 'CANCELADA';
type StatusPago = 'PAGADA' | 'NO_PAGADA';

export const useFacturaForm = () => {
  const router = useRouter();
  const raw = router.query.id;
  const id = Array.isArray(raw) ? raw[0] : (raw as string | undefined);

  // ── Form instances ────────────────────────────────────────────────────────────
  const [form] = Form.useForm();
  const [conceptoForm] = Form.useForm();
  const [psForm] = Form.useForm();
  const [cancelForm] = Form.useForm();

  // ── UI state ──────────────────────────────────────────────────────────────────
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // ── Invoice metadata ──────────────────────────────────────────────────────────
  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);
  const [estatusCFDI, setEstatusCFDI] = useState<EstatusCFDI>('BORRADOR');
  const [statusPago, setStatusPago] = useState<StatusPago>('NO_PAGADA');
  const [rfcEmisor, setRfcEmisor] = useState<string>('');
  const [fechaSolicitudCancelacion, setFechaSolicitudCancelacion] = useState<string | null>(null);
  const [retencionLocalMonto, setRetencionLocalMonto] = useState<number | null>(null);

  // ── Empresa / Cliente ─────────────────────────────────────────────────────────
  const [currentEmpresa, setCurrentEmpresa] = useState<any | null>(null);
  const [clienteOpts, setClienteOpts] = useState<{ label: string; value: string }[]>([]);
  const [diasCreditoCliente, setDiasCreditoCliente] = useState<number>(0);

  // Global empresa selector (sidebar)
  const { selectedEmpresaId: globalEmpresaId } = useEmpresaSelector();
  const globalEmpresaIdRef = useRef(globalEmpresaId);
  useEffect(() => { globalEmpresaIdRef.current = globalEmpresaId; }, [globalEmpresaId]);

  // ── Watchers ──────────────────────────────────────────────────────────────────
  const empresaId = Form.useWatch('empresa_id', form);
  const moneda = Form.useWatch('moneda', form);
  const metodoPago = Form.useWatch('metodo_pago', form);
  Form.useWatch('forma_pago', form); // side-effect watcher

  // ── Sub-hooks ─────────────────────────────────────────────────────────────────
  const catalogos = useFacturaCatalogos();

  const conceptosHook = useFacturaConceptos(form, conceptoForm);

  const acciones = useFacturaAccionesCFDI({
    id,
    estatusCFDI,
    setEstatusCFDI,
    setFechaSolicitudCancelacion,
    form,
    rfcEmisor,
    motivosCancel: catalogos.motivosCancel,
    cancelForm,
    fetchInitialData: async () => { await fetchInitialData(); },
  });

  // ── Derived flags ─────────────────────────────────────────────────────────────
  const isFormDisabled =
    estatusCFDI === 'TIMBRADA' || estatusCFDI === 'EN_CANCELACION' || estatusCFDI === 'CANCELADA';
  const fieldDisabled = (defaultDisabled: boolean) => (isFormDisabled ? true : defaultDisabled);
  const fieldAlwaysEditable = (name: string) => {
    if (name === 'fecha_pago') return estatusCFDI === 'CANCELADA' || estatusCFDI === 'EN_CANCELACION';
    return ['status_pago', 'fecha_cobro', 'observaciones'].includes(name) ? false : isFormDisabled;
  };

  const puedeTimbrar = Boolean(id) && estatusCFDI === 'BORRADOR';
  const puedeCancelar = Boolean(id) && estatusCFDI === 'TIMBRADA';
  const puedeVerificarSat = Boolean(id) && (estatusCFDI === 'EN_CANCELACION' || estatusCFDI === 'TIMBRADA' || estatusCFDI === 'CANCELADA');
  const puedeRevertir = Boolean(id) && estatusCFDI === 'EN_CANCELACION';

  // ── Forma de pago options (filtered by PUE/PPD) ───────────────────────────────
  const formaPagoOptions = useMemo(() => {
    const POR_DEFINIR = '99';
    if (!metodoPago) return catalogos.formasPago;
    if (metodoPago === 'PUE') return (catalogos.formasPago || []).filter((f) => f.value !== POR_DEFINIR);
    if (metodoPago === 'PPD') return (catalogos.formasPago || []).filter((f) => f.value === POR_DEFINIR);
    return catalogos.formasPago;
  }, [catalogos.formasPago, metodoPago]);

  // Auto-set forma_pago when metodo_pago changes
  useEffect(() => {
    const POR_DEFINIR = '99';
    if (!metodoPago) return;
    const current = form.getFieldValue('forma_pago');
    if (metodoPago === 'PUE' && current === POR_DEFINIR) {
      form.setFieldValue('forma_pago', undefined);
    } else if (metodoPago === 'PPD' && current !== POR_DEFINIR) {
      form.setFieldValue('forma_pago', POR_DEFINIR);
    }
  }, [metodoPago, form]);

  // ── Empresa change ────────────────────────────────────────────────────────────
  const onEmpresaChange = useCallback(async (empId?: string) => {
    form.setFieldsValue({
      cliente_id: undefined,
      nombre_fiscal_receptor: undefined,
      rfc_receptor: undefined,
      regimen_fiscal_receptor: undefined,
      cp_receptor: undefined,
    });
    setClienteOpts([]);
    setDiasCreditoCliente(0);

    if (!empId) {
      form.setFieldsValue({
        nombre_fiscal_emisor: undefined,
        regimen_fiscal_emisor: undefined,
        lugar_expedicion: undefined,
      });
      setRfcEmisor('');
      setCurrentEmpresa(null);
      return;
    }

    const data = await svc.getEmpresaById(empId);
    setCurrentEmpresa(data);
    form.setFieldsValue({
      nombre_fiscal_emisor: data.nombre ?? data.nombre_comercial,
      regimen_fiscal_emisor: data.regimen_fiscal,
      lugar_expedicion: data.codigo_postal,
    });
    setRfcEmisor((data?.rfc || '').toUpperCase());

    try {
      const res = await (await import('@/lib/axios')).default.get('/facturas/', {
        params: { empresa_id: empId, limit: 1, offset: 0, order_by: 'serie_folio', order_dir: 'desc' },
      });
      const last = res?.data?.items?.[0];
      form.setFieldValue('folio', last?.folio ? Number(last.folio) + 1 : 1);
    } catch {
      form.setFieldValue('folio', 1);
    }
  }, [form]);

  // ── Cliente search ────────────────────────────────────────────────────────────
  const buscarClientes = useMemo(
    () =>
      debounce(async (q: string) => {
        const empId = form.getFieldValue('empresa_id');
        if (!empId || !q || q.trim().length < 3) { setClienteOpts([]); return; }
        try {
          const data = await svc.searchClientes(q, empId);
          setClienteOpts(
            (data || []).map((c: any) => ({
              value: c.id,
              label: c.nombre_comercial ?? c.razon_social ?? c.nombre ?? 'Cliente',
            })),
          );
        } catch { setClienteOpts([]); }
      }, 350),
    [form],
  );

  // ── Cliente change ────────────────────────────────────────────────────────────
  const onClienteChange = useCallback(async (cid?: string) => {
    if (!cid) {
      form.setFieldsValue({
        nombre_fiscal_receptor: undefined,
        rfc_receptor: undefined,
        regimen_fiscal_receptor: undefined,
        cp_receptor: undefined,
        fecha_pago: null,
      });
      setDiasCreditoCliente(0);
      return;
    }
    const data = await svc.getClienteById(cid);
    form.setFieldsValue({
      nombre_fiscal_receptor: data.nombre_razon_social ?? data.nombre_comercial,
      rfc_receptor: data.rfc,
      regimen_fiscal_receptor: data.regimen_fiscal,
      cp_receptor: data.codigo_postal,
      cliente: { email: data.email },
    });
    const dias = Number(data.dias_credito ?? 0);
    setDiasCreditoCliente(dias);
    const fe = form.getFieldValue('fecha_emision') as Dayjs | undefined;
    if (fe && dayjs.isDayjs(fe)) form.setFieldValue('fecha_pago', fe.add(dias, 'day'));
  }, [form]);

  // ── Fecha emisión change ──────────────────────────────────────────────────────
  const onFechaEmisionChange = (d: Dayjs | null) => {
    if (!d) { form.setFieldsValue({ fecha_pago: null, fecha_cobro: null }); return; }
    form.setFieldsValue({
      fecha_pago: d.add(diasCreditoCliente || 0, 'day'),
      ...(form.getFieldValue('status_pago') === 'PAGADA' ? { fecha_cobro: d.add(diasCreditoCliente || 0, 'day') } : {}),
    });
  };

  // ── Initial data fetch ────────────────────────────────────────────────────────
  const fetchInitialData = useCallback(async () => {
    try {
      const empOptions = await catalogos.fetchCatalogos();

      if (id) {
        const data = await svc.getFacturaById(id);
        setEstatusCFDI(data.estatus);
        setStatusPago(data.status_pago);
        setFechaSolicitudCancelacion(data.fecha_solicitud_cancelacion ?? null);
        setRetencionLocalMonto(data.retencion_local_monto != null ? Number(data.retencion_local_monto) : null);

        await onEmpresaChange(data.empresa_id);

        if (data.cliente_id) {
          try {
            const cli = await svc.getClienteById(data.cliente_id);
            const label = cli?.nombre_comercial ?? cli?.razon_social ?? cli?.nombre ?? 'Cliente';
            setClienteOpts([{ value: data.cliente_id, label }]);
            form.setFieldValue('cliente_id', data.cliente_id);
            await onClienteChange(data.cliente_id);
          } catch {
            form.setFieldValue('cliente_id', data.cliente_id);
          }
        }

        const conceptosCargados = (data.conceptos || []).map((c: any) => ({
          ...c,
          cantidad: Number(c.cantidad ?? 0),
          valor_unitario: Number(c.valor_unitario ?? 0),
          descuento: c.descuento != null ? Number(c.descuento) : null,
          iva_tasa: c.iva_tasa != null ? Number(c.iva_tasa) : 0,
          ret_iva_tasa: c.ret_iva_tasa != null ? Number(c.ret_iva_tasa) : 0,
          ret_isr_tasa: c.ret_isr_tasa != null ? Number(c.ret_isr_tasa) : 0,
        }));
        conceptosHook.setConceptos(conceptosCargados);

        form.setFieldsValue({
          empresa_id: data.empresa_id,
          serie: data.serie ?? undefined,
          folio: data.folio,
          moneda: data.moneda,
          tipo_cambio: data.tipo_cambio ?? undefined,
          metodo_pago: data.metodo_pago ?? undefined,
          forma_pago: data.forma_pago ?? undefined,
          uso_cfdi: data.uso_cfdi ?? undefined,
          lugar_expedicion: data.lugar_expedicion ?? undefined,
          condiciones_pago: data.condiciones_pago ?? undefined,
          cfdi_relacionados_tipo: data.cfdi_relacionados_tipo ?? undefined,
          cfdi_relacionados: data.cfdi_relacionados ?? undefined,
          tiene_relacion: !!(data.cfdi_relacionados_tipo || data.cfdi_relacionados),
          status_pago: data.status_pago,
          folio_fiscal: data.folio_fiscal ?? (data as any).cfdi_uuid ?? undefined,
          fecha_emision: data.fecha_emision ? dayjs(normalizeISOToUTC(data.fecha_emision)) : dayjs(),
          fecha_timbrado: data.fecha_timbrado ? dayjs(normalizeISOToUTC(data.fecha_timbrado)) : null,
          fecha_pago: data.fecha_pago ? dayjs(normalizeISOToUTC(data.fecha_pago)) : null,
          fecha_cobro: data.fecha_cobro ? dayjs(normalizeISOToUTC(data.fecha_cobro)) : null,
          observaciones: data.observaciones ?? undefined,
          retencion_local_desc: data.retencion_local_desc ?? undefined,
          retencion_local_tasa: data.retencion_local_tasa != null ? Number(data.retencion_local_tasa) : undefined,
        });
        setMetadata({ creado_en: data.creado_en, actualizado_en: data.actualizado_en });
      } else {
        conceptosHook.setConceptos([]);
        setEstatusCFDI('BORRADOR');
        setStatusPago('NO_PAGADA');
        form.setFieldsValue({ moneda: 'MXN', tiene_relacion: false, fecha_emision: dayjs(), status_pago: 'NO_PAGADA' });

        const globalId = globalEmpresaIdRef.current;
        const defaultId =
          globalId && empOptions.some((e) => e.value === globalId)
            ? globalId
            : empOptions.length === 1 ? empOptions[0].value : undefined;
        if (defaultId) {
          form.setFieldValue('empresa_id', defaultId);
          await onEmpresaChange(defaultId);
        }
      }
    } catch (e) {
      console.error(e);
      message.error(normalizeHttpError(e) || 'Error al cargar catálogos/empresas');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => { fetchInitialData(); }, [fetchInitialData]);

  // ── Save ──────────────────────────────────────────────────────────────────────
  const normalizeConcepto = (c: any) => ({
    clave_producto: c.clave_producto,
    clave_unidad: c.clave_unidad,
    descripcion: c.descripcion || 'Concepto sin descripción',
    cantidad: Number(c.cantidad ?? 0),
    valor_unitario: Number(c.valor_unitario ?? 0),
    descuento: c.descuento != null ? Number(c.descuento) : undefined,
    iva_tasa: c.iva_tasa != null ? Number(c.iva_tasa) : undefined,
    ret_iva_tasa: c.ret_iva_tasa != null ? Number(c.ret_iva_tasa) : undefined,
    ret_isr_tasa: c.ret_isr_tasa != null ? Number(c.ret_isr_tasa) : undefined,
  });

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      if (values.status_pago === 'PAGADA' && !values.fecha_cobro) {
        message.error('Para marcar PAGADA, captura la Fecha de cobro.');
        setSaving(false);
        return;
      }
      const POR_DEFINIR = '99';
      if (values.metodo_pago === 'PUE' && values.forma_pago === POR_DEFINIR) {
        message.error('Con método PUE la forma de pago no puede ser "Por definir (99)".');
        setSaving(false);
        return;
      }
      if (values.metodo_pago === 'PPD' && values.forma_pago !== POR_DEFINIR) {
        message.error('Con método PPD la forma de pago debe ser "Por definir (99)".');
        setSaving(false);
        return;
      }

      const payload = {
        ...values,
        cliente_id: values.cliente_id,
        uso_cfdi: values.uso_cfdi || null,
        fecha_emision: values.fecha_emision ? (values.fecha_emision as Dayjs).toISOString() : null,
        fecha_timbrado: values.fecha_timbrado ? (values.fecha_timbrado as Dayjs).toISOString() : null,
        fecha_pago: values.fecha_pago ? (values.fecha_pago as Dayjs).toISOString() : null,
        fecha_cobro: values.fecha_cobro ? (values.fecha_cobro as Dayjs).toISOString() : null,
        tipo_cambio:
          values.moneda === 'USD'
            ? values.tipo_cambio !== undefined && values.tipo_cambio !== null
              ? Number(values.tipo_cambio)
              : undefined
            : null,
        cfdi_relacionados_tipo: values.tiene_relacion ? values.cfdi_relacionados_tipo : null,
        cfdi_relacionados: values.tiene_relacion ? values.cfdi_relacionados : null,
        observaciones: values.observaciones || null,
        folio_fiscal: values.folio_fiscal || null,
        retencion_local_desc: values.retencion_local_desc || null,
        retencion_local_tasa:
          values.retencion_local_tasa != null ? Number(values.retencion_local_tasa) : null,
        conceptos: conceptosHook.conceptos.map(normalizeConcepto),
      };

      if (id) {
        await svc.updateFactura(id, payload);
        message.success('Factura actualizada');
        fetchInitialData();
      } else {
        const payload2: any = { ...payload };
        delete payload2.folio;
        const nuevaFactura = await svc.createFactura(payload2);
        message.success('Factura creada');
        router.push(`/facturas/form/${nuevaFactura.id}`);
      }
    } catch (err: any) {
      applyFormErrors(err, form);
      if (!err?._handled) message.error(normalizeHttpError(err));
    } finally {
      setSaving(false);
    }
  };

  // ── Return ────────────────────────────────────────────────────────────────────
  return {
    // state
    id, loading, saving, metadata, estatusCFDI, statusPago, rfcEmisor,
    fechaSolicitudCancelacion,

    // forms
    form, conceptoForm, psForm, cancelForm,

    // catalogs (from useFacturaCatalogos)
    empresas: catalogos.empresas,
    regimenes: catalogos.regimenes,
    metodosPago: catalogos.metodosPago,
    formaPagoOptions,
    usosCfdi: catalogos.usosCfdi,
    tiposRelacion: catalogos.tiposRelacion,
    motivosCancel: catalogos.motivosCancel,

    // empresa/cliente
    clienteOpts, currentEmpresa,

    // watchers / flags
    empresaId, moneda, isFormDisabled, fieldDisabled, fieldAlwaysEditable,
    puedeTimbrar, puedeCancelar, puedeVerificarSat, puedeRevertir,

    // conceptos (from useFacturaConceptos)
    ...conceptosHook,

    // calculated
    retencionLocalMonto,

    // handlers
    onFinish, onEmpresaChange, buscarClientes, onClienteChange, onFechaEmisionChange,

    // CFDI actions (from useFacturaAccionesCFDI)
    accionLoading: acciones.accionLoading,
    cancelSubmitting: acciones.cancelSubmitting,
    cancelModalOpen: acciones.cancelModalOpen,
    setCancelModalOpen: acciones.setCancelModalOpen,
    previewModalOpen: acciones.previewModalOpen,
    previewPdfUrl: acciones.previewPdfUrl,
    timbrarFactura: acciones.timbrarFactura,
    abrirModalCancelacion: acciones.abrirModalCancelacion,
    submitCancel: acciones.submitCancel,
    verPDF: acciones.verPDF,
    cerrarPreview: acciones.cerrarPreview,
    descargarPDF: acciones.descargarPDF,
    descargarXML: acciones.descargarXML,
    handleVerificarSAT: acciones.handleVerificarSAT,
    handleRevertirCancelacion: acciones.handleRevertirCancelacion,
  };
};
