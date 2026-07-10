// src/utils/sorters.ts
// Helpers de ordenamiento para columnas de tablas (antd).

/**
 * Comparador "natural" para cadenas alfanuméricas: ordena C-1, C-2, C-10
 * (no C-1, C-10, C-2). Los valores vacíos van al final.
 */
export function natCompare(a?: string | number | null, b?: string | number | null): number {
  const sa = a == null ? '' : String(a);
  const sb = b == null ? '' : String(b);
  if (!sa && !sb) return 0;
  if (!sa) return 1;
  if (!sb) return -1;
  return sa.localeCompare(sb, 'es', { numeric: true, sensitivity: 'base' });
}

/** Comparador numérico (trata null/undefined/'' como el menor). */
export function numCompare(a?: number | string | null, b?: number | string | null): number {
  const na = a == null || a === '' ? -Infinity : Number(a);
  const nb = b == null || b === '' ? -Infinity : Number(b);
  return na - nb;
}

/** Comparador de fechas ISO/parseables (null va al final). */
export function dateCompare(a?: string | null, b?: string | null): number {
  const ta = a ? new Date(a).getTime() : NaN;
  const tb = b ? new Date(b).getTime() : NaN;
  if (isNaN(ta) && isNaN(tb)) return 0;
  if (isNaN(ta)) return 1;
  if (isNaN(tb)) return -1;
  return ta - tb;
}

/** Comparador booleano (true primero al ascender). */
export function boolCompare(a?: boolean | null, b?: boolean | null): number {
  return (a ? 1 : 0) - (b ? 1 : 0);
}

// ── Ordenamiento en servidor (tablas paginadas) ─────────────────────────────

export interface ServerSort {
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

/**
 * Traduce el objeto `sorter` del onChange de una <Table> antd a los parámetros
 * `order_by` / `order_dir` que espera el backend. Si el usuario quita el orden,
 * devuelve `fallback` (para mantener un orden por defecto estable).
 *
 * Usa `columnKey` (o `field`) de la columna como `order_by`, así que la `key`
 * de cada columna ordenable debe coincidir con el valor que acepta el backend.
 */
export function parseAntdSorter(sorter: any, fallback: ServerSort = {}): ServerSort {
  const s = Array.isArray(sorter) ? sorter[0] : sorter;
  if (!s || !s.order) return fallback;
  const key = (s.columnKey ?? s.field) as string | undefined;
  if (!key) return fallback;
  return { order_by: String(key), order_dir: s.order === 'ascend' ? 'asc' : 'desc' };
}
