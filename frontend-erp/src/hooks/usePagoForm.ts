// src/hooks/usePagoForm.ts
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { Form, message } from 'antd';
import dayjs from 'dayjs';
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
  const [clientes, setClientes] = useState<{ label: string; value: string }[]>([]);
  const [formasPago, setFormasPago] = useState<{ label: string; value: string }[]>([]);

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

        setEmpresas(
          (empresasData || []).map((e: any) => ({
            value: e.id,
            label: e.nombre_comercial ?? e.nombre,
          })),
        );

        setFormasPago(
          (formasPagoData || []).map((fp: any) => ({
            value: fp.clave,
            label: `${fp.clave} - ${fp.descripcion}`,
          })),
        );

        if (id) {
          const pagoData = await pagoService.getPagoById(id);
          setPago(pagoData);

          form.setFieldsValue({
            ...pagoData,
            fecha_pago: pagoData?.fecha_pago ? dayjs(pagoData.fecha_pago) : null,
          });

          if (pagoData.cliente_id) {
            const clienteData = await facturaService.getClienteById(pagoData.cliente_id);
            setClientes([
              {
                label:
                  clienteData.nombre_comercial ||
                  clienteData.razon_social ||
                  clienteData.nombre ||
                  'Cliente',
                value: clienteData.id,
              },
            ]);
          }
          
          // Cargar asignaciones existentes del pago
          const allocation: Record<string, number | null> = {};
          (pagoData.documentos_relacionados || []).forEach((doc: any) => {
            if (doc?.factura_id != null) {
              allocation[doc.factura_id] = Number(doc.imp_pagado ?? 0);
            }
          });
          setPaymentAllocation(allocation);

        } else {
          // Valores por defecto para un nuevo pago
          form.setFieldsValue({
            fecha_pago: dayjs(),
            forma_pago_p: '3', // 3 = Transferencia electrónica de fondos
            moneda_p: 'MXN',
          });
          setClientes([]);
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
          const nextFolio = await pagoService.getSiguienteFolioPago(empresaId, '');
          form.setFieldsValue({ folio: nextFolio.toString() });
        } catch (error) {
          message.error(normalizeHttpError(error) || 'Error al obtener el siguiente folio.');
        }
      };
      fetchFolio();
    }
  }, [id, empresaId, form]);

  // Cambio de empresa -> carga clientes
  useEffect(() => {
    if (!empresaId) {
      setClientes([]);
      form.setFieldsValue({ cliente_id: null });
      return;
    }
    facturaService
      .getClientesByEmpresa(empresaId)
      .then((data) =>
        setClientes(
          (data || []).map((c: any) => ({
            value: c.id,
            label: c.nombre_comercial ?? c.razon_social ?? c.nombre ?? 'Cliente',
          })),
        ),
      )
  .catch((e) => message.error(normalizeHttpError(e) || 'Error al cargar clientes.'));
  }, [empresaId, form]);

  // Efecto para manejar la lógica de facturas pendientes y asignaciones cuando cambia el cliente
  useEffect(() => {
    if (!clienteId) {
      setFacturasPendientes([]);
      setPaymentAllocation({});
      return;
    }

    const isEditing = !!id;

    pagoService
      .getFacturasPendientes(clienteId)
      .then((pendingInvoicesData) => {
        let finalFacturas = pendingInvoicesData || [];
        
        // Si estamos editando y el cliente no ha cambiado, unimos las facturas del pago con las pendientes
        if (isEditing && pago && pago.cliente_id === clienteId) {
          const facturasDelPago = (pago.documentos_relacionados || [])
            .map((doc: any) => doc.factura)
            .filter(Boolean);

          const map = new Map<string, any>();
          [...facturasDelPago, ...finalFacturas].forEach((f: any) => {
            if (f?.id) map.set(f.id, f);
          });
          finalFacturas = Array.from(map.values());
        }
        
        setFacturasPendientes(finalFacturas);

        // Limpiamos las asignaciones solo si es un pago nuevo o si el usuario cambió manualmente el cliente
        if (!isEditing || (pago && clienteId !== pago.cliente_id)) {
          setPaymentAllocation({});
        }
      })
  .catch((e) => message.error(normalizeHttpError(e) || 'Error al cargar facturas pendientes.'));
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

  const cancelarComplemento = async () => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, cancelando: true }));
    try {
      // Implementar cuando tu backend lo soporte
      message.info('Funcionalidad de cancelación no implementada.');
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al cancelar el pago.');
    } finally {
      setAccionLoading((s) => ({ ...s, cancelando: false }));
    }
  };

  const enviarComplemento = async () => {
    message.info('Funcionalidad de envío no implementada.');
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

  const verPdf = async () => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, visualizando: true }));
    try {
      const blob = await pagoService.getPagoPdf(id); // <— nombre correcto
      openBlobInNewTab(blob);
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al generar el PDF.');
    } finally {
      setAccionLoading((s) => ({ ...s, visualizando: false }));
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
    clientes,
    formasPago,
    facturasPendientes,
    paymentAllocation,
    handleAllocationChange,
    onFinish,
    generarComplemento,
    enviarComplemento,
    cancelarComplemento,
    verPdf,
    descargarPdf,
    descargarXml,
  };
};