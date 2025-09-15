//frontend-erp/src/hooks/useFacturaForm.ts

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/router';
import { Form, message } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import debounce from 'lodash/debounce';
import * as svc from '@/services/facturaService';

type EstatusCFDI = 'BORRADOR' | 'TIMBRADA' | 'CANCELADA';
type StatusPago = 'PAGADA' | 'NO_PAGADA';

interface ConceptoForm {
  ps_lookup?: any;
  clave_producto?: string;
  clave_unidad?: string;
  descripcion?: string;
  cantidad?: number;
  valor_unitario?: number;
  descuento?: number | null;
  iva_tasa?: number | null;
  ret_iva_tasa?: number | null;
  ret_isr_tasa?: number | null;
}

export const useFacturaForm = () => {
  const router = useRouter();
  const raw = router.query.id;
  const id = Array.isArray(raw) ? raw[0] : (raw as string | undefined);

  // forms
  const [form] = Form.useForm();
  const [conceptoForm] = Form.useForm();
  const [psForm] = Form.useForm();
  const [cancelForm] = Form.useForm();

  // estado UI
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [accionLoading, setAccionLoading] = useState({ timbrar: false, cancelar: false });
  const [cancelSubmitting, setCancelSubmitting] = useState(false);

  // modal cancelación
  const [cancelModalOpen, setCancelModalOpen] = useState(false);

  // encabezados / metadatos
  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);
  const [estatusCFDI, setEstatusCFDI] = useState<EstatusCFDI>('BORRADOR');
  const [statusPago, setStatusPago] = useState<StatusPago>('NO_PAGADA');
  const [rfcEmisor, setRfcEmisor] = useState<string>('');

  // catálogos
  const [empresas, setEmpresas] = useState<{ label: string; value: string }[]>([]);
  const [regimenes, setRegimenes] = useState<{ value: string; label: string }[]>([]);
  const [metodosPago, setMetodosPago] = useState<{ value: string; label: string }[]>([]);
  const [formasPago, setFormasPago] = useState<{ value: string; label: string }[]>([]);
  const [usosCfdi, setUsosCfdi] = useState<{ value: string; label: string }[]>([]);
  const [tiposRelacion, setTiposRelacion] = useState<{ value: string; label: string }[]>([]);
  const [motivosCancel, setMotivosCancel] = useState<{ value: string; label: string }[]>([]);

  // clientes / productos
  const [clienteOpts, setClienteOpts] = useState<{ label: string; value: string }[]>([]);
  const [diasCreditoCliente, setDiasCreditoCliente] = useState<number>(0);
  const [psOpts, setPsOpts] = useState<{ value: string; label: string; meta: any }[]>([]);
  const [unidadOpts, setUnidadOpts] = useState<{ value: string; label: string }[]>([]);
  const [claveSatOpts, setClaveSatOpts] = useState<{ value: string; label: string }[]>([]);

  // conceptos
  const [conceptos, setConceptos] = useState<ConceptoForm[]>([]);
  const [isConceptoModalOpen, setIsConceptoModalOpen] = useState(false);
  const [editingConcepto, setEditingConcepto] = useState<ConceptoForm | null>(null);
  const [editingConceptoIndex, setEditingConceptoIndex] = useState<number | null>(null);

  // PS modal
  const [psModalOpen, setPsModalOpen] = useState(false);
  const [psSaving, setPsSaving] = useState(false);

  // watchers
  const empresaId = Form.useWatch('empresa_id', form);
  const moneda = Form.useWatch('moneda', form);
  const metodoPago = Form.useWatch('metodo_pago', form);
  const formaPago = Form.useWatch('forma_pago', form);

  // helpers bloqueo
  const isFormDisabled = estatusCFDI === 'TIMBRADA' || estatusCFDI === 'CANCELADA';
  const fieldDisabled = (defaultDisabled: boolean) => (isFormDisabled ? true : defaultDisabled);
  const fieldAlwaysEditable = (name: string) =>
    ['status_pago', 'fecha_cobro', 'observaciones'].includes(name) ? false : isFormDisabled;

  const puedeTimbrar = Boolean(id) && estatusCFDI === 'BORRADOR';
  const puedeCancelar = Boolean(id) && estatusCFDI === 'TIMBRADA';

  // -------- Carga inicial (catálogos + empresas + (opcional) factura) --------
  const fetchInitialData = useCallback(async () => {
    try {
      const [
        empresasData,
        mpData,
        fpData,
        ucData,
        rfData,
        trData,
        mcData,
      ] = await Promise.all([
        svc.getEmpresas(),
        svc.getMetodosPago(),
        svc.getFormasPago(),
        svc.getUsosCfdi(),
        svc.getRegimenesFiscales(),
        svc.getTiposRelacion(),
        svc.getMotivosCancelacion(),
      ]);

      setEmpresas((empresasData || []).map((e: any) => ({
        value: e.id,
        label: e.nombre_comercial ?? e.nombre,
      })));
      setMetodosPago((mpData || []).map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
      setFormasPago((fpData || []).map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
      setUsosCfdi((ucData || []).map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
      setRegimenes((rfData || []).map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
      setTiposRelacion((trData || []).map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
      setMotivosCancel((mcData || []).map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));

      if (id) {
        const data = await svc.getFacturaById(id);

        setEstatusCFDI(data.estatus);
        setStatusPago(data.status_pago);

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
        setConceptos(conceptosCargados);

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
          fecha_emision: data.fecha_emision ? dayjs(data.fecha_emision) : dayjs(),
          fecha_timbrado: data.fecha_timbrado ? dayjs(data.fecha_timbrado) : null,
          fecha_pago: data.fecha_pago ? dayjs(data.fecha_pago) : null,
          fecha_cobro: data.fecha_cobro ? dayjs(data.fecha_cobro) : null,
          observaciones: data.observaciones ?? undefined,
        });

        setMetadata({ creado_en: data.creado_en, actualizado_en: data.actualizado_en });
      } else {
        // nuevo
        setConceptos([]);
        setEstatusCFDI('BORRADOR');
        setStatusPago('NO_PAGADA');
        form.setFieldsValue({
          moneda: 'MXN',
          tiene_relacion: false,
          fecha_emision: dayjs(),
          status_pago: 'NO_PAGADA',
        });
      }
    } catch (e) {
      console.error(e);
      message.error('Error al cargar catálogos/empresas');
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  // -------- Empresa / Cliente --------
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
      return;
    }

    const data = await svc.getEmpresaById(empId);
    form.setFieldsValue({
      nombre_fiscal_emisor: data.nombre ?? data.nombre_comercial,
      regimen_fiscal_emisor: data.regimen_fiscal,
      lugar_expedicion: data.codigo_postal,
    });
    setRfcEmisor((data?.rfc || '').toUpperCase());

    // sugerir folio siguiente
    try {
      const res = await (await import('@/lib/axios')).default.get('/facturas/', {
        params: { empresa_id: empId, limit: 1, offset: 0, order_by: 'serie_folio', order_dir: 'desc' },
      });
      const last = res?.data?.items?.[0];
      const nextFolio = last?.folio ? Number(last.folio) + 1 : 1;
      form.setFieldValue('folio', nextFolio);
    } catch {
      form.setFieldValue('folio', 1);
    }
  }, [form]);

  const buscarClientes = useMemo(
    () =>
      debounce(async (q: string) => {
        const empId = form.getFieldValue('empresa_id');
        if (!empId) return;
        if (!q || q.trim().length < 3) {
          setClienteOpts([]);
          return;
        }
        try {
          const data = await svc.searchClientes(q);
          setClienteOpts(
            (data || []).map((c: any) => ({
              value: c.id,
              label: c.nombre_comercial ?? c.razon_social ?? c.nombre ?? 'Cliente',
            })),
          );
        } catch {
          setClienteOpts([]);
        }
      }, 350),
    [form],
  );

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
    });
    const dias = Number(data.dias_credito ?? 0);
    setDiasCreditoCliente(dias);

    const fe = form.getFieldValue('fecha_emision') as Dayjs | undefined;
    if (fe && dayjs.isDayjs(fe)) {
      form.setFieldValue('fecha_pago', fe.add(dias, 'day'));
    }
  }, [form]);

  const onFechaEmisionChange = (d: Dayjs | null) => {
    if (!d) {
      form.setFieldsValue({ fecha_pago: null, fecha_cobro: null });
      return;
    }
    const dias = diasCreditoCliente || 0;
    form.setFieldsValue({
      fecha_pago: d.add(dias, 'day'),
      ...(form.getFieldValue('status_pago') === 'PAGADA' ? { fecha_cobro: d.add(dias, 'day') } : {}),
    });
  };

  // -------- Formas de pago dependientes (PUE/PPD) --------
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

  const formaPagoOptions = useMemo(() => {
    const POR_DEFINIR = '99';
    if (!metodoPago) return formasPago;
    if (metodoPago === 'PUE') return (formasPago || []).filter((f) => f.value !== POR_DEFINIR);
    if (metodoPago === 'PPD') return (formasPago || []).filter((f) => f.value === POR_DEFINIR);
    return formasPago;
  }, [formasPago, metodoPago]);

  // -------- Conceptos (modal) --------
  const sugerirRetencionesSiAplica = async () => {
    try {
      const reg = form.getFieldValue('regimen_fiscal_emisor') as string | undefined;
      if (!reg) return;

      let receptorMoral = false;
      const cid = form.getFieldValue('cliente_id');
      if (cid) {
        const data = await svc.getClienteById(cid);
        receptorMoral = (data?.tipo_persona ?? '').toUpperCase() === 'MORAL';
      }

      const esRIFoRESICO =
        /Régimen Simplificado de Confianza/i.test(reg) ||
        /Incorporación Fiscal/i.test(reg) ||
        /RESICO/i.test(reg) ||
        /RIF/i.test(reg);

      if (esRIFoRESICO && receptorMoral) {
        if (conceptoForm.getFieldValue('ret_iva_tasa') == null) conceptoForm.setFieldValue('ret_iva_tasa', 0.106667);
        if (conceptoForm.getFieldValue('ret_isr_tasa') == null) conceptoForm.setFieldValue('ret_isr_tasa', 0.0125);
        message.info('Sugeridas retenciones para RESICO/RIF a persona moral (ajústalas si es necesario).');
      }
    } catch { /* no-op */ }
  };

  const onSelectPSInModal = (_: any, option: any) => {
    const meta = option?.meta || {};
    conceptoForm.setFieldsValue({
      clave_producto: meta.clave_producto,
      clave_unidad: meta.clave_unidad,
      descripcion: meta.descripcion,
      valor_unitario: meta.valor_unitario,
    });
    sugerirRetencionesSiAplica();
  };

  const handleSaveConcepto = async () => {
    const values = await conceptoForm.validateFields();
    const newConcepto: ConceptoForm = {
      ...values,
      cantidad: Number(values.cantidad ?? 0),
      valor_unitario: Number(values.valor_unitario ?? 0),
      descuento: values.descuento != null ? Number(values.descuento) : null,
      iva_tasa: values.iva_tasa != null ? Number(values.iva_tasa) : 0,
      ret_iva_tasa: values.ret_iva_tasa != null ? Number(values.ret_iva_tasa) : 0,
      ret_isr_tasa: values.ret_isr_tasa != null ? Number(values.ret_isr_tasa) : 0,
    };

    if (editingConceptoIndex !== null) {
      const newConceptos = [...conceptos];
      newConceptos[editingConceptoIndex] = newConcepto;
      setConceptos(newConceptos);
    } else {
      setConceptos([...conceptos, newConcepto]);
    }
    setIsConceptoModalOpen(false);
  };

  // buscar PS (existentes por empresa)
  const buscarPS = useMemo(
    () =>
      debounce(async (q: string) => {
        const empId = form.getFieldValue('empresa_id');
        if (!empId) return;
        if (!q || q.trim().length < 2) {
          setPsOpts([]);
          return;
        }
        try {
          const data = await svc.searchProductosServicios(empId, q);
          const opts = (data || []).map((it: any) => ({
            value: it.id,
            label: `${it.clave_producto} — ${it.descripcion}`,
            meta: {
              id: it.id,
              clave_producto: it.clave_producto,
              clave_unidad: it.clave_unidad,
              descripcion: it.descripcion,
              valor_unitario: Number(it.valor_unitario ?? 0),
            },
          }));
          setPsOpts(opts);
        } catch {
          setPsOpts([]);
        }
      }, 300),
    [form],
  );

  // SAT: claves producto / unidades (para alta PS)
  const buscarClavesProductoSAT = useMemo(
    () =>
      debounce(async (q: string) => {
        if (!q || q.trim().length < 3) {
          setClaveSatOpts([]);
          return;
        }
        try {
          const data = await svc.searchSatProductos(q);
          setClaveSatOpts((data || []).map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
        } catch {
          setClaveSatOpts([]);
        }
      }, 350),
    [],
  );

  const buscarUnidadesSAT = useMemo(
    () =>
      debounce(async (q: string) => {
        if (!q || q.trim().length < 2) {
          setUnidadOpts([]);
          return;
        }
        try {
          const data = await svc.searchSatUnidades(q);
          setUnidadOpts((data || []).map((u: any) => ({ value: u.clave, label: `${u.clave} — ${u.descripcion}` })));
        } catch {
          setUnidadOpts([]);
        }
      }, 250),
    [],
  );

  // -------- Totales (como en tu render actual: strings formateadas) --------
  const resumen = useMemo(() => {
    let subtotal = 0, traslados = 0, retenciones = 0;
    conceptos.forEach(c => {
      const cantidad = Number(c.cantidad || 0);
      const valor_unitario = Number(c.valor_unitario || 0);
      const descuento = Number(c.descuento || 0);
      const iva_tasa = Number(c.iva_tasa || 0);
      const ret_iva_tasa = Number(c.ret_iva_tasa || 0);
      const ret_isr_tasa = Number(c.ret_isr_tasa || 0);
      const base = Math.max(cantidad * valor_unitario - descuento, 0);
      const iva = base * iva_tasa;
      const ret_iva = base * ret_iva_tasa;
      const ret_isr = base * ret_isr_tasa;
      subtotal += base;
      traslados += iva;
      retenciones += ret_iva + ret_isr;
    });
    const total = subtotal + traslados - retenciones;
    const fmt = (n: number) => n.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
    return { subtotal: fmt(subtotal), traslados: fmt(traslados), retenciones: fmt(retenciones), total: fmt(total) };
  }, [conceptos]);

  // -------- Guardar --------
  const normalizeConcepto = (c: ConceptoForm) => ({
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
        conceptos: conceptos.map(normalizeConcepto),
      };

      if (id) {
        await svc.updateFactura(id, payload);
        message.success('Factura actualizada');
      } else {
        // server asigna folio
        const payload2: any = { ...payload };
        delete payload2.folio;
        await svc.createFactura(payload2);
        message.success('Factura creada');
      }
      router.push('/facturas');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (Array.isArray(detail)) {
        const mensajes = detail.map((e: any) => `${e?.loc?.join('.')}: ${e?.msg}`).join('\n');
        message.error(mensajes || 'Error de validación');
      } else if (typeof detail === 'string') {
        message.error(detail);
      } else {
        message.error('Error al guardar');
      }
    } finally {
      setSaving(false);
    }
  };

  // -------- Acciones CFDI / archivos --------
  const timbrarFactura = async () => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, timbrar: true }));
    try {
      const data = await svc.timbrarFactura(id);
      setEstatusCFDI(data.estatus);
      form.setFieldsValue({
        fecha_timbrado: data.fecha_timbrado ? dayjs(data.fecha_timbrado) : form.getFieldValue('fecha_timbrado'),
        folio_fiscal: data.folio_fiscal ?? form.getFieldValue('folio_fiscal'),
      });
      message.success('Factura timbrada');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'No se pudo timbrar');
    } finally {
      setAccionLoading((s) => ({ ...s, timbrar: false }));
    }
  };

  const abrirModalCancelacion = () => {
    cancelForm.resetFields();
    const defaultMotivo = motivosCancel?.[0]?.value || '02';
    cancelForm.setFieldsValue({ motivo: defaultMotivo, folio_sustitucion: undefined });
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
        const detail = e?.response?.data?.detail || e?.message;
        message.error(detail || 'No se pudo cancelar');
      }
    } finally {
      setCancelSubmitting(false);
    }
  };

  const openBlobInNewTab = (blob: Blob) => {
    const url = window.URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  };

  const verPDF = async () => {
    if (!id) {
      message.info('Guarda la factura para generar la vista previa.');
      return;
    }
    try {
      const blob =
        estatusCFDI === 'BORRADOR'
          ? await svc.getPdfPreview(id)
          : await svc.getPdf(id);
      openBlobInNewTab(blob);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      message.error(detail || 'No se pudo abrir el PDF');
    }
  };

  const descargarPDF = async () => {
    if (!id) return;
    try {
      const blob = await svc.downloadPdf(id);
      const url = window.URL.createObjectURL(blob);
      const rfc = (rfcEmisor || 'RFC').toUpperCase().replace(/\s+/g, '');
      const serie = (form.getFieldValue('serie') || 'S/N').toString().replace(/\s+/g, '');
      const folio = (form.getFieldValue('folio') || id).toString().replace(/\s+/g, '');
      const safe = (s: string) => s.replace(/[^a-zA-Z0-9._-]/g, '');
      const filename = `${safe(rfc)}-factura-${safe(serie)}-${safe(folio)}.pdf`;
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      message.error(detail || 'No se pudo descargar el PDF');
    }
  };

  const descargarXML = async () => {
    if (!id) return;
    try {
      const blob = await svc.downloadXml(id);
      const url = window.URL.createObjectURL(blob);
      const rfc = (rfcEmisor || 'RFC').toUpperCase().replace(/\s+/g, '');
      const serie = (form.getFieldValue('serie') || 'S/N').toString().replace(/\s+/g, '');
      const folio = (form.getFieldValue('folio') || id).toString().replace(/\s+/g, '');
      const safe = (s: string) => s.replace(/[^a-zA-Z0-9._-]/g, '');
      const filename = `${safe(rfc)}-factura-${safe(serie)}-${safe(folio)}.xml`;
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      message.error(detail || 'No se pudo descargar el XML');
    }
  };

  // -------- return --------
  return {
    // estado
    id, loading, saving, accionLoading, cancelSubmitting, metadata, estatusCFDI, statusPago, rfcEmisor,

    // forms
    form, conceptoForm, psForm, cancelForm,

    // catálogos / opciones
    empresas, regimenes, metodosPago, formaPagoOptions, usosCfdi, tiposRelacion, motivosCancel,
    clienteOpts, psOpts, unidadOpts, claveSatOpts,

    // watchers / flags
    empresaId, moneda, isFormDisabled, fieldDisabled, fieldAlwaysEditable, puedeTimbrar, puedeCancelar,

    // conceptos
    conceptos, setConceptos, isConceptoModalOpen, setIsConceptoModalOpen, editingConcepto,
    setEditingConcepto, setEditingConceptoIndex,

    // calculados
    resumen,

    // handlers (empresa/cliente/fechas)
    onFinish, onEmpresaChange, buscarClientes, onClienteChange, onFechaEmisionChange,

    // handlers (conceptos)
    buscarPS, onSelectPSInModal, handleSaveConcepto,

    // handlers (PS modal SAT)
    buscarClavesProductoSAT, buscarUnidadesSAT, psModalOpen, setPsModalOpen, psSaving,

    // modal cancelación
    cancelModalOpen, setCancelModalOpen, abrirModalCancelacion, submitCancel,

    // acciones (CFDI / archivos)
    timbrarFactura, verPDF, descargarPDF, descargarXML,
  };
};