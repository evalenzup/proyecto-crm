import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/router';
import { TablePaginationConfig } from 'antd/es/table';
import { Dayjs } from 'dayjs';
import debounce from 'lodash/debounce';
import {
  getPagos,
  type PagoRow,
  type EstatusPagoCfdi,
} from '@/services/pagoService';
import { searchClientes } from '@/services/facturaService';
import { useEmpresaSelector } from './useEmpresaSelector';

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

  const [clienteOptions, setClienteOptions] = useState<Opcion[]>([]);
  const [clienteId, setClienteId] = useState<string | undefined>(undefined);
  const [clienteQuery, setClienteQuery] = useState<string>('');
  const [estatus, setEstatus] = useState<EstatusPagoCfdi | undefined>(undefined);
  const [rangoFechas, setRangoFechas] = useState<[Dayjs, Dayjs] | null>(null);

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
    } catch (error) {
      console.error('Error fetching pagos', error);
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

  // Ya no necesitamos fetchEmpresas, el hook lo hace

  const debouncedBuscarClientes = useMemo(() =>
    debounce(async (q: string) => {
      if (!q || q.trim().length < 3) {
        setClienteOptions([]);
        return;
      }
      try {
        const list = await searchClientes(q, empresaId); // Filtrar por empresa
        setClienteOptions(
          (list || []).slice(0, 20).map((c: any) => ({
            value: c.id,
            label: c.nombre_comercial || c.nombre || c.razon_social || 'Cliente',
          }))
        );
      } catch {
        setClienteOptions([]);
      }
    }, 300)
    , [empresaId]);

  // useEffect(() => {
  //   fetchEmpresas();
  // }, [fetchEmpresas]);
  // ELIMINADO

  // Preview Modal logic
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);
  const [previewRow, setPreviewRow] = useState<PagoRow | null>(null);

  // Email Modal logic
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [emailRow, setEmailRow] = useState<PagoRow | null>(null);
  const [emailLoading, setEmailLoading] = useState(false);

  const abrirEmailModal = (row: PagoRow) => {
    setEmailRow(row);
    setEmailModalOpen(true);
  };

  const verPdf = async (row: PagoRow) => {
    setLoading(true);
    try {
      // Importar getPagoPdf del servicio (asumiendo que existe y se llama así)
      const { getPagoPdf } = await import('@/services/pagoService');
      const blob = await getPagoPdf(row.id);
      const url = window.URL.createObjectURL(blob);
      setPreviewPdfUrl(url);
      setPreviewRow(row);
      setPreviewModalOpen(true);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const cerrarPreview = () => {
    setPreviewModalOpen(false);
    setPreviewRow(null);
    if (previewPdfUrl) {
      window.URL.revokeObjectURL(previewPdfUrl);
      setPreviewPdfUrl(null);
    }
  };

  const cerrarEmailModal = () => {
    setEmailModalOpen(false);
    setEmailRow(null);
  };

  const enviarCorreo = async (id: string, recipients: string[]) => {
    setEmailLoading(true);
    try {
      // Importar dinámicamente o usar la función exportada que ya existe
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
      clienteId, setClienteId, clienteOptions,
      clienteQuery, setClienteQuery, debouncedBuscarClientes,
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
