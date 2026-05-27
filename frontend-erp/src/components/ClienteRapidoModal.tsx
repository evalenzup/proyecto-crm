// src/components/ClienteRapidoModal.tsx
/**
 * Modal para crear un cliente con datos mínimos desde el formulario de OS.
 *
 * Campos esenciales:
 *   - Nombre comercial (requerido)
 *   - RFC (default: XAXX010101000 — público en general)
 *   - Teléfono, Email (opcionales)
 *   - Código postal (requerido) → dispara lookup Nominatim → auto-fill ciudad/estado/coords
 *   - Calle (opcional)
 *   - Colonia, Ciudad, Estado → auto-rellenados desde Nominatim; editables
 *
 * Al guardar, llama onCreated({ id, nombre_comercial }) para que el padre
 * inyecte el cliente nuevo en su Select sin recargar la página.
 */
import React, { useState, useRef } from 'react';
import {
  Modal,
  Form,
  Input,
  Button,
  Row,
  Col,
  message,
  Spin,
  Tooltip,
} from 'antd';
import { EnvironmentOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { clienteService } from '@/services/clienteService';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';

// ── Tipos ─────────────────────────────────────────────────────────────────────

export interface ClienteCreado {
  id: string;
  nombre_comercial: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (cliente: ClienteCreado) => void;
}

// ── Constantes ────────────────────────────────────────────────────────────────

const RFC_GENERICO = 'XAXX010101000';
const REGIMEN_DEFAULT = '616'; // Sin obligaciones fiscales (público en general)
const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';
const USER_AGENT = 'proyecto-crm/1.0 (netov1@gmail.com)';

// ── Helper Nominatim ──────────────────────────────────────────────────────────

interface NominatimResult {
  ciudad: string | null;
  estado: string | null;
  colonia: string | null;
  lat: number | null;
  lon: number | null;
}

async function lookupCP(cp: string): Promise<NominatimResult> {
  const url = `${NOMINATIM_URL}?postalcode=${cp}&country=MX&format=json&addressdetails=1&limit=1`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);

  let res: Response;
  try {
    // Nota: User-Agent es un header restringido en browsers; se omite aquí
    res = await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) throw new Error(`Nominatim HTTP ${res.status}`);
  const data = await res.json();
  console.log('[Nominatim] CP lookup raw response:', JSON.stringify(data, null, 2));
  if (!data || data.length === 0) return { ciudad: null, estado: null, colonia: null, lat: null, lon: null };

  const item = data[0];
  const address = item.address ?? {};

  let ciudad: string =
    address.city ||
    address.town ||
    address.municipality ||
    address.village ||
    address.county ||
    '';

  // Nominatim a veces devuelve "Municipio de X" — limpiar
  if (ciudad.toLowerCase().startsWith('municipio de ')) {
    ciudad = ciudad.substring('municipio de '.length);
  }

  const estado: string = address.state ?? '';

  // Colonia: Nominatim la devuelve como suburb, neighbourhood o quarter (no siempre disponible)
  const colonia: string =
    address.suburb ||
    address.neighbourhood ||
    address.quarter ||
    '';

  return {
    ciudad: ciudad.trim() || null,
    estado: estado.trim() || null,
    colonia: colonia.trim() || null,
    lat: item.lat ? parseFloat(item.lat) : null,
    lon: item.lon ? parseFloat(item.lon) : null,
  };
}

// ── Componente ────────────────────────────────────────────────────────────────

const ClienteRapidoModal: React.FC<Props> = ({ open, onClose, onCreated }) => {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [buscandoCP, setBuscandoCP] = useState(false);
  const { selectedEmpresaId } = useEmpresaSelector();

  // Evita disparar el lookup si el CP ya fue procesado
  const lastCPRef = useRef<string>('');
  // Coordenadas obtenidas de Nominatim para mostrarlas como feedback visual
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);

  // ── Reset al abrir ─────────────────────────────────────────────────────────
  const handleAfterOpen = () => {
    form.resetFields();
    lastCPRef.current = '';
    setCoords(null);
  };

  // ── Lookup de CP via Nominatim ─────────────────────────────────────────────
  const handleCPChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const cp = e.target.value.replace(/\D/g, '').slice(0, 5);

    // Solo disparar cuando tengamos exactamente 5 dígitos y sea diferente al último
    if (cp.length !== 5 || cp === lastCPRef.current) return;
    lastCPRef.current = cp;

    setBuscandoCP(true);
    try {
      const result = await lookupCP(cp);
      if (result.ciudad || result.estado) {
        // Solo auto-llenar colonia si está vacía (no pisar lo que el usuario ya escribió)
        const coloniaActual = form.getFieldValue('serv_colonia');
        form.setFieldsValue({
          serv_ciudad:  result.ciudad  ?? form.getFieldValue('serv_ciudad'),
          serv_estado:  result.estado  ?? form.getFieldValue('serv_estado'),
          serv_colonia: coloniaActual || result.colonia || undefined,
          _latitud:     result.lat  ?? undefined,
          _longitud:    result.lon  ?? undefined,
        });
        if (result.lat && result.lon) {
          setCoords({ lat: result.lat, lon: result.lon });
        }
        message.success(`CP ${cp}: ${result.ciudad ?? '?'}, ${result.estado ?? '?'}`, 2);
      } else {
        message.warning(`No se encontró información para el CP ${cp}`, 3);
      }
    } catch (err: any) {
      const isTimeout = err?.name === 'AbortError';
      message.warning(
        isTimeout
          ? `Tiempo de espera agotado al consultar el CP ${cp}. Llena ciudad y estado manualmente.`
          : 'No se pudo consultar el código postal',
        4,
      );
    } finally {
      setBuscandoCP(false);
    }
  };

  // ── Guardar ────────────────────────────────────────────────────────────────
  const handleOk = async () => {
    let values: any;
    try {
      values = await form.validateFields();
    } catch {
      return; // Ant Design ya muestra los errores inline
    }

    setSaving(true);
    try {
      const telefonoRaw = (values.telefono ?? '').trim();
      const emailRaw = (values.email ?? '').trim();

      const payload: any = {
        nombre_comercial: values.nombre_comercial.trim(),
        nombre_razon_social: values.nombre_comercial.trim(), // igual al comercial por defecto
        rfc: (values.rfc ?? RFC_GENERICO).trim().toUpperCase(),
        regimen_fiscal: REGIMEN_DEFAULT,
        codigo_postal: (values.serv_codigo_postal ?? '00000').trim(),
        // Dirección de servicio
        serv_calle: values.serv_calle?.trim() || undefined,
        serv_colonia: values.serv_colonia?.trim() || undefined,
        serv_ciudad: values.serv_ciudad?.trim() || undefined,
        serv_estado: values.serv_estado?.trim() || undefined,
        serv_codigo_postal: values.serv_codigo_postal?.trim() || undefined,
        // Geolocalización del centroide del CP
        latitud: values._latitud ?? undefined,
        longitud: values._longitud ?? undefined,
        // Contacto
        telefono: telefonoRaw ? [telefonoRaw] : undefined,
        email: emailRaw ? [emailRaw] : undefined,
        // Empresa — el backend la asigna desde el usuario en sesión;
        // si el hook tiene empresa seleccionada, la enviamos explícitamente.
        empresa_id: selectedEmpresaId ? [selectedEmpresaId] : [],
      };

      const creado = await clienteService.createCliente(payload);
      message.success(`Cliente "${creado.nombre_comercial}" creado correctamente`);
      onCreated({ id: creado.id, nombre_comercial: creado.nombre_comercial });
      onClose();
    } catch (err: any) {
      if (!err?._handled) {
        const detail = err?.response?.data?.detail;
        message.error(
          Array.isArray(detail)
            ? detail.map((d: any) => d.msg ?? d).join(' | ')
            : detail ?? 'Error al crear el cliente',
        );
      }
    } finally {
      setSaving(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <Modal
      title="Nuevo cliente rápido"
      open={open}
      onCancel={onClose}
      afterOpenChange={(isOpen) => { if (isOpen) handleAfterOpen(); }}
      width={560}
      footer={[
        <Button key="cancel" onClick={onClose} disabled={saving}>
          Cancelar
        </Button>,
        <Button key="submit" type="primary" loading={saving} onClick={handleOk}>
          Crear cliente
        </Button>,
      ]}
      destroyOnClose
    >
      <Spin spinning={buscandoCP} tip="Consultando código postal…">
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>

          {/* ── Identificación ──────────────────────────────────────────── */}
          <Form.Item
            name="nombre_comercial"
            label="Nombre comercial"
            rules={[{ required: true, message: 'El nombre es obligatorio' }]}
          >
            <Input placeholder="Nombre del cliente o negocio" autoFocus />
          </Form.Item>

          <Row gutter={12}>
            <Col xs={24} sm={14}>
              <Form.Item
                name="rfc"
                label={
                  <span>
                    RFC&nbsp;
                    <Tooltip title="XAXX010101000 = Público en general (sin datos fiscales)">
                      <InfoCircleOutlined style={{ color: '#aaa', fontSize: 12 }} />
                    </Tooltip>
                  </span>
                }
                initialValue={RFC_GENERICO}
                rules={[{ required: true, message: 'RFC requerido' }]}
              >
                <Input placeholder={RFC_GENERICO} style={{ textTransform: 'uppercase' }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={10}>
              <Form.Item name="telefono" label="Teléfono">
                <Input placeholder="Ej. 664 123 4567" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="email" label="Correo electrónico">
            <Input placeholder="cliente@ejemplo.com" type="email" />
          </Form.Item>

          {/* ── Dirección de servicio ────────────────────────────────────── */}
          <div
            style={{
              borderTop: '1px solid #f0f0f0',
              marginTop: 4,
              marginBottom: 16,
              paddingTop: 12,
            }}
          >
            <span style={{ fontSize: 13, fontWeight: 500, color: '#595959' }}>
              <EnvironmentOutlined style={{ marginRight: 6 }} />
              Dirección de servicio
            </span>
          </div>

          <Row gutter={12}>
            <Col xs={24} sm={16}>
              <Form.Item name="serv_calle" label="Calle y número">
                <Input placeholder="Ej. Av. Insurgentes 145" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item
                name="serv_codigo_postal"
                label={
                  <span>
                    Código postal&nbsp;
                    <Tooltip title="Al ingresar 5 dígitos se auto-completarán ciudad y estado">
                      <InfoCircleOutlined style={{ color: '#1677ff', fontSize: 12 }} />
                    </Tooltip>
                  </span>
                }
                rules={[{ required: true, message: 'CP requerido' }]}
              >
                <Input
                  placeholder="Ej. 22000"
                  maxLength={5}
                  onChange={handleCPChange}
                  suffix={buscandoCP ? <Spin size="small" /> : null}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col xs={24} sm={8}>
              <Form.Item name="serv_colonia" label="Colonia">
                <Input placeholder="Colonia" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item name="serv_ciudad" label="Ciudad">
                <Input placeholder="Auto-completado" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item name="serv_estado" label="Estado">
                <Input placeholder="Auto-completado" />
              </Form.Item>
            </Col>
          </Row>

          {/* Latitud/Longitud ocultas — se rellenan desde Nominatim */}
          <Form.Item name="_latitud" hidden><Input /></Form.Item>
          <Form.Item name="_longitud" hidden><Input /></Form.Item>

          {/* Feedback visual de coordenadas cuando Nominatim las devuelve */}
          {coords && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginTop: -4,
                marginBottom: 12,
                padding: '6px 10px',
                background: 'rgba(22,119,255,0.06)',
                border: '1px solid rgba(22,119,255,0.2)',
                borderRadius: 6,
                fontSize: 12,
                color: '#1677ff',
              }}
            >
              <EnvironmentOutlined />
              <span>
                Geolocalizado: <strong>{coords.lat.toFixed(6)}</strong>,&nbsp;
                <strong>{coords.lon.toFixed(6)}</strong>
              </span>
              <a
                href={`https://www.google.com/maps?q=${coords.lat},${coords.lon}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ marginLeft: 'auto', fontSize: 11 }}
              >
                Ver en mapa ↗
              </a>
            </div>
          )}

          <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: -8 }}>
            Podrás completar los datos fiscales y dirección de facturación desde el módulo de Clientes.
          </div>
        </Form>
      </Spin>
    </Modal>
  );
};

export default ClienteRapidoModal;
