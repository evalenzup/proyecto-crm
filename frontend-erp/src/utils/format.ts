// frontend-erp/src/utils/format.ts

/**
 * Formatea un número como una cadena de moneda en formato USD.
 * @param value El número a formatear.
 * @returns Una cadena con el formato de moneda (ej. "$1,234.56").
 */
export const formatCurrency = (value: number | string): string => {
  const numericValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numericValue)) {
    return '$0.00';
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(numericValue);
};
