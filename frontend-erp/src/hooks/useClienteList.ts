import { useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { clienteService, ClienteOut } from '../services/clienteService';
import { EmpresaOut } from '../services/empresaService';
import { useEmpresaSelector } from './useEmpresaSelector'; // Importar hook

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
  isAdmin: boolean; // Exponer para UI
}

export const useClienteList = (): UseClienteListResult => {
  const [clientes, setClientes] = useState<ClienteOut[]>([]);
  const [loading, setLoading] = useState(false); // Inicialmente false, esperamos a tener empresa
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Usar el hook de selector de empresa
  const {
    selectedEmpresaId: empresaFiltro,
    setSelectedEmpresaId: setEmpresaFiltro,
    empresas: empresasForFilter,
    isAdmin
  } = useEmpresaSelector();

  const [rfcFiltro, setRfcFiltro] = useState<string>('');
  const [nombreFiltro, setNombreFiltro] = useState<string>('');

  // Debounced filter values
  const [debouncedRfc, setDebouncedRfc] = useState('');
  const [debouncedNombre, setDebouncedNombre] = useState('');

  // This effect debounces the text inputs
  useEffect(() => {
    const timer = setTimeout(() => {
      if (rfcFiltro.length === 0 || rfcFiltro.length >= 3) {
        setDebouncedRfc(rfcFiltro);
      }
      setDebouncedNombre(nombreFiltro);
    }, 500);
    return () => clearTimeout(timer);
  }, [rfcFiltro, nombreFiltro]);

  const fetchClientes = useCallback(async () => {
    if (!empresaFiltro) {
      setClientes([]);
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
      setClientes(data.items);
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

  const clearFilters = useCallback(() => {
    // Si es admin, NO limpiamos la empresa a null, tal vez a undefined, pero useEmpresaSelector lo maneja?
    // Mejor solo limpiar textos. El usuario puede cambiar empresa manualmente.
    // Si limpiamos empresaFiltro a null, el hook useEmpresaSelector no re-selecciona automatico
    // a menos que reiniciemos el componente.
    // Para simplificar: Limpiar filtros de texto. El de empresa se cambia explicitamente.
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
    setEmpresaFiltro, // Type fix implied: string | undefined
    rfcFiltro,
    setRfcFiltro,
    nombreFiltro,
    setNombreFiltro,
    clearFilters,
    isAdmin
  };
};