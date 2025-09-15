// frontend-erp/src/hooks/useProductoServicioList.ts
import { useEffect, useState, useCallback, useMemo } from 'react';
import { message } from 'antd';
import { productoServicioService, ProductoServicioOut } from '../services/productoServicioService';
import { empresaService, EmpresaOut } from '../services/empresaService';
import api from '../lib/axios'; // Necesario para las llamadas a /catalogos

interface UseProductoServicioListResult {
  productosServicios: ProductoServicioOut[];
  loading: boolean;
  refresh: () => void;
  handleDelete: (id: string) => Promise<void>;
  empresasForFilter: EmpresaOut[];
  empresaFiltro: string | null;
  setEmpresaFiltro: (id: string | null) => void;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  clearFilters: () => void;
  mapaClaves: Record<string, string>; // Añadido para las descripciones de catálogos
}

export const useProductoServicioList = (): UseProductoServicioListResult => {
  const [allProductosServicios, setAllProductosServicios] = useState<ProductoServicioOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [empresasForFilter, setEmpresasForFilter] = useState<EmpresaOut[]>([]);
  const [mapaClaves, setMapaClaves] = useState<Record<string, string>>({}); // Estado para las descripciones de catálogos

  // Estados para los filtros
  const [empresaFiltro, setEmpresaFiltro] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const fetchDescripciones = useCallback(async (items: ProductoServicioOut[]) => {
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
      console.error('Error fetching SAT descriptions:', error);
    }
    setMapaClaves(mapa);
  }, []);

  const fetchProductosServicios = useCallback(async () => {
    setLoading(true);
    try {
      let data: ProductoServicioOut[];
      if (searchTerm || empresaFiltro) {
        data = await productoServicioService.buscarProductoServicios(searchTerm, empresaFiltro);
      } else {
        data = await productoServicioService.getProductoServicios();
      }
      setAllProductosServicios(data);
      await fetchDescripciones(data); // Cargar descripciones después de obtener los productos
    } catch (error) {
      message.error('Error al cargar productos y servicios.');
      console.error('Error fetching productos/servicios:', error);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, empresaFiltro, fetchDescripciones]);

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
    fetchProductosServicios();
    fetchEmpresasForFilter();
  }, [fetchProductosServicios, fetchEmpresasForFilter]);

  const refresh = useCallback(() => {
    fetchProductosServicios();
  }, [fetchProductosServicios]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await productoServicioService.deleteProductoServicio(id);
      message.success('Producto/Servicio eliminado correctamente.');
      refresh();
    } catch (error) {
      message.error('Error al eliminar el producto/servicio.');
      console.error('Error deleting producto/servicio:', error);
    }
  }, [refresh]);

  const clearFilters = useCallback(() => {
    setEmpresaFiltro(null);
    setSearchTerm('');
  }, []);

  return {
    productosServicios: allProductosServicios,
    loading,
    refresh,
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