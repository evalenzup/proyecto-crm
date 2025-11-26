import { useEffect, useState, useMemo } from 'react';
import { message, Form } from 'antd';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import debounce from 'lodash/debounce';
import { presupuestoService, PresupuestoCreate, PresupuestoUpdate } from '@/services/presupuestoService';
import { clienteService, ClienteCreate, ClienteOut } from '@/services/clienteService';
import { empresaService } from '@/services/empresaService';
import { productoServicioService, ProductoServicioOut } from '@/services/productoServicioService';
import { normalizeHttpError } from '@/utils/httpError';
import { applyFormErrors } from '@/utils/formErrors';
import { Presupuesto, PresupuestoDetalle } from '@/models/presupuesto';
import dayjs, { Dayjs } from 'dayjs';

export const usePresupuestoForm = (id?: string) => {
  const [form] = Form.useForm();
  const [conceptoForm] = Form.useForm();
  const [quickClienteForm] = Form.useForm();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // State for versioning
  const [selectedVersionId, setSelectedVersionId] = useState<string | undefined>(id);

  // State for quick create modal
  const [isClienteModalOpen, setIsClienteModalOpen] = useState(false);

  // State for conceptos
  const [conceptos, setConceptos] = useState<PresupuestoDetalle[]>([]);
  const [isConceptoModalOpen, setIsConceptoModalOpen] = useState(false);
  const [editingConcepto, setEditingConcepto] = useState<Partial<PresupuestoDetalle> | null>(null);
  const [editingConceptoIndex, setEditingConceptoIndex] = useState<number | null>(null);
  const [psOpts, setPsOpts] = useState<{ value: string; label: string; meta: ProductoServicioOut }[]>([]);

  // Watchers
  const empresaId = Form.useWatch('empresa_id', form);

  // Update selectedVersionId when URL id changes
  useEffect(() => {
    setSelectedVersionId(id);
  }, [id]);

  // Fetch data for select options
  const { data: empresas, isLoading: loadingEmpresas } = useQuery({
    queryKey: ['empresasForSelect'],
    queryFn: () => empresaService.getEmpresas({ limit: 500, offset: 0 }),
  });

  const [clientesOptions, setClientesOptions] = useState<{ label: string; value: string; }[]>([]);
  const buscarClientes = useMemo(
    () =>
      debounce(async (q: string) => {
        if (!empresaId || !q || q.trim().length < 3) {
          setClientesOptions([]);
          return;
        }
        try {
          const data = await clienteService.buscarClientes(q, empresaId);
          setClientesOptions(
            (data || []).map((c: ClienteOut) => ({
              value: c.id,
              label: c.nombre_comercial,
            })),
          );
        } catch {
          setClientesOptions([]);
        }
      }, 350),
    [empresaId],
  );

  const handleSaveQuickCliente = async () => {
    try {
      const values = await quickClienteForm.validateFields();
      const empId = form.getFieldValue('empresa_id');
      if (!empId) {
        message.error('Por favor, selecciona una empresa primero.');
        return;
      }

      const empresaSeleccionada = empresas?.find(e => e.id === empId);
      if (!empresaSeleccionada) {
        message.error('La empresa seleccionada no es válida.');
        return;
      }

      const payload: ClienteCreate = {
        nombre_comercial: values.nombre_comercial,
        nombre_razon_social: values.nombre_comercial,
        rfc: values.rfc || 'XAXX010101000',
        regimen_fiscal: 'Sin obligaciones fiscales',
        codigo_postal: empresaSeleccionada.codigo_postal,
        empresa_id: [empId],
        email: values.email ? [values.email] : undefined,
        telefono: values.telefono ? [values.telefono] : undefined,
      };

      const newCliente = await clienteService.createCliente(payload);
      message.success('Cliente creado con éxito');
      
      const newOption = { label: newCliente.nombre_comercial, value: newCliente.id };
      setClientesOptions(prev => [newOption, ...prev]);
      form.setFieldValue('cliente_id', newCliente.id);

      setIsClienteModalOpen(false);
      quickClienteForm.resetFields();

    } catch (err) {
      applyFormErrors(err, quickClienteForm);
      message.error(normalizeHttpError(err));
    }
  };

  const onEmpresaChange = async (empId: string) => {
    form.setFieldsValue({ cliente_id: undefined });
    setClientesOptions([]);

    if (empId && !id) { // Solo sugerir folio para nuevos presupuestos
      try {
        const data = await presupuestoService.getSiguienteFolio(empId);
        form.setFieldValue('folio', data.folio);
      } catch (error) {
        console.error("Failed to fetch next folio", error);
        form.setFieldValue('folio', 'PRE-????-????');
      }
    }
  };

  // Fetch presupuesto data for the selected version
  const { data: presupuesto, isLoading: loadingPresupuesto } = useQuery<Presupuesto>({
    queryKey: ['presupuesto', selectedVersionId],
    queryFn: () => presupuestoService.getPresupuesto(selectedVersionId!),
    enabled: !!selectedVersionId,
  });

  // Fetch version history when a presupuesto is loaded
  const { data: rawVersionHistory } = useQuery<Presupuesto[]>({
    queryKey: ['presupuestoHistory', presupuesto?.folio],
    queryFn: () => presupuestoService.getPresupuestoHistory(presupuesto!.folio, presupuesto!.empresa_id),
    enabled: !!presupuesto,
  });

  const versionHistory = useMemo(() => {
    return (rawVersionHistory || []).sort((a, b) => b.version - a.version);
  }, [rawVersionHistory]);

  // Set form fields when data is loaded or for a new form
  useEffect(() => {
    if (selectedVersionId) {
      if (presupuesto) {
        form.setFieldsValue({
          ...presupuesto,
          fecha_emision: presupuesto.fecha_emision ? dayjs(presupuesto.fecha_emision) : null,
          fecha_vencimiento: presupuesto.fecha_vencimiento ? dayjs(presupuesto.fecha_vencimiento) : null,
        });
        setConceptos(presupuesto.detalles || []);
        if (presupuesto.cliente) {
          setClientesOptions([{ label: presupuesto.cliente.nombre_comercial, value: presupuesto.cliente.id }]);
        }
      }
    } else {
      // Set defaults for new presupuesto
      const today = dayjs();
      form.setFieldsValue({
        fecha_emision: today,
        fecha_vencimiento: today.add(10, 'day'),
        folio: undefined,
        cliente_id: undefined,
      });
      setConceptos([]);
      setClientesOptions([]);
    }
  }, [selectedVersionId, presupuesto, form]);

  const onFechaEmisionChange = (date: Dayjs | null) => {
    if (date) {
      form.setFieldValue('fecha_vencimiento', date.add(10, 'day'));
    } else {
      form.setFieldValue('fecha_vencimiento', null);
    }
  };

  // Conceptos logic
  const buscarPS = useMemo(
    () =>
      debounce(async (q: string) => {
        const empId = form.getFieldValue('empresa_id');
        if (!empId || !q || q.trim().length < 2) {
          setPsOpts([]);
          return;
        }
        try {
          const data = await productoServicioService.buscarProductoServicios(q, empId);
          const opts = (data || []).map((it: ProductoServicioOut) => ({
            value: it.id,
            label: `${it.clave_producto || 'N/A'} — ${it.descripcion}`,
            meta: it,
          }));
          setPsOpts(opts);
        } catch {
          setPsOpts([]);
        }
      }, 300),
    [form],
  );

  const onSelectPSInModal = (_: string, option: { meta: ProductoServicioOut }) => {
    const meta = option?.meta || {};
    conceptoForm.setFieldsValue({
      descripcion: meta.descripcion,
      precio_unitario: meta.valor_unitario,
      producto_servicio_id: meta.id,
    });
  };

  const handleSaveConcepto = async () => {
    const values = await conceptoForm.validateFields();
    const importe = (values.cantidad || 0) * (values.precio_unitario || 0);
    
    const newConcepto: PresupuestoDetalle = {
      id: editingConcepto?.id || crypto.randomUUID(),
      ...values,
      importe: importe,
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

  const onFinish = async (values: PresupuestoCreate) => {
    setIsSubmitting(true);
    
    const formattedValues = {
      ...values,
      fecha_emision: values.fecha_emision ? dayjs(values.fecha_emision).format('YYYY-MM-DD') : undefined,
      fecha_vencimiento: values.fecha_vencimiento ? dayjs(values.fecha_vencimiento).format('YYYY-MM-DD') : undefined,
    };

    const payload: PresupuestoCreate | PresupuestoUpdate = {
      ...formattedValues,
      detalles: conceptos.map(c => ({
        producto_servicio_id: c.producto_servicio_id,
        descripcion: c.descripcion,
        cantidad: c.cantidad,
        unidad: c.unidad,
        precio_unitario: c.precio_unitario,
        tasa_impuesto: c.tasa_impuesto,
        costo_estimado: c.costo_estimado,
      })),
    };

    try {
      if (id) {
        const newVersion = await presupuestoService.updatePresupuesto(id, payload as PresupuestoUpdate);
        message.success(`Presupuesto actualizado a la versión ${newVersion.version}`);
        await queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
        router.push(`/presupuestos/form/${newVersion.id}`);

      } else {
        const newPresupuesto = await presupuestoService.createPresupuesto(payload as PresupuestoCreate);
        message.success('Presupuesto creado con éxito');
        router.push(`/presupuestos/form/${newPresupuesto.id}`);
      }
    } catch (err) {
      applyFormErrors(err, form);
      message.error(normalizeHttpError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const statusUpdateMutation = useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: string }) =>
      presupuestoService.updatePresupuestoStatus(id, estado),
    onSuccess: () => {
      message.success('Estado del presupuesto actualizado');
      queryClient.invalidateQueries({ queryKey: ['presupuesto', selectedVersionId] });
      queryClient.invalidateQueries({ queryKey: ['presupuestoHistory', presupuesto?.folio] });
    },
    onError: (err) => message.error(normalizeHttpError(err) || 'Error al actualizar estado'),
  });

  const uploadEvidenciaMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      presupuestoService.uploadEvidencia(id, file),
    onSuccess: () => {
      message.success('Evidencia subida y presupuesto aceptado');
      queryClient.invalidateQueries({ queryKey: ['presupuesto', selectedVersionId] });
      queryClient.invalidateQueries({ queryKey: ['presupuestoHistory', presupuesto?.folio] });
    },
    onError: (err) => message.error(normalizeHttpError(err) || 'Error al subir evidencia'),
  });

  const verPDF = async () => {
    if (!selectedVersionId) {
      message.info('Guarda el presupuesto para generar una vista previa.');
      return;
    }
    try {
      const blob = await presupuestoService.getPresupuestoPdf(selectedVersionId);
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e: any) {
      message.error(normalizeHttpError(e) || 'No se pudo abrir el PDF');
    }
  };

  const empresasOptions = empresas?.map(e => ({ value: e.id, label: e.nombre_comercial })) || [];

  return {
    form,
    isSubmitting,
    loading: loadingEmpresas || (!!id && loadingPresupuesto),
    presupuesto,
    onFinish,
    clientesOptions,
    empresasOptions,
    empresaId,
    onEmpresaChange,
    buscarClientes,
    onFechaEmisionChange,
    // Versioning
    versionHistory,
    selectedVersionId,
    setSelectedVersionId,
    // Status Change
    statusUpdateMutation,
    uploadEvidenciaMutation,
    // Conceptos
    conceptos,
    setConceptos,
    isConceptoModalOpen,
    setIsConceptoModalOpen,
    editingConcepto,
    setEditingConcepto,
    setEditingConceptoIndex,
    conceptoForm,
    buscarPS,
    psOpts,
    onSelectPSInModal,
    handleSaveConcepto,
    // Quick Cliente
    isClienteModalOpen,
    setIsClienteModalOpen,
    quickClienteForm,
    handleSaveQuickCliente,
    verPDF,
  };
};