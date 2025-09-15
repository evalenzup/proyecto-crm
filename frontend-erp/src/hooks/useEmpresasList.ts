// frontend-erp/src/hooks/useEmpresasList.ts
import { useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { empresaService, EmpresaOut } from '../services/empresaService';

interface UseEmpresasListResult {
  empresas: EmpresaOut[];
  loading: boolean;
  refresh: () => void;
  handleDelete: (id: string) => Promise<void>;
}

export const useEmpresasList = (): UseEmpresasListResult => {
  const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchEmpresas = useCallback(async () => {
    setLoading(true);
    try {
      const data = await empresaService.getEmpresas();
      setEmpresas(data);
    } catch (error) {
      message.error('Error al cargar las empresas.');
      console.error('Error fetching empresas:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEmpresas();
  }, [fetchEmpresas]);

  const refresh = useCallback(() => {
    fetchEmpresas();
  }, [fetchEmpresas]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await empresaService.deleteEmpresa(id);
      message.success('Empresa eliminada correctamente.');
      refresh(); // Recargar la lista después de eliminar
    } catch (error) {
      message.error('Error al eliminar la empresa.');
      console.error('Error deleting empresa:', error);
    }
  }, [refresh]);

  return {
    empresas,
    loading,
    refresh,
    handleDelete,
  };
};
