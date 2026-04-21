import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { empresaService, EmpresaOut, RfcGroup } from '@/services/empresaService';

const EMPRESA_STORAGE_KEY = 'ui.empresa.selected';

interface EmpresaContextType {
    selectedEmpresaId: string | undefined;
    setSelectedEmpresaId: (id: string | undefined) => void;
    empresas: EmpresaOut[];
    rfcGroups: RfcGroup[];         // grupos de empresas con RFC compartido (≥2 empresas)
    loadingEmpresas: boolean;
    isAdmin: boolean;   // true para superadmin y admin (con selector multi-empresa)
}

const EmpresaContext = createContext<EmpresaContextType | undefined>(undefined);

export const EmpresaProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const { user } = useAuth();

    // superadmin y admin tienen selector multi-empresa
    const isAdmin = user?.rol === 'superadmin' || user?.rol === 'admin';
    const supervisorEmpresaId = !isAdmin && user?.empresa_id ? user.empresa_id : undefined;

    const [selectedEmpresaId, setSelectedEmpresaIdState] = useState<string | undefined>(() => {
        if (typeof window !== 'undefined') {
            return localStorage.getItem(EMPRESA_STORAGE_KEY) || undefined;
        }
        return undefined;
    });

    const setSelectedEmpresaId = useCallback((id: string | undefined) => {
        setSelectedEmpresaIdState(id);
        if (typeof window !== 'undefined') {
            if (id) localStorage.setItem(EMPRESA_STORAGE_KEY, id);
            else localStorage.removeItem(EMPRESA_STORAGE_KEY);
        }
    }, []);

    // Admin/superadmin: el endpoint /empresas ya filtra por sus empresas asignadas
    const { data: empresasAdmin = [], isLoading: loadingAdmin } = useQuery({
        queryKey: ['empresas', user?.id],
        queryFn: () => empresaService.getEmpresas(),
        enabled: !!user && isAdmin,
    });

    // RFC groups (solo para admin/superadmin)
    const { data: rfcGroups = [] } = useQuery({
        queryKey: ['rfc-groups', user?.id],
        queryFn: () => empresaService.getRfcGroups(),
        enabled: !!user && isAdmin,
    });

    // Supervisor/estandar: carga su única empresa
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
            setSelectedEmpresaIdState(prev => {
                if (prev && empresasAdmin.find(e => e.id === prev)) return prev;
                const firstId = empresasAdmin[0].id;
                if (typeof window !== 'undefined') localStorage.setItem(EMPRESA_STORAGE_KEY, firstId);
                return firstId;
            });
        }
    }, [isAdmin, supervisorEmpresaId, empresasAdmin, user, setSelectedEmpresaId]);

    return (
        <EmpresaContext.Provider value={{
            selectedEmpresaId,
            setSelectedEmpresaId,
            empresas,
            rfcGroups,
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
