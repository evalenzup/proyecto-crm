// Shared hook: debounced server-side client search used by useFacturasList and usePagosList
import { useState, useMemo } from 'react';
import debounce from 'lodash/debounce';
import { searchClientes } from '@/services/facturaService';

interface Opcion { label: string; value: string }

export const useClienteSearch = (empresaId: string | undefined) => {
  const [clienteOptionsComercial, setClienteOptionsComercial] = useState<Opcion[]>([]);
  const [clienteOptionsFiscal, setClienteOptionsFiscal] = useState<Opcion[]>([]);

  const debouncedBuscarClientesComercial = useMemo(
    () =>
      debounce(async (q: string) => {
        if (!q || q.trim().length < 3) { setClienteOptionsComercial([]); return; }
        try {
          const list = await searchClientes(q, empresaId, 'comercial');
          setClienteOptionsComercial(
            (list || []).slice(0, 20).map((c: any) => ({
              value: c.id,
              label: `${c.nombre_comercial} (${c.nombre_razon_social})`,
            })),
          );
        } catch { setClienteOptionsComercial([]); }
      }, 300),
    [empresaId],
  );

  const debouncedBuscarClientesFiscal = useMemo(
    () =>
      debounce(async (q: string) => {
        if (!q || q.trim().length < 3) { setClienteOptionsFiscal([]); return; }
        try {
          const list = await searchClientes(q, empresaId, 'fiscal');
          setClienteOptionsFiscal(
            (list || []).slice(0, 20).map((c: any) => ({
              value: c.id,
              label: `${c.nombre_razon_social} (${c.nombre_comercial})`,
            })),
          );
        } catch { setClienteOptionsFiscal([]); }
      }, 300),
    [empresaId],
  );

  /** Populate options from a known clienteId (e.g., when loading a saved filter) */
  const syncClienteById = (clienteId: string | undefined) => {
    if (!clienteId) {
      setClienteOptionsComercial([]);
      setClienteOptionsFiscal([]);
      return;
    }
    import('@/services/facturaService')
      .then(({ getClienteById }) =>
        getClienteById(clienteId).then((c: any) => {
          if (c) {
            setClienteOptionsComercial([{ value: c.id, label: `${c.nombre_comercial} (${c.nombre_razon_social})` }]);
            setClienteOptionsFiscal([{ value: c.id, label: `${c.nombre_razon_social} (${c.nombre_comercial})` }]);
          }
        }).catch(() => { }),
      );
  };

  return {
    clienteOptionsComercial,
    setClienteOptionsComercial,
    clienteOptionsFiscal,
    setClienteOptionsFiscal,
    debouncedBuscarClientesComercial,
    debouncedBuscarClientesFiscal,
    syncClienteById,
  };
};
