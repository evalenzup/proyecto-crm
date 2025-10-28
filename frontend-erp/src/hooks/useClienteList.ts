import { useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { clienteService, ClienteOut } from '../services/clienteService';
import { empresaService, EmpresaOut } from '../services/empresaService';

interface UseClienteListResult {
  clientes: ClienteOut[];
  loading: boolean;
  total: number;
  currentPage: number;
  pageSize: number;
  handlePageChange: (page: number, size?: number) => void;
  handleDelete: (id: string) => Promise<void>;
  empresasForFilter: EmpresaOut[];
  empresaFiltro: string | null;
  setEmpresaFiltro: (id: string | null) => void;
  rfcFiltro: string;
  setRfcFiltro: (rfc: string) => void;
  nombreFiltro: string;
  setNombreFiltro: (nombre: string) => void;
  clearFilters: () => void;
}

export const useClienteList = (): UseClienteListResult => {
  const [clientes, setClientes] = useState<ClienteOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const [empresasForFilter, setEmpresasForFilter] = useState<EmpresaOut[]>([]);

  // Filter states
  const [empresaFiltro, setEmpresaFiltro] = useState<string | null>(null);
  const [rfcFiltro, setRfcFiltro] = useState<string>('');
  const [nombreFiltro, setNombreFiltro] = useState<string>('');

  // Debounced filter values
  const [debouncedRfc, setDebouncedRfc] = useState('');
  const [debouncedNombre, setDebouncedNombre] = useState('');

  // This effect debounces the text inputs
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedRfc(rfcFiltro);
      setDebouncedNombre(nombreFiltro);
    }, 500);
    return () => clearTimeout(timer);
  }, [rfcFiltro, nombreFiltro]);

  const fetchClientes = useCallback(async () => {
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
      setClientes(data.items);
      setTotal(data.total);
    } catch (error) {
      message.error('Error al cargar los clientes.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, empresaFiltro, debouncedRfc, debouncedNombre]);

  const fetchEmpresasForFilter = useCallback(async () => {
    try {
      const data = await empresaService.getEmpresas();
      setEmpresasForFilter(data);
    } catch (error) {
      message.error('Error al cargar empresas para el filtro.');
    }
  }, []);

  useEffect(() => {
    fetchClientes();
  }, [fetchClientes]);

  useEffect(() => {
    fetchEmpresasForFilter();
  }, [fetchEmpresasForFilter]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await clienteService.deleteCliente(id);
      message.success('Cliente eliminado correctamente.');
      fetchClientes();
    } catch (error) {
      message.error('Error al eliminar el cliente.');
    }
  }, [fetchClientes]);

  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size && size !== pageSize) {
      setPageSize(size);
    }
  };

  const clearFilters = useCallback(() => {
    setEmpresaFiltro(null);
    setRfcFiltro('');
    setNombreFiltro('');
  }, []);

  return {
    clientes,
    loading,
    total,
    currentPage,
    pageSize,
    handlePageChange,
    handleDelete,
    empresasForFilter,
    empresaFiltro,
    setEmpresaFiltro,
    rfcFiltro,
    setRfcFiltro,
    nombreFiltro,
    setNombreFiltro,
    clearFilters,
  };
};