import { useState, useEffect, useCallback, useMemo } from 'react';
import { message } from 'antd';
import { TablePaginationConfig } from 'antd/es/table';
import { Dayjs } from 'dayjs';
import {
  getFacturas,
  type FacturaListParams,
  type FacturaRow,
} from '@/services/facturaService';
import { useEmpresaSelector } from './useEmpresaSelector';
import { useFilterContext } from '@/context/FilterContext';
import { useClienteSearch } from './useClienteSearch';
import { usePdfPreview } from './usePdfPreview';
import { useEmailModal } from './useEmailModal';
import dayjs from 'dayjs';

type EstatusCFDI = 'BORRADOR' | 'TIMBRADA' | 'CANCELADA';
type EstatusPago = 'PAGADA' | 'NO_PAGADA';
interface Opcion { label: string; value: string }

const toLimitOffset = (pagination: TablePaginationConfig) => {
  const page = pagination.current ?? 1;
  const pageSize = pagination.pageSize ?? 10;
  const offset = (page - 1) * pageSize;
  return { limit: pageSize, offset };
};

const DEFAULT_SORT = { order_by: 'serie_folio' as const, order_dir: 'desc' as const };

export const useFacturasList = () => {
  const [rows, setRows] = useState<FacturaRow[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [loading, setLoading] = useState(false);
  const [sort, setSort] = useState<{ order_by: string; order_dir: 'asc' | 'desc' }>(DEFAULT_SORT);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 10,
    showSizeChanger: true,
    pageSizeOptions: [10, 20, 50, 100],
  });

  // Filtros
  const {
    selectedEmpresaId: empresaId,
    setSelectedEmpresaId: setEmpresaId,
    empresas,
    isAdmin
  } = useEmpresaSelector();

  const empresasOptions = (empresas || []).map((e: any) => ({ value: e.id, label: e.nombre_comercial || e.nombre }));

  // Use Unified Filter Context
  const { facturas: filters, setFacturas: setFilters } = useFilterContext();
  const clienteId = filters.clienteId;
  const clienteQuery = filters.clienteQuery;
  const estatus = filters.estatus as EstatusCFDI | undefined;
  const estatusPago = filters.estatusPago as EstatusPago | undefined;
  const folio = filters.folio;

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
  const setEstatus = (val: EstatusCFDI | undefined) => setFilters(prev => ({ ...prev, estatus: val }));
  const setEstatusPago = (val: EstatusPago | undefined) => setFilters(prev => ({ ...prev, estatusPago: val }));
  const setFolio = (val: string) => setFilters(prev => ({ ...prev, folio: val }));

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
  } = usePdfPreview<FacturaRow>();

  const {
    emailModalOpen, emailRow, emailLoading, setEmailLoading,
    abrirEmailModal, cerrarEmailModal,
  } = useEmailModal<FacturaRow>();

  const fetchFacturas = useCallback(async (
    pag: TablePaginationConfig = pagination,
    sortArg: { order_by: string; order_dir: 'asc' | 'desc' } = sort,
  ) => {
    if (!empresaId) {
      setRows([]);
      setTotalRows(0);
      return;
    }

    const { limit, offset } = toLimitOffset(pag);
    const params: FacturaListParams = { limit, offset, order_by: sortArg.order_by as any, order_dir: sortArg.order_dir };
    if (empresaId) params.empresa_id = empresaId;
    if (clienteId) params.cliente_id = clienteId;
    if (estatus) params.estatus = estatus;
    if (estatusPago) params.status_pago = estatusPago;
    if (rangoFechas) {
      params.fecha_desde = rangoFechas[0].format('YYYY-MM-DD');
      params.fecha_hasta = rangoFechas[1].format('YYYY-MM-DD');
    }
    if (folio) {
      params.folio = folio;
    }

    setLoading(true);
    try {
      const data = await getFacturas(params);        // ← devuelve data directo
      setRows(data.items || []);
      setTotalRows(data.total || 0);
      setPagination((p) => ({ ...p, current: pag.current, pageSize: pag.pageSize }));
    } catch (error: any) {
      if (!error?._handled) message.error('Error al cargar las facturas');
    } finally {
      setLoading(false);
    }
  }, [empresaId, clienteId, estatus, estatusPago, rangoFechas, folio, sort]);

  // Handler para el onChange de la <Table>: aplica orden del servidor.
  const handleTableChange = useCallback((pag: TablePaginationConfig, _filters: any, sorter: any) => {
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    const next = (s && s.order)
      ? { order_by: String(s.columnKey ?? s.field), order_dir: (s.order === 'ascend' ? 'asc' : 'desc') as 'asc' | 'desc' }
      : DEFAULT_SORT;
    setSort(next);
    fetchFacturas(pag, next);
  }, [fetchFacturas]);

  useEffect(() => {
    fetchFacturas();
  }, [fetchFacturas]);

  // Reset page logic
  useEffect(() => {
    setPagination(p => ({ ...p, current: 1 }));
  }, [empresaId, clienteId, estatus, estatusPago, rangoFechas, folio]);

  // Ya no necesitamos fetchEmpresas, el hook lo hace

  // Sync client options when clienteId changes
  useEffect(() => {
    syncClienteById(clienteId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteId]);

  const verPdf = async (row: FacturaRow) => {
    setLoading(true);
    try {
      const blob = row.estatus === 'BORRADOR'
        ? await import('@/services/facturaService').then(m => m.getPdfPreview(row.id))
        : await import('@/services/facturaService').then(m => m.getPdf(row.id));
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
      const { sendEmail, sendPreviewEmail } = await import('@/services/facturaService');
      if (emailRow?.estatus === 'BORRADOR') {
        await sendPreviewEmail(id, recipients);
      } else {
        await sendEmail(id, recipients);
      }
    } finally {
      setEmailLoading(false);
    }
  };

  return {
    rows,
    totalRows,
    loading,
    pagination,
    fetchFacturas,
    setPagination,
    sort,
    handleTableChange,
    filters: {
      empresaId, setEmpresaId, empresasOptions, empresas,
      clienteId, setClienteId,
      clienteOptionsComercial, clienteOptionsFiscal,
      clienteQuery, setClienteQuery,
      debouncedBuscarClientesComercial, debouncedBuscarClientesFiscal,
      estatus, setEstatus,
      estatusPago, setEstatusPago,
      rangoFechas, setRangoFechas,
      folio, setFolio,
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