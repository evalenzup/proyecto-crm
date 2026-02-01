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

  // Si el backend devolvió un string
  if (typeof data === 'string') {
    // 1. Intentar XML SOAP
    const m = data.match(/<faultstring>([\s\S]*?)<\/faultstring>/i);
    if (m && m[1]) {
      return m[1].trim();
    }
    // 2. Intentar parsear si parece JSON
    try {
      const parsed = JSON.parse(data);
      if (parsed && (parsed.detail || parsed.message)) {
        // Recursión o asignación manual
        const d = parsed.detail || parsed.message;
        const msg = formatDetail(d);
        if (msg) return msg;
      }
    } catch {
      // No es JSON, usar el string tal cual
      if (status === 400 && data.length < 2000) {
        return data;
      }
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
  // PRIORIDAD: Si no encontré detalle, uso mensajes genéricos.
  if (status === 422) return 'Hay errores de validación en el formulario.';
  if (status === 404) return 'Recurso no encontrado.';
  if (status === 401) return 'No autorizado. Inicia sesión nuevamente.';
  if (status === 403) return 'No tienes permisos para realizar esta acción.';

  // Modificado: Si es 400 y tenemos data, intentamos mostrarla
  if (status === 400) {
    // Si llegamos aqui y data es string (largo) o objeto sin detail/message
    if (data && typeof data === 'string') return data;
    if (data && typeof data === 'object') {
      // Intento final de formatear lo que haya
      const raw = formatDetail(data);
      if (raw && raw !== 'Error desconocido') return raw;
      return JSON.stringify(data);
    }
    return 'Solicitud inválida. Verifica la información ingresada.';
  }
  if (status === 500) return 'Error interno del servidor. Intenta más tarde.';

  // Fallback por statusText o mensaje
  const byText = (error?.response as any)?.statusText || (error as any)?.message;
  return byText || fallback;
}

export async function parseBlobError(err: any): Promise<string | null> {
  if (err?.response?.data instanceof Blob) {
    try {
      const text = await err.response.data.text();
      const json = JSON.parse(text);
      return normalizeHttpError({ response: { ...err.response, data: json } });
    } catch {
      return null;
    }
  }
  return normalizeHttpError(err);
}
