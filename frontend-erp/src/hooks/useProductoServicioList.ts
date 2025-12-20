import { useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { productoServicioService, ProductoServicioOut } from '../services/productoServicioService';
import { EmpresaOut } from '../services/empresaService';
import api from '../lib/axios';
import { useEmpresaSelector } from './useEmpresaSelector';
import { useFilterContext } from '@/context/FilterContext';

interface UseProductoServicioListResult {
  productosServicios: ProductoServicioOut[];
  loading: boolean;
  total: number;
  currentPage: number;
  pageSize: number;
  handlePageChange: (page: number, size?: number) => void;
  handleDelete: (id: string) => Promise<void>;
  empresasForFilter: EmpresaOut[];
  empresaFiltro: string | undefined;
  setEmpresaFiltro: (id: string | undefined) => void;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  clearFilters: () => void;
  mapaClaves: Record<string, string>;
  isAdmin: boolean;
}

export const useProductoServicioList = (): UseProductoServicioListResult => {
  const [productosServicios, setProductosServicios] = useState<ProductoServicioOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [mapaClaves, setMapaClaves] = useState<Record<string, string>>({});

  const {
    selectedEmpresaId: empresaFiltro,
    setSelectedEmpresaId: setEmpresaFiltro,
    empresas: empresasForFilter,
    isAdmin
  } = useEmpresaSelector();

  // Use Unified Filter Context
  const { productos: filterState, setProductos: setFilterState } = useFilterContext();
  const searchTerm = filterState.searchTerm;
  const setSearchTerm = useCallback((term: string) => setFilterState(prev => ({ ...prev, searchTerm: term })), [setFilterState]);

  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState(searchTerm);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearchTerm(searchTerm), 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Reset page logic
  useEffect(() => {
    setCurrentPage(1);
  }, [empresaFiltro, debouncedSearchTerm]);

  const fetchDescripciones = useCallback(async (items: ProductoServicioOut[]) => {
    if (items.length === 0) return;
    const clavesProd = [...new Set(items.map(i => i.clave_producto))];
    const clavesUni = [...new Set(items.map(i => i.clave_unidad))];
    const mapa: Record<string, string> = {};

    try {
      const [prodData, uniData] = await Promise.all([
        Promise.all(clavesProd.map(c => api.get(`/catalogos/descripcion/producto/${c}`))),
        Promise.all(clavesUni.map(c => api.get(`/catalogos/descripcion/unidad/${c}`))),
      ]);

      for (const res of prodData) {
        mapa[res.data.clave] = res.data.descripcion;
      }
      for (const res of uniData) {
        mapa[res.data.clave] = res.data.descripcion;
      }
    } catch (error) {
      // message.warning('No se pudo obtener descripción de claves SAT.');
      console.error("Error obteniendo descripciones SAT", error);
    }
    setMapaClaves(prev => ({ ...prev, ...mapa }));
  }, []);

  const fetchProductosServicios = useCallback(async () => {
    if (!empresaFiltro) {
      setProductosServicios([]);
      setTotal(0);
      return;
    }

    setLoading(true);
    try {
      const params = {
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
        empresa_id: empresaFiltro,
        q: debouncedSearchTerm,
      };
      const data = await productoServicioService.getProductoServicios(params);
      setProductosServicios(data.items);
      setTotal(data.total);

      // Asincrono para no bloquear UI
      fetchDescripciones(data.items);
    } catch (error) {
      console.error(error);
      message.error('Error al cargar productos y servicios.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, empresaFiltro, debouncedSearchTerm, fetchDescripciones]);

  useEffect(() => {
    fetchProductosServicios();
  }, [fetchProductosServicios]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await productoServicioService.deleteProductoServicio(id);
      message.success('Producto/Servicio eliminado correctamente.');
      fetchProductosServicios();
    } catch (error) {
      console.error(error);
      message.error('Error al eliminar el producto/servicio.');
    }
  }, [fetchProductosServicios]);

  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size && size !== pageSize) {
      setPageSize(size);
    }
  };

  const clearFilters = useCallback(() => {
    setFilterState(prev => ({ ...prev, searchTerm: '' }));
  }, [setFilterState]);

  return {
    productosServicios,
    loading,
    total,
    currentPage,
    pageSize,
    handlePageChange,
    handleDelete,
    empresasForFilter,
    empresaFiltro,
    setEmpresaFiltro, // Type fix
    searchTerm,
    setSearchTerm,
    clearFilters,
    mapaClaves,
    isAdmin
  };
};