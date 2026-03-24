import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { empresaService, EmpresaOut } from '@/services/empresaService';

interface EmpresaContextType {
    selectedEmpresaId: string | undefined;
    setSelectedEmpresaId: (id: string | undefined) => void;
    empresas: EmpresaOut[];
    loadingEmpresas: boolean;
    isAdmin: boolean;
}

const EmpresaContext = createContext<EmpresaContextType | undefined>(undefined);

export const EmpresaProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const { user } = useAuth();
    const [selectedEmpresaId, setSelectedEmpresaId] = useState<string | undefined>(undefined);

    const isAdmin = user?.rol === 'admin';
    const supervisorEmpresaId = !isAdmin && user?.empresa_id ? user.empresa_id : undefined;

    // Fetch lista de empresas (admin) — cacheado 5 min por el QueryClient global
    const { data: empresasAdmin = [], isLoading: loadingAdmin } = useQuery({
        queryKey: ['empresas'],
        queryFn: () => empresaService.getEmpresas(),
        enabled: !!user && isAdmin,
    });

    // Fetch empresa individual (supervisor) — cacheada 5 min
    const { data: empresaSupervisor, isLoading: loadingSupervisor } = useQuery({
        queryKey: ['empresa', supervisorEmpresaId],
        queryFn: () => empresaService.getEmpresa(supervisorEmpresaId!),
        enabled: !!user && !isAdmin && !!supervisorEmpresaId,
    });

    const empresas: EmpresaOut[] = isAdmin
        ? empresasAdmin
        : empresaSupervisor
        ? [empresaSupervisor]
        : [];

    const loadingEmpresas = isAdmin ? loadingAdmin : loadingSupervisor;

    // Auto-seleccionar empresa cuando cambia la lista o el usuario
    useEffect(() => {
        if (!user) {
            setSelectedEmpresaId(undefined);
            return;
        }

        if (!isAdmin && supervisorEmpresaId) {
            setSelectedEmpresaId(supervisorEmpresaId);
            return;
        }

        if (isAdmin && empresasAdmin.length > 0) {
            setSelectedEmpresaId(prev => {
                if (prev && empresasAdmin.find(e => e.id === prev)) return prev;
                return empresasAdmin[0].id;
            });
        }
    }, [isAdmin, supervisorEmpresaId, empresasAdmin, user]);

    return (
        <EmpresaContext.Provider value={{
            selectedEmpresaId,
            setSelectedEmpresaId,
            empresas,
            loadingEmpresas,
            isAdmin,
        }}>
            {children}
        </EmpresaContext.Provider>
    );
};

export const useEmpresaContext = () => {
    const context = useContext(EmpresaContext);
    if (context === undefined) {
        throw new Error('useEmpresaContext must be used within an EmpresaProvider');
    }
    return context;
};
