import { useState, useEffect, useCallback, useMemo } from 'react';
import { message } from 'antd';
import { useRouter } from 'next/router';
import { TablePaginationConfig } from 'antd/es/table';
import { Dayjs } from 'dayjs';
import {
  getPagos,
  type PagoRow,
  type EstatusPagoCfdi,
} from '@/services/pagoService';
import { useEmpresaSelector } from './useEmpresaSelector';
import { useFilterContext } from '@/context/FilterContext';
import { useClienteSearch } from './useClienteSearch';
import { usePdfPreview } from './usePdfPreview';
import { useEmailModal } from './useEmailModal';
import dayjs from 'dayjs';

interface Opcion { label: string; value: string }

const toLimitOffset = (pagination: TablePaginationConfig) => {
  const page = pagination.current ?? 1;
  const pageSize = pagination.pageSize ?? 10;
  const offset = (page - 1) * pageSize;
  return { limit: pageSize, offset };
};

export const usePagosList = () => {
  const router = useRouter();
  const [rows, setRows] = useState<PagoRow[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 10,
    showSizeChanger: true,
    pageSizeOptions: [10, 20, 50, 100],
  });

  // Filters
  const {
    selectedEmpresaId: empresaId,
    setSelectedEmpresaId: setEmpresaId,
    empresas,
    isAdmin
  } = useEmpresaSelector();

  const empresasOptions = (empresas || []).map((e: any) => ({ value: e.id, label: e.nombre_comercial || e.nombre }));

  // Use Unified Filter Context
  const { pagos: filters, setPagos: setFilters } = useFilterContext();
  const clienteId = filters.clienteId;
  const clienteQuery = filters.clienteQuery;
  const estatus = filters.estatus as EstatusPagoCfdi | undefined;

  // Convert string dates from context back to Dayjs for RangePicker
  const rangoFechas: [Dayjs, Dayjs] | null = useMemo(() => {
    if (filters.fechaInicio && filters.fechaFin) {
      return [dayjs(filters.fechaInicio), dayjs(filters.fechaFin)];
    }
    return null;
  }, [filters.fechaInicio, filters.fechaFin]);

  // Setters wrappers
  const setClienteId = (val: string | undefined) => setFilters(prev => ({ ...prev, clienteId: val }));
  const setClienteQuery = (val: string) => setFilters(prev => ({ ...prev, clienteQuery: val }));
  const setEstatus = (val: EstatusPagoCfdi | undefined) => setFilters(prev => ({ ...prev, estatus: val }));

  const setRangoFechas = (dates: [Dayjs, Dayjs] | null) => {
    setFilters(prev => ({
      ...prev,
      fechaInicio: dates ? dates[0].format('YYYY-MM-DD') : undefined,
      fechaFin: dates ? dates[1].format('YYYY-MM-DD') : undefined
    }));
  };

  const {
    clienteOptionsComercial, setClienteOptionsComercial,
    clienteOptionsFiscal, setClienteOptionsFiscal,
    debouncedBuscarClientesComercial, debouncedBuscarClientesFiscal,
    syncClienteById,
  } = useClienteSearch(empresaId);

  const {
    previewModalOpen, previewPdfUrl, previewRow,
    openPreview, cerrarPreview,
  } = usePdfPreview<PagoRow>();

  const {
    emailModalOpen, emailRow, emailLoading, setEmailLoading,
    abrirEmailModal, cerrarEmailModal,
  } = useEmailModal<PagoRow>();

  const fetchPagos = useCallback(async (pag: TablePaginationConfig = pagination) => {
    if (!empresaId) {
      setRows([]);
      setTotalRows(0);
      return;
    }
    const { limit, offset } = toLimitOffset(pag);
    const params: any = { limit, offset, order_by: 'folio', order_dir: 'desc' };
    if (empresaId) params.empresa_id = empresaId;
    if (clienteId) params.cliente_id = clienteId;
    if (estatus) params.estatus = estatus;
    if (rangoFechas) {
      params.fecha_desde = rangoFechas[0].format('YYYY-MM-DD');
      params.fecha_hasta = rangoFechas[1].format('YYYY-MM-DD');
    }

    setLoading(true);
    try {
      const data = await getPagos(params);
      setRows(data.items || []);
      setTotalRows(data.total || 0);
      setPagination((p) => ({ ...p, current: pag.current, pageSize: pag.pageSize }));
    } catch (error: any) {
      if (!error?._handled) message.error('Error al cargar los pagos');
    } finally {
      setLoading(false);
    }
  }, [empresaId, clienteId, estatus, rangoFechas]);

  useEffect(() => {
    fetchPagos();
  }, [fetchPagos, router.asPath]);

  // Reset page logic
  useEffect(() => {
    setPagination(p => ({ ...p, current: 1 }));
  }, [empresaId, clienteId, estatus, rangoFechas]);


  // Sync client options when clienteId changes
  useEffect(() => {
    syncClienteById(clienteId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteId]);

  const verPdf = async (row: PagoRow) => {
    setLoading(true);
    try {
      const { getPagoPdf } = await import('@/services/pagoService');
      const blob = await getPagoPdf(row.id);
      openPreview(blob, row);
    } catch (error: any) {
      if (!error?._handled) message.error('Error al generar la vista previa del PDF');
    } finally {
      setLoading(false);
    }
  };

  const enviarCorreo = async (id: string, recipients: string[]) => {
    setEmailLoading(true);
    try {
      const { enviarPagoEmail } = await import('@/services/pagoService');
      await enviarPagoEmail(id, recipients, 'Envío de Complemento de Pago', 'Se adjunta el complemento.');
    } finally {
      setEmailLoading(false);
    }
  };

  return {
    rows,
    totalRows,
    loading,
    pagination,
    fetchPagos,
    setPagination,
    filters: {
      empresaId, setEmpresaId, empresasOptions, empresas,
      clienteId, setClienteId,
      clienteOptionsComercial, clienteOptionsFiscal,
      debouncedBuscarClientesComercial, debouncedBuscarClientesFiscal,
      clienteQuery, setClienteQuery,
      estatus, setEstatus,
      rangoFechas, setRangoFechas,
      isAdmin,
    },
    // Preview helpers
    previewModalOpen,
    previewPdfUrl,
    previewRow,
    verPdf,
    cerrarPreview,
    // Email helpers
    emailModalOpen,
    emailRow,
    emailLoading,
    abrirEmailModal,
    cerrarEmailModal,
    enviarCorreo
  };
};
