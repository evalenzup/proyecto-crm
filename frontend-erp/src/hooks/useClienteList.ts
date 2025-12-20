import { useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { useFilterContext } from '@/context/FilterContext';
import { clienteService, ClienteOut } from '../services/clienteService';
import { EmpresaOut } from '../services/empresaService';
import { useEmpresaSelector } from './useEmpresaSelector';

interface UseClienteListResult {
  clientes: ClienteOut[];
  loading: boolean;
  total: number;
  currentPage: number;
  pageSize: number;
  handlePageChange: (page: number, size?: number) => void;
  handleDelete: (id: string) => Promise<void>;
  empresasForFilter: EmpresaOut[];
  empresaFiltro: string | undefined;
  setEmpresaFiltro: (id: string | undefined) => void;
  rfcFiltro: string;
  setRfcFiltro: (rfc: string) => void;
  nombreFiltro: string;
  setNombreFiltro: (nombre: string) => void;
  clearFilters: () => void;
  isAdmin: boolean;
}

export const useClienteList = (): UseClienteListResult => {
  const [clientes, setClientesList] = useState<ClienteOut[]>([]); // Renamed internal state to avoid conflict with context 'clientes'
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const {
    selectedEmpresaId: empresaFiltro,
    setSelectedEmpresaId: setEmpresaFiltro,
    empresas: empresasForFilter,
    isAdmin
  } = useEmpresaSelector();

  // Use Unified Filter Context
  const { clientes: filterState, setClientes: setFilterState } = useFilterContext();
  const rfcFiltro = filterState.rfc;
  const nombreFiltro = filterState.nombre;

  const setRfcFiltro = useCallback((val: string) => setFilterState(prev => ({ ...prev, rfc: val })), [setFilterState]);
  const setNombreFiltro = useCallback((val: string) => setFilterState(prev => ({ ...prev, nombre: val })), [setFilterState]);

  const clearFilters = useCallback(() => {
    setFilterState({ rfc: '', nombre: '' });
  }, [setFilterState]);

  // Debounced local state
  const [debouncedRfc, setDebouncedRfc] = useState(rfcFiltro);
  const [debouncedNombre, setDebouncedNombre] = useState(nombreFiltro);

  // Update debounced values when context changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (rfcFiltro.length === 0 || rfcFiltro.length >= 3) {
        setDebouncedRfc(rfcFiltro);
      }
      setDebouncedNombre(nombreFiltro);
    }, 500);
    return () => clearTimeout(timer);
  }, [rfcFiltro, nombreFiltro]);

  // Reset page to 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [empresaFiltro, debouncedRfc, debouncedNombre]);

  const fetchClientes = useCallback(async () => {
    if (!empresaFiltro) {
      setClientesList([]);
      setTotal(0);
      return;
    }

    setLoading(true);
    try {
      const params = {
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
        empresa_id: empresaFiltro,
        rfc: debouncedRfc,
        nombre_comercial: debouncedNombre,
      };
      const data = await clienteService.getClientes(params);
      setClientesList(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error(error);
      message.error('Error al cargar los clientes.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, empresaFiltro, debouncedRfc, debouncedNombre]);

  // NO necesitamos cargar empresas manualmente aquí, el hook lo hace

  useEffect(() => {
    fetchClientes();
  }, [fetchClientes]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await clienteService.deleteCliente(id);
      message.success('Cliente eliminado correctamente.');
      fetchClientes();
    } catch (error) {
      console.error(error);
      message.error('Error al eliminar el cliente.');
    }
  }, [fetchClientes]);

  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size && size !== pageSize) {
      setPageSize(size);
    }
  };

  // clearFilters from context already exposed
  // But if we need custom logic we can keep a wrapper.
  // The original one set state to empty string. Context one does same.
  // We can just return 'clearFilters' from the destructuring above and remove this Block if it matches.
  // But wait, the return logic below uses 'clearFilters'. Let's ensure strict equivalence.

  return {
    clientes: clientes, // Renamed state variable
    loading,
    total,
    currentPage,
    pageSize,
    handlePageChange,
    handleDelete,
    empresasForFilter,
    empresaFiltro,
    setEmpresaFiltro, // Type fix implied: string | undefined
    rfcFiltro,
    setRfcFiltro,
    nombreFiltro,
    setNombreFiltro,
    clearFilters,
    isAdmin
  };
};