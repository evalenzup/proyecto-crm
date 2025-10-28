// src/utils/formErrors.ts
import type { FormInstance } from 'antd';

// Traducciones básicas para mensajes comunes
const msgMap: Record<string, string> = {
  'Field required': 'Campo requerido',
  'Input should be a valid email address': 'Correo electrónico no válido',
  'value is not a valid email address': 'Correo electrónico no válido',
  'None is not an allowed value': 'Valor requerido',
  'value is not a valid integer': 'Valor numérico inválido',
  'value is not a valid boolean': 'Valor booleano inválido',
  'Type error': 'Tipo de dato inválido',
};

function translate(msg: string): string {
  if (!msg) return 'Error de validación';
  if (msgMap[msg]) return msgMap[msg];
  const found = Object.keys(msgMap).find((k) => msg.toLowerCase().includes(k.toLowerCase()));
  return found ? msgMap[found] : msg;
}

function getFieldFromLoc(loc: any): (string | number)[] {
  if (!Array.isArray(loc)) return [];
  // Regla: ignorar los primeros scopes (body, query, path) y tomar el resto
  const parts = loc.filter((x: any) => typeof x === 'string' || typeof x === 'number');
  const withoutScopes = parts.filter((p: any) => !['body', 'query', 'path'].includes(String(p)));
  return withoutScopes.length ? withoutScopes : parts.slice(-1);
}

export function applyFormErrors(error: any, form: FormInstance) {
  const status = error?.response?.status;
  const detail = error?.response?.data?.detail;
  if (status !== 422 || !Array.isArray(detail)) return; // Solo manejamos validaciones típicas FastAPI

  const fields = detail
    .map((d: any) => {
      const name = getFieldFromLoc(d?.loc);
      const msg = translate(d?.msg || 'Error en el formulario');
      if (!name || name.length === 0) return null;
      return { name, errors: [msg] } as { name: any; errors: string[] };
    })
    .filter(Boolean);

  if (fields.length) {
    form.setFields(fields as any);
  }
}
