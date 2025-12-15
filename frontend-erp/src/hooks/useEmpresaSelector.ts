import { useEmpresaContext } from '@/context/EmpresaContext';

export const useEmpresaSelector = () => {
    return useEmpresaContext();
};
