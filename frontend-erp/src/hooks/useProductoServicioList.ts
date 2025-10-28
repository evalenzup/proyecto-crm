import { useEffect, useState, useCallback } from 'react';
import { message } from 'antd';
import { productoServicioService, ProductoServicioOut } from '../services/productoServicioService';
import { empresaService, EmpresaOut } from '../services/empresaService';
import api from '../lib/axios';

interface UseProductoServicioListResult {
  productosServicios: ProductoServicioOut[];
  loading: boolean;
  total: number;
  currentPage: number;
  pageSize: number;
  handlePageChange: (page: number, size?: number) => void;
  handleDelete: (id: string) => Promise<void>;
  empresasForFilter: EmpresaOut[];
  empresaFiltro: string | null;
  setEmpresaFiltro: (id: string | null) => void;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  clearFilters: () => void;
  mapaClaves: Record<string, string>;
}

export const useProductoServicioList = (): UseProductoServicioListResult => {
  const [productosServicios, setProductosServicios] = useState<ProductoServicioOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const [empresasForFilter, setEmpresasForFilter] = useState<EmpresaOut[]>([]);
  const [mapaClaves, setMapaClaves] = useState<Record<string, string>>({});

  // Filter states
  const [empresaFiltro, setEmpresaFiltro] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearchTerm(searchTerm), 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

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
      message.warning('No se pudo obtener descripción de claves SAT.');
    }
    setMapaClaves(mapa);
  }, []);

  const fetchProductosServicios = useCallback(async () => {
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
      await fetchDescripciones(data.items);
    } catch (error) {
      message.error('Error al cargar productos y servicios.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, empresaFiltro, debouncedSearchTerm, fetchDescripciones]);

  const fetchEmpresasForFilter = useCallback(async () => {
    try {
      const data = await empresaService.getEmpresas();
      setEmpresasForFilter(data);
    } catch (error) {
      message.error('Error al cargar empresas para el filtro.');
    }
  }, []);

  useEffect(() => {
    fetchProductosServicios();
  }, [fetchProductosServicios]);

  useEffect(() => {
    fetchEmpresasForFilter();
  }, [fetchEmpresasForFilter]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await productoServicioService.deleteProductoServicio(id);
      message.success('Producto/Servicio eliminado correctamente.');
      fetchProductosServicios();
    } catch (error) {
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
    setEmpresaFiltro(null);
    setSearchTerm('');
  }, []);

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
    setEmpresaFiltro,
    searchTerm,
    setSearchTerm,
    clearFilters,
    mapaClaves,
  };
};