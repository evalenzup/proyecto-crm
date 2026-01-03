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
import { useFilterContext } from '@/context/FilterContext';
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

  const [clienteOptionsComercial, setClienteOptionsComercial] = useState<Opcion[]>([]);
  const [clienteOptionsFiscal, setClienteOptionsFiscal] = useState<Opcion[]>([]);

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
    if (folio) {
      params.folio = folio;
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
  }, [empresaId, clienteId, estatus, estatusPago, rangoFechas, folio]);

  useEffect(() => {
    fetchFacturas();
  }, [fetchFacturas]);

  // Reset page logic
  useEffect(() => {
    setPagination(p => ({ ...p, current: 1 }));
  }, [empresaId, clienteId, estatus, estatusPago, rangoFechas, folio]);

  // Ya no necesitamos fetchEmpresas, el hook lo hace

  const debouncedBuscarClientesComercial = useMemo(() =>
    debounce(async (q: string) => {
      if (!q || q.trim().length < 3) {
        setClienteOptionsComercial([]);
        return;
      }
      try {
        const list = await searchClientes(q, empresaId, 'comercial');
        setClienteOptionsComercial(
          (list || []).slice(0, 20).map((c: any) => ({
            value: c.id,
            label: `${c.nombre_comercial} (${c.nombre_razon_social})`,
          }))
        );
      } catch {
        setClienteOptionsComercial([]);
      }
    }, 300)
    , [empresaId]);

  const debouncedBuscarClientesFiscal = useMemo(() =>
    debounce(async (q: string) => {
      if (!q || q.trim().length < 3) {
        setClienteOptionsFiscal([]);
        return;
      }
      try {
        const list = await searchClientes(q, empresaId, 'fiscal');
        setClienteOptionsFiscal(
          (list || []).slice(0, 20).map((c: any) => ({
            value: c.id,
            label: `${c.nombre_razon_social} (${c.nombre_comercial})`,
          }))
        );
      } catch {
        setClienteOptionsFiscal([]);
      }
    }, 300)
    , [empresaId]);

  // Sync client options when clienteId changes
  useEffect(() => {
    if (clienteId) {
      // Reusamos getClienteById del servicio si está exportado, o searchClientes para obtener nombre si no tenemos getById directo.
      // Asumiendo que podemos obtener el cliente para mostrar su nombre.
      // Como no tenemos getClienteById importado explícitamente, vamos a importarlo dinámicamente o asumir que searchById existe.
      // Si no existe, podemos llamar a searchClientes con el ID? No, search busca por texto.
      // Mejor importar getClienteById desde facturaService o clienteService.
      // En usePagoForm importamos getClienteById de facturaService (o similar).
      import('@/services/facturaService').then(({ getClienteById }) => {
        // Nota: getClienteById podría no existir en facturaService si no lo verifiqué.
        // En usePagosList usé: import('@/services/facturaService').then(({ getClienteById }) ...
        // Verifiquemos si existe. Si no, usaremos un truco o fallback.
        // Asumiré que existe por paridad con usePagosList.
        if (getClienteById) {
          getClienteById(clienteId).then((c: any) => {
            if (c) {
              const labelCom = `${c.nombre_comercial} (${c.nombre_razon_social})`;
              const labelFis = `${c.nombre_razon_social} (${c.nombre_comercial})`;
              setClienteOptionsComercial([{ label: labelCom, value: c.id }]);
              setClienteOptionsFiscal([{ label: labelFis, value: c.id }]);
            }
          }).catch(() => { });
        }
      });
    } else {
      setClienteOptionsComercial([]);
      setClienteOptionsFiscal([]);
    }
  }, [clienteId]);

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

  // Email Modal logic
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [emailRow, setEmailRow] = useState<FacturaRow | null>(null);
  const [emailLoading, setEmailLoading] = useState(false);

  const abrirEmailModal = (row: FacturaRow) => {
    setEmailRow(row);
    setEmailModalOpen(true);
  };

  const cerrarEmailModal = () => {
    setEmailModalOpen(false);
    setEmailRow(null);
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