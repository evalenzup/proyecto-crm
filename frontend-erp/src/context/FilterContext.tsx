
import React, { createContext, useContext, useState, ReactNode } from 'react';

// Interfaces for each module's filter state
interface ClienteFilters {
    rfc: string;
    nombre: string;
}

interface ProductoFilters {
    searchTerm: string;
}

interface FacturaFilters {
    clienteId?: string;
    clienteQuery: string;
    estatus?: string; // 'BORRADOR' | 'TIMBRADA' | 'CANCELADA'
    estatusPago?: string; // 'PAGADA' | 'NO_PAGADA'
    fechaInicio?: string; // YYYY-MM-DD
    fechaFin?: string;    // YYYY-MM-DD
    folio: string;
}

interface PagoFilters {
    clienteId?: string;
    clienteQuery: string;
    estatus?: string; // e.g. 'VIGENTE' | 'CANCELADO'
    fechaInicio?: string;
    fechaFin?: string;
}

interface EgresoFilters {
    proveedor?: string;
    categoria?: string;
    estatus?: string;
    fechaInicio?: string;
    fechaFin?: string;
}

interface FilterContextType {
    clientes: ClienteFilters;
    setClientes: React.Dispatch<React.SetStateAction<ClienteFilters>>;

    productos: ProductoFilters;
    setProductos: React.Dispatch<React.SetStateAction<ProductoFilters>>;

    facturas: FacturaFilters;
    setFacturas: React.Dispatch<React.SetStateAction<FacturaFilters>>;

    pagos: PagoFilters;
    setPagos: React.Dispatch<React.SetStateAction<PagoFilters>>;

    egresos: EgresoFilters;
    setEgresos: React.Dispatch<React.SetStateAction<EgresoFilters>>;

    clearAllFilters: () => void;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export const FilterProvider = ({ children }: { children: ReactNode }) => {
    // Initial States
    const initialClientes: ClienteFilters = { rfc: '', nombre: '' };
    const initialProductos: ProductoFilters = { searchTerm: '' };
    const initialFacturas: FacturaFilters = { folio: '', clienteQuery: '' };
    const initialPagos: PagoFilters = { clienteQuery: '' };
    const initialEgresos: EgresoFilters = {};

    const [clientes, setClientes] = useState<ClienteFilters>(initialClientes);
    const [productos, setProductos] = useState<ProductoFilters>(initialProductos);
    const [facturas, setFacturas] = useState<FacturaFilters>(initialFacturas);
    const [pagos, setPagos] = useState<PagoFilters>(initialPagos);
    const [egresos, setEgresos] = useState<EgresoFilters>(initialEgresos);

    const clearAllFilters = React.useCallback(() => {
        setClientes(initialClientes);
        setProductos(initialProductos);
        setFacturas(initialFacturas);
        setPagos(initialPagos);
        setEgresos(initialEgresos);
    }, []);

    const contextValue = React.useMemo(() => ({
        clientes, setClientes,
        productos, setProductos,
        facturas, setFacturas,
        pagos, setPagos,
        egresos, setEgresos,
        clearAllFilters,
    }), [clientes, productos, facturas, pagos, egresos, clearAllFilters]);

    return (
        <FilterContext.Provider value={contextValue}>
            {children}
        </FilterContext.Provider>
    );
};

export const useFilterContext = () => {
    const context = useContext(FilterContext);
    if (!context) {
        throw new Error('useFilterContext must be used within a FilterProvider');
    }
    return context;
};
