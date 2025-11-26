// frontend-erp/src/hooks/usePresupuestoList.ts
import { useState, useCallback, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { presupuestoService, PresupuestoSimpleOut } from '@/services/presupuestoService';
import { empresaService, EmpresaOut } from '@/services/empresaService';
import { clienteService, ClienteOut } from '@/services/clienteService';
import { message } from 'antd';
import { normalizeHttpError } from '@/utils/httpError';
import { Dayjs } from 'dayjs';

type RangeValue = [Dayjs | null, Dayjs | null] | null;

export const usePresupuestoList = () => {
  const queryClient = useQueryClient();
  
  // State for pagination and filters
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [empresaId, setEmpresaId] = useState<string | undefined>(undefined);
  const [clienteId, setClienteId] = useState<string | undefined>(undefined);
  const [clienteQuery, setClienteQuery] = useState('');
  const [estatus, setEstatus] = useState<string | undefined>(undefined);
  const [rangoFechas, setRangoFechas] = useState<RangeValue>(null);

  // Fetching data for filters
  const { data: empresasOptions = [] } = useQuery({
    queryKey: ['empresasForSelect'],
    queryFn: () => empresaService.getEmpresas({ limit: 1000, offset: 0 }),
  });

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
    queryKey: ['presupuestos', pagination, empresaId, clienteId, estatus, rangoFechas],
    queryFn: () => 
      presupuestoService.getPresupuestos({
        offset: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        empresa_id: empresaId,
        cliente_id: clienteId,
        estado: estatus,
        fecha_inicio: rangoFechas?.[0]?.format('YYYY-MM-DD'),
        fecha_fin: rangoFechas?.[1]?.format('YYYY-MM-DD'),
      }),
    keepPreviousData: true,
  });

  const fetchPresupuestos = useCallback((pag = pagination) => {
    setPagination(pag);
    refetch();
  }, [refetch, pagination]);

  useEffect(() => {
    fetchPresupuestos();
  }, []);


  const deleteMutation = useMutation({
    mutationFn: presupuestoService.deletePresupuesto,
    onSuccess: () => {
      message.success('Presupuesto eliminado con éxito');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
    },
    onError: (err) => message.error(normalizeHttpError(err) || 'Error al eliminar'),
  });

  const sendMutation = useMutation({
    mutationFn: ({ id, email }: { id: string; email: string }) => 
      presupuestoService.sendPresupuesto(id, email),
    onSuccess: () => {
      message.success('Presupuesto enviado con éxito');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
    },
    onError: (err) => message.error(normalizeHttpError(err) || 'Error al enviar'),
  });

  const conversionMutation = useMutation({
    mutationFn: presupuestoService.convertirAFactura,
    onSuccess: (data) => {
      message.success('Presupuesto convertido a factura con éxito');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
      // TODO: Redirect to the new invoice
      // router.push(`/facturas/form/${data.id}`);
    },
    onError: (err) => message.error(normalizeHttpError(err) || 'Error al convertir a factura'),
  });

  const statusUpdateMutation = useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: string }) =>
      presupuestoService.updatePresupuestoStatus(id, estado),
    onSuccess: () => {
      message.success('Estado del presupuesto actualizado');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
    },
    onError: (err) => message.error(normalizeHttpError(err) || 'Error al actualizar estado'),
  });

  const uploadEvidenciaMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      presupuestoService.uploadEvidencia(id, file),
    onSuccess: () => {
      message.success('Evidencia subida y presupuesto aceptado');
      queryClient.invalidateQueries({ queryKey: ['presupuestos'] });
    },
    onError: (err) => message.error(normalizeHttpError(err) || 'Error al subir evidencia'),
  });

  const filters = {
    empresaId, setEmpresaId, empresasOptions,
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
    filters,
    handleDelete: deleteMutation.mutate,
    sendMutation,
    conversionMutation,
    statusUpdateMutation,
    uploadEvidenciaMutation,
  };
};
