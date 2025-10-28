// frontend-erp/src/hooks/useProductoServicioForm.ts
import { useEffect, useState } from 'react';
import { message, Form } from 'antd';
import { productoServicioService, ProductoServicioOut, ProductoServicioCreate, ProductoServicioUpdate, TipoProductoServicio } from '../services/productoServicioService';
import { empresaService, EmpresaOut } from '../services/empresaService'; // Para obtener las empresas para el select
import { useRouter } from 'next/router';
import api from '../lib/axios'; // Para los catálogos SAT
import { normalizeHttpError } from '@/utils/httpError';
import { applyFormErrors } from '@/utils/formErrors';

interface ProductoServicioFormData {
  id?: string;
  tipo: TipoProductoServicio;
  clave_producto: string;
  clave_unidad: string;
  descripcion: string;
  valor_unitario: number;
  empresa_id: string;
  cantidad?: number;
  stock_actual?: number;
  stock_minimo?: number;
  unidad_inventario?: string;
  ubicacion?: string;
  requiere_lote: boolean;
}

interface JSONSchema { properties: Record<string, any>; required?: string[]; }

interface UseProductoServicioFormResult {
  form: any; // Ant Design Form instance
  loading: boolean;
  metadata: { creado_en: string; actualizado_en: string } | null;
  empresasOptions: { value: string; label: string }[];
  onFinish: (values: ProductoServicioFormData) => Promise<void>;
  schema: JSONSchema;
  mapaClavesSat: Record<string, string>; // Para descripciones de claves SAT
  loadingSatCatalogs: boolean;
}

export const useProductoServicioForm = (id?: string): UseProductoServicioFormResult => {
  const [form] = Form.useForm();
  const router = useRouter();

  const [loadingRecord, setLoadingRecord] = useState(false);
  const [loadingEmpresas, setLoadingEmpresas] = useState(true);
  const [loadingSchema, setLoadingSchema] = useState(true);
  const [loadingSatCatalogs, setLoadingSatCatalogs] = useState(true);

  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);
  const [empresasOptions, setEmpresasOptions] = useState<{ value: string; label: string }[]>([]);
  const [schema, setSchema] = useState<JSONSchema>({ properties: {}, required: [] });
  const [mapaClavesSat, setMapaClavesSat] = useState<Record<string, string>>({});

  // Cargar opciones de empresas, esquema y catálogos SAT
  useEffect(() => {
    Promise.all([
      empresaService.getEmpresas(),
      productoServicioService.getProductoServicioSchema(),
      api.get('/catalogos/productos'), // Catálogo de productos SAT
      api.get('/catalogos/unidades'), // Catálogo de unidades SAT
    ])
      .then(([empresasData, schemaData, productosSatData, unidadesSatData]) => {
        setEmpresasOptions(empresasData.map(emp => ({ value: emp.id, label: emp.nombre_comercial })));
        
        // Inyectar opciones de catálogos SAT en el esquema
        const newSchema = { ...schemaData };
        if (newSchema.properties.clave_producto) {
          newSchema.properties.clave_producto['x-options'] = productosSatData.data.map((item: any) => ({
            value: item.clave,
            label: `${item.clave} - ${item.descripcion}`,
          }));
        }
        if (newSchema.properties.clave_unidad) {
          newSchema.properties.clave_unidad['x-options'] = unidadesSatData.data.map((item: any) => ({
            value: item.clave,
            label: `${item.clave} - ${item.descripcion}`,
          }));
        }
        setSchema(newSchema);

        const newMapaClavesSat: Record<string, string> = {};
        productosSatData.data.forEach((item: any) => { newMapaClavesSat[item.clave] = item.descripcion; });
        unidadesSatData.data.forEach((item: any) => { newMapaClavesSat[item.clave] = item.descripcion; });
        setMapaClavesSat(newMapaClavesSat);
      })
      .catch((e) => message.error(normalizeHttpError(e)))
      .finally(() => {
        setLoadingEmpresas(false);
        setLoadingSchema(false);
        setLoadingSatCatalogs(false);
      });
  }, []);

  // Cargar datos del registro si es edición
  useEffect(() => {
    if (!id) return;
    setLoadingRecord(true);
    productoServicioService.getProductoServicio(id)
      .then((data: ProductoServicioOut) => {
        const initial: ProductoServicioFormData = {
          ...data,
          valor_unitario: data.valor_unitario, // Asegurar que sea number
          cantidad: data.cantidad,
          stock_actual: data.stock_actual,
          stock_minimo: data.stock_minimo,
        };
        form.setFieldsValue(initial);
        setMetadata({ creado_en: data.creado_en, actualizado_en: data.actualizado_en });
      })
      .catch((e) => {
        message.error(normalizeHttpError(e) || 'Registro no encontrado');
        router.replace('/productos-servicios');
      })
      .finally(() => setLoadingRecord(false));
  }, [id, form, router]);

  // Manejo del envío del formulario
  const onFinish = async (values: ProductoServicioFormData) => {
    try {
      const payload: ProductoServicioCreate | ProductoServicioUpdate = {
        ...values,
        valor_unitario: Number(values.valor_unitario), // Asegurar que sea number
        cantidad: values.cantidad ? Number(values.cantidad) : undefined,
        stock_actual: values.stock_actual ? Number(values.stock_actual) : undefined,
        stock_minimo: values.stock_minimo ? Number(values.stock_minimo) : undefined,
      };

      if (id) {
        await productoServicioService.updateProductoServicio(id, payload as ProductoServicioUpdate);
        message.success('Producto/Servicio actualizado');
      } else {
        await productoServicioService.createProductoServicio(payload as ProductoServicioCreate);
        message.success('Producto/Servicio creado');
      }
      router.push('/productos-servicios');
    } catch (err: any) {
      applyFormErrors(err, form);
      message.error(normalizeHttpError(err));
    }
  };

  return {
    form,
    loading: loadingRecord || loadingEmpresas || loadingSchema || loadingSatCatalogs,
    metadata,
    empresasOptions,
    onFinish,
    schema,
    mapaClavesSat,
    loadingSatCatalogs,
  };
};
