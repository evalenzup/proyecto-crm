// frontend-erp/src/hooks/usePresupuestoList.ts
import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { presupuestoService, PresupuestoSimpleOut } from '@/services/presupuestoService';
import { clienteService, ClienteOut } from '@/services/clienteService';
import { message } from 'antd';
import { normalizeHttpError } from '@/utils/httpError';
import { Dayjs } from 'dayjs';
import { useEmpresaSelector } from './useEmpresaSelector';

type RangeValue = [Dayjs | null, Dayjs | null] | null;

export const usePresupuestoList = () => {
  const queryClient = useQueryClient();
  const router = useRouter();
  
  // State for pagination and filters
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [clienteId, setClienteId] = useState<string | undefined>(undefined);
  const [clienteQuery, setClienteQuery] = useState('');
  const [estatus, setEstatus] = useState<string | undefined>(undefined);
  const [rangoFechas, setRangoFechas] = useState<RangeValue>(null);
  const [sort, setSort] = useState<{ order_by?: string; order_dir?: 'asc' | 'desc' }>({});

  // Empresa global (from sidebar selector)
  const { selectedEmpresaId: empresaId } = useEmpresaSelector();

  const { data: clienteOptionsData, isLoading: loadingClientes } = useQuery({
    queryKey: ['clientesForSearch', clienteQuery],
    queryFn: () => clienteService.buscarClientes(clienteQuery),
    enabled: clienteQuery.length >= 3,
  });
  const clienteOptions = useMemo(() => 
    clienteOptionsData?.map(c => ({ label: c.nombre_comercial, value: c.id })) || [], 
    [clienteOptionsData]
  );

  const debouncedBuscarClientes = useMemo(() => {
    const loadOptions = (value: string) => {
      if (value.length >= 3) {
        setClienteQuery(value);
      }
    };
    return loadOptions;
  }, []);

  // Main data query
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['presupuestos', pagination, empresaId, clienteId, estatus, rangoFechas, sort],
    queryFn: () =>
      presupuestoService.getPresupuestos({
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        empresa_id: empresaId,
        cliente_id: clienteId,
        estado: estatus,
        fecha_inicio: rangoFechas?.[0]?.format('YYYY-MM-DD'),
        fecha_fin: rangoFechas?.[1]?.format('YYYY-MM-DD'),
        order_by: sort.order_by,
        order_dir: sort.order_dir,
      }),
    placeholderData: keepPreviousData,
  });

  const fetchPresupuestos = useCallback((pag = pagination) => {
    setPagination(pag);
    refetch();
  }, [refetch, pagination]);

  const handleTableChange = useCallback((pag: any, _filters: any, sorter: any) => {
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    setSort(s && s.order
      ? { order_by: String(s.columnKey ?? s.field), order_dir: (s.order === 'ascend' ? 'asc' : 'desc') as 'asc' | 'desc' }
      : {});
    setPagination((p) => ({ ...p, current: pag?.current ?? 1 }));
  }, []);

  useEffect(() => {
    fetchPresupuestos();
  }, []);


  const deleteMutation = useMutation({
    mutationFn: presupuestoService.deletePresupuesto,
    onSuccess: () => {
      message.success('Presupuesto eliminado con éxito');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
    },
    onError: (err: any) => { if (!err?._handled) message.error(normalizeHttpError(err) || 'Error al eliminar'); },
  });

  const sendMutation = useMutation({
    mutationFn: ({ id, email }: { id: string; email: string }) => 
      presupuestoService.sendPresupuesto(id, email),
    onSuccess: () => {
      message.success('Presupuesto enviado con éxito');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
    },
    onError: (err: any) => { if (!err?._handled) message.error(normalizeHttpError(err) || 'Error al enviar'); },
  });

  const conversionMutation = useMutation({
    mutationFn: presupuestoService.convertirAFactura,
    onSuccess: (data) => {
      message.success('Presupuesto convertido a factura con éxito');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
      router.push(`/facturas/form/${data.id}`);
    },
    onError: (err: any) => { if (!err?._handled) message.error(normalizeHttpError(err) || 'Error al convertir a factura'); },
  });

  const statusUpdateMutation = useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: string }) =>
      presupuestoService.updatePresupuestoStatus(id, estado),
    onSuccess: () => {
      message.success('Estado del presupuesto actualizado');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
    },
    onError: (err: any) => { if (!err?._handled) message.error(normalizeHttpError(err) || 'Error al actualizar estado'); },
  });

  const uploadEvidenciaMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      presupuestoService.uploadEvidencia(id, file),
    onSuccess: () => {
      message.success('Evidencia subida y presupuesto aceptado');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
    },
    onError: (err: any) => { if (!err?._handled) message.error(normalizeHttpError(err) || 'Error al subir evidencia'); },
  });

  // ── PDF Preview ────────────────────────────────────────────────────────────
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);
  const [previewRow, setPreviewRow] = useState<PresupuestoSimpleOut | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const verPdf = useCallback(async (row: PresupuestoSimpleOut) => {
    setPdfLoading(true);
    try {
      const blob = await presupuestoService.getPresupuestoPdf(row.id);
      const url = window.URL.createObjectURL(blob);
      setPreviewPdfUrl(url);
      setPreviewRow(row);
      setPreviewModalOpen(true);
    } catch (err: any) {
      if (!err?._handled) message.error('No se pudo generar la vista previa del PDF');
    } finally {
      setPdfLoading(false);
    }
  }, []);

  const cerrarPreview = useCallback(() => {
    setPreviewModalOpen(false);
    setPreviewRow(null);
    if (previewPdfUrl) {
      window.URL.revokeObjectURL(previewPdfUrl);
      setPreviewPdfUrl(null);
    }
  }, [previewPdfUrl]);

  const filters = {
    clienteId, setClienteId, clienteOptions, clienteQuery, setClienteQuery, debouncedBuscarClientes,
    estatus, setEstatus,
    rangoFechas, setRangoFechas,
  };

  return {
    rows: data?.items ?? [],
    totalRows: data?.total ?? 0,
    loading: isLoading,
    pagination,
    fetchPresupuestos,
    sort,
    handleTableChange,
    filters,
    handleDelete: deleteMutation.mutate,
    sendMutation,
    conversionMutation,
    statusUpdateMutation,
    uploadEvidenciaMutation,
    verPdf,
    cerrarPreview,
    previewModalOpen,
    previewPdfUrl,
    previewRow,
    pdfLoading,
  };
};
