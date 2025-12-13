import { useState, useEffect, useCallback, useMemo } from 'react';
import { TablePaginationConfig } from 'antd/es/table';
import { Dayjs } from 'dayjs';
import debounce from 'lodash/debounce';
import {
  getFacturas,
  searchClientes,
  type FacturaListParams,
  type FacturaRow,
} from '@/services/facturaService';
import { useEmpresaSelector } from './useEmpresaSelector';

type EstatusCFDI = 'BORRADOR' | 'TIMBRADA' | 'CANCELADA';
type EstatusPago = 'PAGADA' | 'NO_PAGADA';
interface Opcion { label: string; value: string }

const toLimitOffset = (pagination: TablePaginationConfig) => {
  const page = pagination.current ?? 1;
  const pageSize = pagination.pageSize ?? 10;
  const offset = (page - 1) * pageSize;
  return { limit: pageSize, offset };
};

export const useFacturasList = () => {
  const [rows, setRows] = useState<FacturaRow[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [loading, setLoading] = useState(false);
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

  const [clienteOptions, setClienteOptions] = useState<Opcion[]>([]);
  const [clienteId, setClienteId] = useState<string | undefined>(undefined);
  const [clienteQuery, setClienteQuery] = useState<string>('');
  const [estatus, setEstatus] = useState<EstatusCFDI | undefined>(undefined);
  const [estatusPago, setEstatusPago] = useState<EstatusPago | undefined>(undefined);
  const [rangoFechas, setRangoFechas] = useState<[Dayjs, Dayjs] | null>(null);

  const fetchFacturas = useCallback(async (pag: TablePaginationConfig = pagination) => {
    if (!empresaId) {
      setRows([]);
      setTotalRows(0);
      return;
    }

    const { limit, offset } = toLimitOffset(pag);
    const params: FacturaListParams = { limit, offset, order_by: 'serie_folio', order_dir: 'desc' };
    if (empresaId) params.empresa_id = empresaId;
    if (clienteId) params.cliente_id = clienteId;
    if (estatus) params.estatus = estatus;
    if (estatusPago) params.status_pago = estatusPago;
    if (rangoFechas) {
      params.fecha_desde = rangoFechas[0].format('YYYY-MM-DD');
      params.fecha_hasta = rangoFechas[1].format('YYYY-MM-DD');
    }

    setLoading(true);
    try {
      const data = await getFacturas(params);        // ← devuelve data directo
      setRows(data.items || []);
      setTotalRows(data.total || 0);
      setPagination((p) => ({ ...p, current: pag.current, pageSize: pag.pageSize }));
    } catch (error) {
      // Puedes mostrar un message.error aquí si quieres
      console.error('Error fetching facturas', error);
    } finally {
      setLoading(false);
    }
  }, [empresaId, clienteId, estatus, estatusPago, rangoFechas]);

  useEffect(() => {
    fetchFacturas();
  }, [fetchFacturas]);

  // Ya no necesitamos fetchEmpresas, el hook lo hace

  const debouncedBuscarClientes = useMemo(() =>
    debounce(async (q: string) => {
      if (!q || q.trim().length < 3) {
        setClienteOptions([]);
        return;
      }
      try {
        const list = await searchClientes(q, empresaId); // Buscar clientes filtrados por empresa si es posible
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
    , [empresaId]); // Dependencia empresaId agregada

  // useEffect(() => {
  //   fetchEmpresas();
  // }, [fetchEmpresas]);
  // ELIMINADO

  // Preview Modal
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);
  const [previewRow, setPreviewRow] = useState<FacturaRow | null>(null);

  const verPdf = async (row: FacturaRow) => {
    setLoading(true);
    try {
      // Importar servicio dinámicamente o añadir imports arriba si no conflicituan
      // Asumiendo imports: getPdf, getPdfPreview
      const blob = row.estatus === 'BORRADOR'
        ? await import('@/services/facturaService').then(m => m.getPdfPreview(row.id))
        : await import('@/services/facturaService').then(m => m.getPdf(row.id));

      const url = window.URL.createObjectURL(blob);
      setPreviewPdfUrl(url);
      setPreviewRow(row); // Guardar row para nombre de archivo
      setPreviewModalOpen(true);
    } catch (error) {
      console.error(error);
      // Podrías añadir un toast message aquí si importas 'message' de antd
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

  return {
    rows,
    totalRows,
    loading,
    pagination,
    fetchFacturas,
    setPagination,
    filters: {
      empresaId, setEmpresaId, empresasOptions,
      clienteId, setClienteId, clienteOptions,
      clienteQuery, setClienteQuery, debouncedBuscarClientes,
      estatus, setEstatus,
      estatusPago, setEstatusPago,
      rangoFechas, setRangoFechas,
      isAdmin,
    },
    // Preview helpers
    previewModalOpen,
    previewPdfUrl,
    previewRow,
    verPdf,
    cerrarPreview,
  };
};