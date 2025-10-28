// frontend-erp/src/hooks/useClienteForm.ts
import { useEffect, useState } from 'react';
import { message, Form } from 'antd';
import { clienteService, ClienteOut, ClienteCreate, ClienteUpdate } from '../services/clienteService';
import { empresaService } from '../services/empresaService'; // Para obtener las empresas para el select
import { getContactosByCliente, createContacto, deleteContacto } from '../services/contactoService'; // IMPORTAR SERVICIOS DE CONTACTO
import { useRouter } from 'next/router';
import { normalizeHttpError } from '@/utils/httpError';
import { applyFormErrors } from '@/utils/formErrors';

interface ClienteFormData {
  id?: string;
  nombre_comercial: string;
  nombre_razon_social: string;
  rfc: string;
  regimen_fiscal: string;
  codigo_postal: string;
  telefono?: string[];
  email?: string[];
  dias_credito?: number;
  dias_recepcion?: number;
  dias_pago?: number;
  tamano?: 'CHICO' | 'MEDIANO' | 'GRANDE';
  actividad?: 'RESIDENCIAL' | 'COMERCIAL' | 'INDUSTRIAL';
  empresa_id: string[];
}

interface JSONSchema { properties: Record<string, any>; required?: string[]; } // Definir JSONSchema aquí

interface UseClienteFormResult {
  form: any; // Ant Design Form instance
  loading: boolean;
  metadata: { creado_en: string; actualizado_en: string } | null;
  empresasOptions: { value: string; label: string }[];
  onFinish: (values: ClienteFormData) => Promise<void>;
  schema: JSONSchema; // Ahora el hook expone el schema
}

export const useClienteForm = (id?: string): UseClienteFormResult => {
  const [form] = Form.useForm();
  const router = useRouter();

  const [loadingRecord, setLoadingRecord] = useState(false);
  const [loadingEmpresas, setLoadingEmpresas] = useState(true);
  const [loadingSchema, setLoadingSchema] = useState(true); // Nuevo estado para el schema
  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);
  const [empresasOptions, setEmpresasOptions] = useState<{ value: string; label: string }[]>([]);
  const [schema, setSchema] = useState<JSONSchema>({ properties: {}, required: [] }); // Nuevo estado para el schema

  // Cargar opciones de empresas y esquema
  useEffect(() => {
    Promise.all([
      empresaService.getEmpresas(),
      clienteService.getClienteSchema() // Cargar el schema
    ])
      .then(([empresasData, schemaData]) => {
        setEmpresasOptions(empresasData.map(emp => ({ value: emp.id, label: emp.nombre_comercial })));
        setSchema(schemaData);
      })
      .catch((e) => message.error(normalizeHttpError(e)))
      .finally(() => {
        setLoadingEmpresas(false);
        setLoadingSchema(false);
      });
  }, []);

  // Cargar datos del registro si es edición
  useEffect(() => {
    if (!id) return;
    setLoadingRecord(true);
    clienteService.getCliente(id)
      .then((data: ClienteOut) => {
        const initial: ClienteFormData = {
          ...data,
          empresa_id: data.empresas?.map(e => e.id) || [], // Mapear a IDs para el formulario
        };
        form.setFieldsValue(initial);
        setMetadata({ creado_en: data.creado_en, actualizado_en: data.actualizado_en });
      })
      .catch((e) => {
        message.error(normalizeHttpError(e) || 'Registro no encontrado');
        router.replace('/clientes'); // Redirigir si no se encuentra el registro
      })
      .finally(() => setLoadingRecord(false));
  }, [id, form, router]);

  // Manejo del envío del formulario
  const onFinish = async (values: any) => { // Cambiado a any para incluir contactos
    try {
      // 1. Separar contactos de los datos del cliente
      const { contactos, ...clienteData } = values;

      const payload: ClienteCreate | ClienteUpdate = {
        ...clienteData,
        empresa_id: clienteData.empresa_id || [],
      };

      let clienteId = id;

      // 2. Guardar el cliente y obtener su ID
      if (id) {
        await clienteService.updateCliente(id, payload as ClienteUpdate);
        message.success('Cliente actualizado');
      } else {
        const nuevoCliente = await clienteService.createCliente(payload as ClienteCreate);
        clienteId = nuevoCliente.id; // Guardamos el ID del nuevo cliente
        message.success('Cliente creado');
      }

      if (!clienteId) {
        throw new Error('No se pudo obtener el ID del cliente.');
      }

      // 3. Obtener y eliminar contactos antiguos
      const contactosAntiguos = await getContactosByCliente(clienteId);
      for (const contacto of contactosAntiguos) {
        await deleteContacto(contacto.id);
      }

      // 4. Crear los nuevos contactos
      if (contactos && Array.isArray(contactos)) {
        for (const contacto of contactos) {
          if (contacto) { // Asegurarse de que el contacto no sea nulo/undefined
            await createContacto(clienteId, contacto);
          }
        }
      }

      router.push('/clientes'); // Redirigir al listado
    } catch (err: any) {
      // Marcar errores de validación en el formulario y mostrar mensaje amigable
      applyFormErrors(err, form);
      message.error(normalizeHttpError(err));
    }
  };

  return {
    form,
    loading: loadingRecord || loadingEmpresas || loadingSchema,
    metadata,
    empresasOptions,
    onFinish,
    schema, // Exponemos el schema
  };
};