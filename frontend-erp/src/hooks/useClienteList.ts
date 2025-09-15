// frontend-erp/src/hooks/useClienteList.ts
import { useEffect, useState, useCallback, useMemo } from 'react';
import { message } from 'antd';
import { clienteService, ClienteOut } from '../services/clienteService';
import { empresaService, EmpresaOut } from '../services/empresaService'; // Necesario para el filtro de empresas

interface UseClienteListResult {
  clientes: ClienteOut[];
  loading: boolean;
  refresh: () => void;
  handleDelete: (id: string) => Promise<void>;
  empresasForFilter: EmpresaOut[]; // Para el dropdown de filtro de empresas
  empresaFiltro: string | null;
  setEmpresaFiltro: (id: string | null) => void;
  rfcFiltro: string;
  setRfcFiltro: (rfc: string) => void;
  nombreFiltro: string;
  setNombreFiltro: (nombre: string) => void;
  clearFilters: () => void;
}

export const useClienteList = (): UseClienteListResult => {
  const [allClientes, setAllClientes] = useState<ClienteOut[]>([]); // Almacena todos los clientes sin filtrar
  const [loading, setLoading] = useState(true);
  const [empresasForFilter, setEmpresasForFilter] = useState<EmpresaOut[]>([]);

  // Estados para los filtros
  const [empresaFiltro, setEmpresaFiltro] = useState<string | null>(null);
  const [rfcFiltro, setRfcFiltro] = useState<string>('');
  const [nombreFiltro, setNombreFiltro] = useState<string>('');

  const fetchAllClientes = useCallback(async () => {
    setLoading(true);
    try {
      const data = await clienteService.getClientes();
      setAllClientes(data);
    } catch (error) {
      message.error('Error al cargar los clientes.');
      console.error('Error fetching clientes:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchEmpresasForFilter = useCallback(async () => {
    try {
      const data = await empresaService.getEmpresas();
      setEmpresasForFilter(data);
    } catch (error) {
      message.error('Error al cargar empresas para el filtro.');
      console.error('Error fetching empresas for filter:', error);
    }
  }, []);

  useEffect(() => {
    fetchAllClientes();
    fetchEmpresasForFilter();
  }, [fetchAllClientes, fetchEmpresasForFilter]);

  const refresh = useCallback(() => {
    fetchAllClientes();
  }, [fetchAllClientes]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await clienteService.deleteCliente(id);
      message.success('Cliente eliminado correctamente.');
      refresh(); // Recargar la lista después de eliminar
    } catch (error) {
      message.error('Error al eliminar el cliente.');
      console.error('Error deleting cliente:', error);
    }
  }, [refresh]);

  // Lógica de filtrado (se ejecuta cada vez que cambian los clientes o los filtros)
  const filteredClientes = useMemo(() => {
    return allClientes.filter((cliente) => {
      // Filtrar por empresa seleccionada
      if (empresaFiltro) {
        const pertenece = cliente.empresas?.some((e) => e.id === empresaFiltro);
        if (!pertenece) return false;
      }
      // Filtrar por RFC
      if (rfcFiltro && !cliente.rfc.toLowerCase().includes(rfcFiltro.toLowerCase())) {
        return false;
      }
      // Filtrar por nombre comercial
      if (
        nombreFiltro &&
        !cliente.nombre_comercial.toLowerCase().includes(nombreFiltro.toLowerCase())
      ) {
        return false;
      }
      return true;
    });
  }, [allClientes, empresaFiltro, rfcFiltro, nombreFiltro]);

  const clearFilters = useCallback(() => {
    setEmpresaFiltro(null);
    setRfcFiltro('');
    setNombreFiltro('');
  }, []);

  return {
    clientes: filteredClientes, // Devolvemos los clientes ya filtrados
    loading,
    refresh,
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