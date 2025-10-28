
import api from '../lib/axios';
import { type Contacto } from '@/types/interfaces'; // Asumiremos que esta interfaz existe

// Obtener todos los contactos de un cliente específico
export const getContactosByCliente = async (clienteId: string): Promise<Contacto[]> => {
  const response = await api.get<Contacto[]>(`/clientes/${clienteId}/contactos`);
  return response.data;
};

// Crear un nuevo contacto para un cliente
export const createContacto = async (clienteId: string, contactoData: Partial<Contacto>): Promise<Contacto> => {
  const response = await api.post<Contacto>(`/clientes/${clienteId}/contactos`, contactoData);
  return response.data;
};

// Actualizar un contacto existente
export const updateContacto = async (contactoId: string, contactoData: Partial<Contacto>): Promise<Contacto> => {
  const response = await api.put<Contacto>(`/contactos/${contactoId}`, contactoData);
  return response.data;
};

// Eliminar un contacto
export const deleteContacto = async (contactoId: string): Promise<void> => {
  await api.delete(`/contactos/${contactoId}`);
};
