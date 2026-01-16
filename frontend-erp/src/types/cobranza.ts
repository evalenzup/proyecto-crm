export interface CobranzaNota {
    id: string;
    empresa_id: string;
    cliente_id: string;
    nota: string;
    fecha_promesa_pago?: string; // ISO date string
    factura_id?: string;
    creado_po: string;
    creado_en: string;
    nombre_creador?: string;
}

export interface CobranzaNotaCreate {
    cliente_id: string;
    nota: string;
    fecha_promesa_pago?: string;
    factura_id?: string;
}

export interface AgingBucket {
    rango: string;
    monto: number;
    cantidad_facturas: number;
}

export interface ClienteAging {
    cliente_id: string;
    nombre_cliente: string;
    rfc?: string;
    total_deuda: number;
    por_vencer: number;
    vencido_0_30: number;
    vencido_31_60: number;
    vencido_61_90: number;
    vencido_mas_90: number;
    nota_mas_reciente?: string;
    fecha_promesa?: string; // ISO String
    email?: string;
}

export interface AgingReportResponse {
    total_general_vencido: number;
    items: ClienteAging[];
}
