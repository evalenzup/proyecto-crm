// src/hooks/usePagoForm.ts
import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/router';
import { Form, message } from 'antd';
import dayjs from 'dayjs';
import debounce from 'lodash/debounce';
import * as pagoService from '@/services/pagoService';
import * as facturaService from '@/services/facturaService';
import type { Pago } from '@/services/pagoService';
import { normalizeHttpError } from '@/utils/httpError';
import { applyFormErrors } from '@/utils/formErrors';

export const usePagoForm = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const [form] = Form.useForm();
  const [pago, setPago] = useState<Pago | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [accionLoading, setAccionLoading] = useState({
    timbrando: false,
    enviando: false,
    cancelando: false,
    visualizando: false,
    descargando: false,
  });

  // Data para selects
  const [empresas, setEmpresas] = useState<{ label: string; value: string }[]>([]);
  const [clientesComercial, setClientesComercial] = useState<{ label: string; value: string }[]>([]); // New
  const [clientesFiscal, setClientesFiscal] = useState<{ label: string; value: string }[]>([]); // New
  const [formasPago, setFormasPago] = useState<{ label: string; value: string }[]>([]);
  const [clienteEmail, setClienteEmail] = useState<string>('');
  const [currentEmpresa, setCurrentEmpresa] = useState<any | null>(null);

  // Datos principales
  const [facturasPendientes, setFacturasPendientes] = useState<pagoService.FacturaPendiente[]>([]);
  const [paymentAllocation, setPaymentAllocation] = useState<Record<string, number | null>>({});

  const handleAllocationChange = (facturaId: string, amount: number | null) => {
    setPaymentAllocation((prev) => ({ ...prev, [facturaId]: amount }));
  };

  const empresaId = Form.useWatch('empresa_id', form);
  const clienteId = Form.useWatch('cliente_id', form);

  // Carga inicial de datos estáticos y del pago existente
  useEffect(() => {
    const fetchInitialData = async () => {
      setLoading(true);
      try {
        const [empresasData, formasPagoData] = await Promise.all([
          facturaService.getEmpresas(),
          facturaService.getFormasPago(),
        ]);

        const empOptions = (empresasData || []).map((e: any) => ({
          value: e.id,
          label: e.nombre_comercial ?? e.nombre,
        }));
        setEmpresas(empOptions);

        // Auto-selección si solo hay una empresa y es nuevo
        if (!id && empOptions.length === 1) {
          form.setFieldValue('empresa_id', empOptions[0].value);
        }

        setFormasPago(
          (formasPagoData || []).map((fp: any) => ({
            value: fp.clave,
            label: `${fp.clave} - ${fp.descripcion}`,
          })),
        );

        if (id) {
          const pagoData = await pagoService.getPagoById(id);
          setPago(pagoData);

          // Setear campos del formulario
          // Normalizar forma_pago_p (padding si es necesario)
          let fp = pagoData.forma_pago_p;
          if (fp && typeof fp === 'string' && fp.length === 1) {
            fp = `0${fp}`;
          }

          form.setFieldsValue({
            ...pagoData,
            forma_pago_p: fp,
            fecha_pago: pagoData?.fecha_pago ? dayjs(pagoData.fecha_pago) : null,
          });

          if (pagoData.cliente_id) {
            // Siempre traer datos frescos del cliente para tener el email
            try {
              const clienteData = await facturaService.getClienteById(pagoData.cliente_id);
              const labelCom = `${clienteData.nombre_comercial} (${clienteData.nombre_razon_social})`;
              const labelFis = `${clienteData.nombre_razon_social} (${clienteData.nombre_comercial})`;
              const email = clienteData.email || '';

              setClientesComercial([{ label: labelCom, value: clienteData.id }]);
              setClientesFiscal([{ label: labelFis, value: clienteData.id }]);
              // Setear email en el form (oculto) y en estado
              form.setFieldValue(['cliente', 'email'], email);
              setClienteEmail(email);
            } catch (e) {
              console.error("Error fetching client details", e);
            }
          }

          // Cargar asignaciones existentes del pago
          const allocation: Record<string, number | null> = {};
          (pagoData.documentos_relacionados || []).forEach((doc: any) => {
            if (doc?.factura_id != null) {
              allocation[doc.factura_id] = Number(doc.imp_pagado ?? 0);
            }
          });
          setPaymentAllocation(allocation);

          // Mostrar inmediatamente las facturas del pago (sin esperar pendientes)
          const facturasDelPago = (pagoData.documentos_relacionados || [])
            .map((d: any) => d?.factura)
            .filter(Boolean);
          const map = new Map<string, any>();
          facturasDelPago.forEach((f: any) => { if (f?.id) map.set(f.id, f); });
          setFacturasPendientes(Array.from(map.values()));

        } else {
          // Valores por defecto para un nuevo pago
          form.setFieldsValue({
            fecha_pago: dayjs(),
            forma_pago_p: '03', // 03 = Transferencia electrónica de fondos
            moneda_p: 'MXN',
          });
          setClientesComercial([]);
          setClientesFiscal([]);
        }
      } catch (error) {
        message.error(normalizeHttpError(error) || 'Error al cargar datos iniciales.');
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
  }, [id, form]);

  // Generar folio si es nuevo pago y empresa seleccionada
  useEffect(() => {
    if (!id && empresaId) {
      const fetchFolio = async () => {
        try {
          // Default series is 'P' in backend, so we must ask for 'P' to get the correct consecutive
          const nextFolio = await pagoService.getSiguienteFolioPago(empresaId, 'P');
          form.setFieldsValue({ folio: nextFolio.toString() });
        } catch (error) {
          message.error(normalizeHttpError(error) || 'Error al obtener el siguiente folio.');
        }
      };
      fetchFolio();
    }
  }, [id, empresaId, form]);

  // Cambio de empresa -> para edición no limpiamos; para nuevo pago sí
  useEffect(() => {
    if (!empresaId) {
      setClientesComercial([]);
      setClientesFiscal([]);
      form.setFieldsValue({ cliente_id: null });
      return;
    }
    // Si estamos editando, no tocar el cliente
    if (id) return;
    setClientesComercial([]);
    setClientesFiscal([]);
    form.setFieldsValue({ cliente_id: null });
  }, [empresaId, form, id]);

  // Cargar datos de la empresa actual cuando cambia
  useEffect(() => {
    if (empresaId) {
      facturaService.getEmpresaById(empresaId)
        .then(data => setCurrentEmpresa(data))
        .catch(e => console.error("Error loading company", e));
    } else {
      setCurrentEmpresa(null);
    }
  }, [empresaId]);

  // Búsqueda de clientes por nombre comercial
  const buscarClientesComercial = useMemo(() =>
    debounce(async (q: string) => {
      const empId = form.getFieldValue('empresa_id');
      if (!empId) return;
      if (!q || q.trim().length < 3) {
        setClientesComercial([]);
        return;
      }
      try {
        const data = await facturaService.searchClientes(q, empId, 'comercial');
        const arr = Array.isArray(data) ? data : (data?.items || []);
        // Si el usuario busca por nombre comercial, le mostramos "Comercial (Fiscal)" para confirmar
        setClientesComercial(arr.map((c: any) => ({
          value: c.id,
          label: `${c.nombre_comercial} (${c.nombre_razon_social})`,
        })));
      } catch (e) {
        setClientesComercial([]);
      }
    }, 350)
    , [form]);

  // Búsqueda de clientes por nombre fiscal
  const buscarClientesFiscal = useMemo(() =>
    debounce(async (q: string) => {
      const empId = form.getFieldValue('empresa_id');
      if (!empId) return;
      if (!q || q.trim().length < 3) {
        setClientesFiscal([]);
        return;
      }
      try {
        const data = await facturaService.searchClientes(q, empId, 'fiscal');
        const arr = Array.isArray(data) ? data : (data?.items || []);
        // Si busca por fiscal, mostramos "Fiscal (Comercial)" o similar, 
        // pero para consistencia visual, mantengamos "Comercial (Fiscal)" o invirtamos según convenga.
        // El usuario pidió inputs separados, así que en el input "Fiscal", tendría sentido ver primero la razón social.
        setClientesFiscal(arr.map((c: any) => ({
          value: c.id,
          label: `${c.nombre_razon_social} (${c.nombre_comercial})`,
        })));
      } catch (e) {
        setClientesFiscal([]);
      }
    }, 350)
    , [form]);

  // Efecto para manejar la lógica de facturas cuando cambia el cliente
  useEffect(() => {
    const isEditing = !!id;

    // Si no hay cliente seleccionado
    if (!clienteId) {
      // En edición, mantenemos asignaciones; en nuevo, limpiamos
      if (!isEditing) setPaymentAllocation({});
      setFacturasPendientes([]);
      return;
    }

    // Si estamos editando y el cliente es el mismo del pago: mostrar sólo las facturas del pago
    if (isEditing && pago && clienteId === pago.cliente_id) {
      const facturasDelPago = (pago.documentos_relacionados || [])
        .map((doc: any) => doc.factura)
        .filter(Boolean);
      const map = new Map<string, any>();
      facturasDelPago.forEach((f: any) => { if (f?.id) map.set(f.id, f); });
      setFacturasPendientes(Array.from(map.values()));
      return;
    }

    // Caso nuevo pago o el usuario cambió el cliente: consultar facturas pendientes
    pagoService
      .getFacturasPendientes(clienteId, empresaId)
      .then((pendingInvoicesData) => {
        const finalFacturas = pendingInvoicesData || [];
        setFacturasPendientes(finalFacturas);
        // Si el usuario cambió el cliente (o es nuevo), limpiar asignaciones
        setPaymentAllocation({});
      })
      .catch((e) => message.error(normalizeHttpError(e) || 'Error al cargar facturas pendientes.'));

    // Fetch cliente details to get email for current user
    if (clienteId) {
      facturaService.getClienteById(clienteId).then(c => {
        if (c) {
          const email = c.email || '';
          setClienteEmail(email);
          form.setFieldValue(['cliente', 'email'], email);

          const labelCom = `${c.nombre_comercial} (${c.nombre_razon_social})`;
          const labelFis = `${c.nombre_razon_social} (${c.nombre_comercial})`;
          setClientesComercial([{ label: labelCom, value: c.id }]);
          setClientesFiscal([{ label: labelFis, value: c.id }]);
        }
      }).catch(() => { });
    } else {
      setClienteEmail('');
      setClientesComercial([]);
      setClientesFiscal([]);
    }
  }, [clienteId, id, pago]);

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      // Construir documentos que tengan monto > 0
      const documentos = Object.entries(paymentAllocation)
        .filter(([_, amount]) => amount != null && Number(amount) > 0)
        .map(([facturaId, amount]) => {
          const f = facturasPendientes.find((x) => x.id === facturaId);
          if (!f) return null;
          const imp_pagado = Number(amount || 0);
          const saldoAnt = Number(f.total || 0); // Ajusta si tu API devuelve otro campo
          return {
            factura_id: f.id,
            imp_pagado,
            num_parcialidad: 1, // Ajusta si tu backend requiere otro valor
            imp_saldo_ant: saldoAnt,
            imp_saldo_insoluto: Math.max(saldoAnt - imp_pagado, 0),
          };
        })
        .filter((x): x is NonNullable<typeof x> => Boolean(x));

      if (documentos.length === 0) {
        message.error('Debe asignar un monto a pagar a al menos una factura.');
        setSaving(false);
        return;
      }

      const totalAplicado = documentos.reduce((sum, d) => sum + Number(d.imp_pagado || 0), 0);
      const monto = Number(values.monto || 0);

      if (Math.abs(totalAplicado - monto) > 0.01) {
        message.error(
          `El monto total (${monto.toFixed(2)}) no coincide con el total aplicado (${totalAplicado.toFixed(2)}).`,
        );
        setSaving(false);
        return;
      }

      const payload = {
        ...values,
        fecha_pago: values?.fecha_pago ? dayjs(values.fecha_pago).toISOString() : null,
        documentos,
      };

      const nuevo = id
        ? await pagoService.updatePago(id, payload)
        : await pagoService.createPago(payload);

      message.success(`Pago ${id ? 'actualizado' : 'creado'} con éxito.`);
      if (!id) {
        router.push(`/pagos/form/${nuevo.id}`);
      } else {
        setPago(nuevo);
      }
    } catch (err: any) {
      applyFormErrors(err, form);
      message.error(normalizeHttpError(err) || 'Error al guardar el pago.');
    } finally {
      setSaving(false);
    }
  };

  const generarComplemento = async () => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, timbrando: true }));
    try {
      const result = await pagoService.timbrarPago(id);
      const updated = await pagoService.getPagoById(id);
      setPago(updated);
      message.success(result?.message || 'Pago timbrado con éxito.');
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al timbrar el pago.');
    } finally {
      setAccionLoading((s) => ({ ...s, timbrando: false }));
    }
  };

  // Cancelación
  const [cancelacionModalOpen, setCancelacionModalOpen] = useState(false);

  const abrirCancelacion = () => {
    setCancelacionModalOpen(true);
  };

  const cerrarCancelacion = () => {
    setCancelacionModalOpen(false);
  };

  const confirmarCancelacion = async (motivo: string, folioSustituto?: string) => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, cancelando: true }));
    try {
      await pagoService.cancelarPagoSat(id, motivo, folioSustituto);
      message.success('Solicitud de cancelación enviada correctamente.');
      // Recargar datos
      const updated = await pagoService.getPagoById(id);
      setPago(updated);
      cerrarCancelacion();
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al cancelar el pago.');
    } finally {
      setAccionLoading((s) => ({ ...s, cancelando: false }));
    }
  };

  // Envío por correo
  const [emailModalOpen, setEmailModalOpen] = useState(false);

  const abrirEmailModal = () => {
    setEmailModalOpen(true);
  };

  const cerrarEmailModal = () => {
    setEmailModalOpen(false);
  };

  const confirmarEnvioCorreo = async (recipients: string[], subject: string, body: string) => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, enviando: true }));
    try {
      await pagoService.enviarPagoEmail(id, recipients, subject, body);
      message.success('Correo enviado correctamente.');
      cerrarEmailModal();
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al enviar el correo.');
    } finally {
      setAccionLoading((s) => ({ ...s, enviando: false }));
    }
  };

  const enviarComplemento = async () => {
    abrirEmailModal();
  };

  // Helpers descarga/visualización
  const openBlobInNewTab = (blob: Blob) => {
    const url = window.URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };

  const forceDownload = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };

  // Modal preview
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);

  const verPdf = async () => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, visualizando: true }));
    try {
      const blob = await pagoService.getPagoPdf(id);
      const url = window.URL.createObjectURL(blob);
      setPreviewPdfUrl(url);
      setPreviewModalOpen(true);
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al generar el PDF.');
    } finally {
      setAccionLoading((s) => ({ ...s, visualizando: false }));
    }
  };

  const cerrarPreview = () => {
    setPreviewModalOpen(false);
    if (previewPdfUrl) {
      URL.revokeObjectURL(previewPdfUrl);
      setPreviewPdfUrl(null);
    }
  };

  const descargarPdf = async () => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, descargando: true }));
    try {
      const blob = await pagoService.getPagoPdf(id); // <— nombre correcto
      forceDownload(blob, `pago-${pago?.folio || id}.pdf`);
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al descargar el PDF.');
    } finally {
      setAccionLoading((s) => ({ ...s, descargando: false }));
    }
  };

  const descargarXml = async () => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, descargando: true }));
    try {
      const blob = await pagoService.downloadPagoXml(id);
      forceDownload(blob, `pago-${pago?.folio || id}.xml`);
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al descargar el XML.');
    } finally {
      setAccionLoading((s) => ({ ...s, descargando: false }));
    }
  };

  return {
    id,
    form,
    pago,
    loading,
    saving,
    accionLoading,
    empresas,
    clientesComercial,
    clientesFiscal,
    buscarClientesComercial,
    buscarClientesFiscal,
    formasPago,
    facturasPendientes,
    paymentAllocation,
    handleAllocationChange,
    onFinish,
    generarComplemento,
    enviarComplemento,
    // Cancelación
    cancelacionModalOpen,
    abrirCancelacion,
    cerrarCancelacion,
    confirmarCancelacion,
    verPdf,
    descargarPdf,
    descargarXml,
    previewModalOpen,
    previewPdfUrl,
    cerrarPreview,
    // Email
    emailModalOpen,
    abrirEmailModal,
    cerrarEmailModal,
    confirmarEnvioCorreo,
    clienteEmail,
    currentEmpresa,
  };
};