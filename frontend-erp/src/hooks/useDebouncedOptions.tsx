import { useState } from 'react';
import debounce from 'lodash/debounce';
import api from '@/lib/axios';

interface Option {
  label: string;
  value: string;
}

export function useDebouncedOptions(endpoint: string, delay = 300) {
  const [options, setOptions] = useState<Option[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = debounce(async (q: string) => {
    if (!q || q.length < 3) return;
    setLoading(true);
    try {
      const { data } = await api.get(endpoint, { params: { q } });
      const opts = data.map((item: any) => ({
        label: `${item.clave} — ${item.descripcion}`,
        value: item.clave,
      }));
      setOptions(opts);
    } catch {
      // Manejo de errores
    } finally {
      setLoading(false);
    }
  }, delay);

  return { options, loading, fetch };
}