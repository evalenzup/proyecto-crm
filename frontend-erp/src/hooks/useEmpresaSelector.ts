import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { empresaService, EmpresaOut } from '@/services/empresaService';

export const useEmpresaSelector = () => {
    const { user } = useAuth();
    const [selectedEmpresaId, setSelectedEmpresaId] = useState<string | undefined>(undefined);
    const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
    const [loadingEmpresas, setLoadingEmpresas] = useState(false);

    const isAdmin = user?.rol === 'admin';
    // Si es supervisor, la empresa asignada es la del usuario
    const supervisorEmpresaId = !isAdmin && user?.empresa_id ? user.empresa_id : undefined;

    useEffect(() => {
        const fetchEmpresas = async () => {
            if (isAdmin) {
                setLoadingEmpresas(true);
                try {
                    const data = await empresaService.getEmpresas();
                    setEmpresas(data);
                    // Seleccionar la primera por defecto si no hay ninguna seleccionada
                    if (data.length > 0 && !selectedEmpresaId) {
                        setSelectedEmpresaId(data[0].id);
                    }
                } catch (error) {
                    console.error("Error cargando empresas:", error);
                } finally {
                    setLoadingEmpresas(false);
                }
            } else if (supervisorEmpresaId) {
                // Si es supervisor, setear su empresa directamente
                setSelectedEmpresaId(supervisorEmpresaId);
                // También necesitamos cargar la info de esta empresa para que el Select muestre el nombre
                // y no el UUID, ya que options={} estaría vacío
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
    }, [isAdmin, supervisorEmpresaId, user]); // Dependencias clave

    return {
        selectedEmpresaId,
        setSelectedEmpresaId,
        empresas,
        loadingEmpresas,
        isAdmin,
    };
};
