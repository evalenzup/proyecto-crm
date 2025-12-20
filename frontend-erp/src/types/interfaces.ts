export interface Contacto {
    id: string;
    cliente_id?: string;
    nombre: string;
    puesto?: string;
    email?: string;
    telefono?: string;
    tipo: 'PRINCIPAL' | 'ADMINISTRATIVO' | 'COBRANZA' | 'OPERATIVO' | 'OTRO';
    creado_en?: string;
    actualizado_en?: string;
}

// Add other interfaces here as needed
