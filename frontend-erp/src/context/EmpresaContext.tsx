import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
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
    const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
    const [loadingEmpresas, setLoadingEmpresas] = useState(false);

    const isAdmin = user?.rol === 'admin';
    const supervisorEmpresaId = !isAdmin && user?.empresa_id ? user.empresa_id : undefined;

    useEffect(() => {
        // Reset state on user change/logout
        if (!user) {
            setEmpresas([]);
            setSelectedEmpresaId(undefined);
            return;
        }

        const fetchEmpresas = async () => {
            if (isAdmin) {
                setLoadingEmpresas(true);
                try {
                    const data = await empresaService.getEmpresas();
                    setEmpresas(data);
                    // Si no hay empresa seleccionada (o la seleccionada ya no existe), seleccionar la primera
                    if (data.length > 0) {
                        // Intentar mantener la seleccionada si existe en la nueva lista
                        setSelectedEmpresaId(prev => {
                            if (prev && data.find(e => e.id === prev)) return prev;
                            return data[0].id;
                        });
                    } else {
                        setSelectedEmpresaId(undefined);
                    }
                } catch (error) {
                    console.error("Error cargando empresas:", error);
                } finally {
                    setLoadingEmpresas(false);
                }
            } else if (supervisorEmpresaId) {
                setSelectedEmpresaId(supervisorEmpresaId);
                setLoadingEmpresas(true);
                try {
                    const empresa = await empresaService.getEmpresa(supervisorEmpresaId);
                    setEmpresas([empresa]);
                } catch (error) {
                    console.error("Error cargando empresa de supervisor:", error);
                } finally {
                    setLoadingEmpresas(false);
                }
            }
        };

        fetchEmpresas();
    }, [isAdmin, supervisorEmpresaId, user]);

    return (
        <EmpresaContext.Provider value={{
            selectedEmpresaId,
            setSelectedEmpresaId,
            empresas,
            loadingEmpresas,
            isAdmin
        }}>
            {children}
        </EmpresaContext.Provider>
    );
};

// Hook interno para usar el contexto directamente si se quisiera, 
// pero mantendremos useEmpresaSelector como la interfaz pública por compatibilidad.
export const useEmpresaContext = () => {
    const context = useContext(EmpresaContext);
    if (context === undefined) {
        throw new Error('useEmpresaContext must be used within an EmpresaProvider');
    }
    return context;
};
