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
  schema: JSONSchema;
  existingClientCandidate: ClienteOut | null;
  confirmAssignment: () => Promise<void>;
  cancelAssignment: () => void;
  lockedEmpresaIds: string[];
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

  const [lockedEmpresaIds, setLockedEmpresaIds] = useState<string[]>([]);

  // Función auxiliar para mezclar opciones y detectar bloqueados
  const mergeEmpresas = (accessibleOpts: { value: string; label: string }[], clienteEmpresas: { id: string; nombre_comercial: string }[]) => {
    const accessibleSet = new Set(accessibleOpts.map(o => o.value));
    const extraOpts: { value: string; label: string }[] = [];
    const lockedIds: string[] = [];

    clienteEmpresas.forEach(emp => {
      if (!accessibleSet.has(emp.id)) {
        extraOpts.push({ value: emp.id, label: emp.nombre_comercial });
        lockedIds.push(emp.id);
      }
    });

    return {
      mergedOptions: [...accessibleOpts, ...extraOpts],
      locked: lockedIds
    };
  };

  // Cargar datos (Unificado para evitar condiciones de carrera)
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [empresasData, schemaData] = await Promise.all([
          empresaService.getEmpresas(),
          clienteService.getClienteSchema()
        ]);

        const accessibleOpts = empresasData.map(emp => ({ value: emp.id, label: emp.nombre_comercial }));
        setSchema(schemaData);

        if (id) {
          setLoadingRecord(true);
          try {
            const clienteData = await clienteService.getCliente(id);
            const { mergedOptions, locked } = mergeEmpresas(accessibleOpts, clienteData.empresas || []);

            setEmpresasOptions(mergedOptions);
            setLockedEmpresaIds(locked);

            const initial: ClienteFormData = {
              ...clienteData,
              empresa_id: clienteData.empresas?.map(e => e.id) || [],
            };
            form.setFieldsValue(initial);
            setMetadata({ creado_en: clienteData.creado_en, actualizado_en: clienteData.actualizado_en });
          } catch (e) {
            message.error(normalizeHttpError(e) || 'Registro no encontrado');
            router.replace('/clientes');
          } finally {
            setLoadingRecord(false);
          }
        } else {
          setEmpresasOptions(accessibleOpts);
          // Si estamos creando (no id) y solo hay una empresa disponible, seleccionarla por defecto
          if (accessibleOpts.length === 1) {
            form.setFieldValue('empresa_id', [accessibleOpts[0].value]);
          }
        }
      } catch (e) {
        message.error(normalizeHttpError(e));
      } finally {
        setLoadingEmpresas(false);
        setLoadingSchema(false);
      }
    };

    fetchData();
  }, [id, form, router]);

  const [existingClientCandidate, setExistingClientCandidate] = useState<ClienteOut | null>(null);

  // Manejo del envío del formulario
  const onFinish = async (values: any) => { // Cambiado a any para incluir contactos
    try {
      // 1. Separar contactos de los datos del cliente
      const { contactos, ...clienteData } = values;

      // Si NO estamos editando (id vacío), verificar existencia antes de crear
      if (!id) {
        const potentialMatch = await clienteService.checkExistingClient(clienteData.rfc, clienteData.nombre_comercial);
        if (potentialMatch) {
          // DETENER FLUJO y retornar candidato para que la UI muestre el modal
          setExistingClientCandidate(potentialMatch);
          return;
        }
      }

      await executeSave(values);
    } catch (err: any) {
      applyFormErrors(err, form);
      message.error(normalizeHttpError(err));
    }
  };

  const executeSave = async (values: any, forceClientId?: string) => {
    const { contactos, ...clienteData } = values;
    const payload: ClienteCreate | ClienteUpdate = {
      ...clienteData,
      empresa_id: clienteData.empresa_id || [],
    };

    let clienteId = id || forceClientId;

    if (id) {
      await clienteService.updateCliente(id, payload as ClienteUpdate);
      message.success('Cliente actualizado');
    } else if (forceClientId) {
      // Asignación de empresas a cliente existente (USAR ENDPOINT DE VINCULACIÓN)
      await clienteService.linkCliente(forceClientId, payload.empresa_id || []);
      message.success('Cliente existente asignado a esta empresa');
    } else {
      const nuevoCliente = await clienteService.createCliente(payload as ClienteCreate);
      clienteId = nuevoCliente.id;
      message.success('Cliente creado');
    }

    if (!clienteId) {
      throw new Error('No se pudo obtener el ID del cliente.');
    }

    // 3. Obtener y eliminar contactos antiguos (Solo si es edición o asignación completa, 
    // pero en asignación NO deberíamos borrar contactos de otras empresas... 
    // El requerimiento dice "hacer la asignacion de ese cliente a la otra empresa". 
    // Asumiremos que contactos se mantienen o se agregan. Por simplicidad en asignación, no tocamos contactos antiguos, solo nuevos.)

    if (id) {
      // Solo limpiar contactos si estamos editando explícitamente el registro
      const contactosAntiguos = await getContactosByCliente(clienteId);
      for (const contacto of contactosAntiguos) {
        await deleteContacto(contacto.id);
      }
    }

    // 4. Crear los contactos del formulario
    if (contactos && Array.isArray(contactos)) {
      for (const contacto of contactos) {
        if (contacto) {
          await createContacto(clienteId, contacto);
        }
      }
    }

    router.push('/clientes');
  };

  const confirmAssignment = async () => {
    if (!existingClientCandidate) return;
    const values = form.getFieldsValue();
    try {
      await executeSave(values, existingClientCandidate.id);
    } catch (err: any) {
      message.error(normalizeHttpError(err));
    }
  };

  const cancelAssignment = () => {
    setExistingClientCandidate(null);
  };

  return {
    form,
    loading: loadingRecord || loadingEmpresas || loadingSchema,
    metadata,
    empresasOptions,
    onFinish,
    schema,
    existingClientCandidate,
    confirmAssignment,
    cancelAssignment,
    lockedEmpresaIds,
  };
};