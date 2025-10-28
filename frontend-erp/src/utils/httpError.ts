// src/utils/httpError.ts
import { AxiosError } from 'axios';

// Traducciones simples de mensajes comunes de Pydantic/FastAPI a español
const msgMap: Record<string, string> = {
  'Field required': 'Campo requerido',
  'value is not a valid email address': 'Correo electrónico no válido',
  'Input should be a valid email address': 'Correo electrónico no válido',
  'None is not an allowed value': 'Valor requerido',
  'value is not a valid integer': 'Valor numérico inválido',
  'value is not a valid boolean': 'Valor booleano inválido',
  'Type error': 'Tipo de dato inválido',
};

function translate(msg: string): string {
  // búsqueda exacta y por inclusión
  if (msgMap[msg]) return msgMap[msg];
  const found = Object.keys(msgMap).find((k) => msg.toLowerCase().includes(k.toLowerCase()));
  return found ? msgMap[found] : msg;
}

function formatLoc(loc: any): string {
  if (!Array.isArray(loc)) return '';
  // loc suele ser ["body","campo"] o ["query","q"] etc.
  const field = loc[loc.length - 1];
  if (typeof field === 'string') return field;
  return '';
}

function formatDetail(detail: any): string {
  // detail puede ser string | array | objeto
  if (!detail) return '';
  if (typeof detail === 'string') return translate(detail);

  // FastAPI ValidationError: array de objetos {loc,msg,type}
  if (Array.isArray(detail)) {
    const messages = detail.map((d) => {
      const field = formatLoc(d?.loc);
      const msg = translate(d?.msg || 'Error en el formulario');
      return field ? `${field}: ${msg}` : msg;
    });
    // dedup y join
    return Array.from(new Set(messages.filter(Boolean))).join('\n');
  }

  // Algunos endpoints devuelven {message: string}
  if (typeof detail === 'object') {
    if (typeof detail.message === 'string') return translate(detail.message);
  }

  try {
    return JSON.stringify(detail);
  } catch {
    return 'Error desconocido';
  }
}

export function normalizeHttpError(err: unknown): string {
  const fallback = 'Error en la comunicación con el servidor';

  // AxiosError
  const error = err as AxiosError<any>;
  const status = error?.response?.status;
  const data = error?.response?.data;

  // Si el backend devolvió un string (ej. XML SOAP), intentar extraer <faultstring>
  if (typeof data === 'string') {
    const m = data.match(/<faultstring>([\s\S]*?)<\/faultstring>/i);
    if (m && m[1]) {
      return m[1].trim();
    }
  }

  if (data?.detail) {
    const msg = formatDetail(data.detail);
    if (msg) return msg;
  }

  // Algunos errores se devuelven en data.message
  if (typeof data?.message === 'string') {
    return translate(data.message);
  }

  // Mensajes por status comunes
  if (status === 422) return 'Hay errores de validación en el formulario. Por favor revisa los campos marcados.';
  if (status === 404) return 'Recurso no encontrado.';
  if (status === 401) return 'No autorizado. Inicia sesión nuevamente.';
  if (status === 403) return 'No tienes permisos para realizar esta acción.';
  if (status === 400) return 'Solicitud inválida. Verifica la información ingresada.';
  if (status === 500) return 'Error interno del servidor. Intenta más tarde.';

  // Fallback por statusText o mensaje
  const byText = (error?.response as any)?.statusText || (error as any)?.message;
  return byText || fallback;
}
