/**
 * Utilidades de formato de fecha/hora.
 *
 * El backend devuelve ISO 8601 con offset de Tijuana (ej. "2024-01-15T10:30:00-08:00").
 * Si por algún motivo llega un string sin timezone (legacy/naive), se asume UTC.
 */

const LOCALE = 'es-MX';
const TIMEZONE = 'America/Tijuana';

/** Detecta si un string ISO ya contiene información de timezone (Z, +HH:MM o -HH:MM). */
const hasTimezone = (iso: string): boolean =>
  iso.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(iso);

/**
 * Parsea un string ISO 8601 a Date, asumiendo UTC si no tiene timezone.
 * Esto evita que el navegador interprete naive datetimes como hora local.
 */
const parseISO = (iso: string): Date => {
  const normalized = hasTimezone(iso) ? iso : `${iso}Z`;
  return new Date(normalized);
};

/**
 * Formatea fecha + hora en zona horaria de Tijuana.
 * Ejemplo: "15/01/2024 10:30:00"
 */
export const formatDate = (iso: string | null | undefined): string => {
  if (!iso) return '-';
  return parseISO(iso).toLocaleString(LOCALE, {
    timeZone: TIMEZONE,
    dateStyle: 'short',
    timeStyle: 'medium',
  });
};

/**
 * Formatea solo la fecha (sin hora) en zona horaria de Tijuana.
 * Ejemplo: "15/01/2024"
 * Usar en columnas de tabla donde la hora no es relevante.
 */
export const formatDateOnly = (iso: string | null | undefined): string => {
  if (!iso) return '-';
  return parseISO(iso).toLocaleDateString(LOCALE, {
    timeZone: TIMEZONE,
    dateStyle: 'short',
  });
};

/**
 * Normaliza un string ISO 8601 para que dayjs lo interprete como UTC.
 * Si el string ya tiene timezone (Z, +HH:MM, -HH:MM) lo deja intacto.
 * Si es naive (sin timezone) le agrega 'Z' para que dayjs no lo trate como hora local.
 *
 * Usar antes de pasar strings del API a dayjs() en formularios.
 * Sin esto, "2026-03-20T09:15:35" sería interpretado como 09:15 hora de Tijuana
 * en lugar de 09:15 UTC → la fecha se corrompería al guardar.
 */
export const normalizeISOToUTC = (iso: string | null | undefined): string | null => {
  if (!iso) return null;
  return hasTimezone(iso) ? iso : `${iso}Z`;
};
