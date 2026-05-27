// src/components/ClienteRapidoModal.tsx
/**
 * Modal para crear un cliente con datos mínimos desde el formulario de OS.
 *
 * Geolocalización en dos pasos:
 *  1. Al completar el CP (5 dígitos) → lookup por postalcode → auto-fill ciudad/estado
 *  2. Botón "Geolocalizar dirección" (habilitado cuando hay calle + CP) →
 *     búsqueda con todos los campos → coordenadas precisas a nivel de calle
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
  Tooltip,
  Alert,
} from 'antd';
import { EnvironmentOutlined, AimOutlined, InfoCircleOutlined } from '@ant-design/icons';
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

const RFC_GENERICO   = 'XAXX010101000';
const REGIMEN_DEFAULT = '616'; // Sin obligaciones fiscales
const BASE_URL       = 'https://nominatim.openstreetmap.org/search';
const TIMEOUT_MS     = 10_000;

// ── Helpers Nominatim ─────────────────────────────────────────────────────────

async function fetchNominatim(params: Record<string, string>) {
  const qs = new URLSearchParams({ ...params, format: 'json', addressdetails: '1', limit: '1' });
  const url = `${BASE_URL}?${qs}`;
  console.log('[Nominatim] fetch →', url);

  const ctrl  = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res  = await fetch(url, { signal: ctrl.signal });
    const data = await res.json();
    console.log('[Nominatim] response:', JSON.stringify(data, null, 2));
    return data;
  } finally {
    clearTimeout(timer);
  }
}

function extractAddress(item: any) {
  const a = item?.address ?? {};
  let ciudad = a.city || a.town || a.municipality || a.village || a.county || '';
  if (ciudad.toLowerCase().startsWith('municipio de ')) ciudad = ciudad.slice(13);
  return {
    ciudad:  ciudad.trim() || null,
    estado:  (a.state ?? '').trim() || null,
    colonia: (a.suburb || a.neighbourhood || a.quarter || '').trim() || null,
    lat:     item?.lat ? parseFloat(item.lat) : null,
    lon:     item?.lon ? parseFloat(item.lon) : null,
  };
}

// ── Componente ────────────────────────────────────────────────────────────────

const ClienteRapidoModal: React.FC<Props> = ({ open, onClose, onCreated }) => {
  const [form]   = Form.useForm();
  const [saving, setSaving]           = useState(false);
  const [buscandoCP, setBuscandoCP]   = useState(false);
  const [geocodando, setGeocodando]   = useState(false);
  const [coords, setCoords]           = useState<{ lat: number; lon: number } | null>(null);
  const lastCPRef = useRef('');
  const { selectedEmpresaId } = useEmpresaSelector();

  // ── Reset ──────────────────────────────────────────────────────────────────
  const handleAfterOpen = () => {
    form.resetFields();
    lastCPRef.current = '';
    setCoords(null);
  };

  // ── Paso 1: CP → ciudad + estado ──────────────────────────────────────────
  const handleCPChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const cp = e.target.value.replace(/\D/g, '').slice(0, 5);
    if (cp.length !== 5 || cp === lastCPRef.current) return;
    lastCPRef.current = cp;

    setBuscandoCP(true);
    try {
      const data = await fetchNominatim({ postalcode: cp, country: 'MX' });
      if (!data?.length) {
        message.warning(`CP ${cp}: no encontrado. Llena ciudad y estado manualmente.`, 3);
        return;
      }
      const r = extractAddress(data[0]);
      const coloniaActual = form.getFieldValue('serv_colonia');
      form.setFieldsValue({
        serv_ciudad:  r.ciudad  ?? undefined,
        serv_estado:  r.estado  ?? undefined,
        serv_colonia: coloniaActual || r.colonia || undefined,
      });
      message.success(`CP ${cp} → ${r.ciudad ?? '?'}, ${r.estado ?? '?'}`, 2);
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        message.warning('Tiempo de espera agotado. Llena ciudad y estado manualmente.', 3);
      }
      // Si falla silenciosamente el usuario puede escribir los campos a mano
    } finally {
      setBuscandoCP(false);
    }
  };

  // ── Paso 2: Dirección completa → lat/lon precisos ─────────────────────────
  const handleGeocodificar = async () => {
    const v = form.getFieldsValue(['serv_calle', 'serv_colonia', 'serv_ciudad', 'serv_estado', 'serv_codigo_postal']);

    const params: Record<string, string> = { country: 'Mexico' };
    if (v.serv_calle)          params.street     = v.serv_calle;
    if (v.serv_codigo_postal)  params.postalcode = v.serv_codigo_postal;
    if (v.serv_ciudad)         params.city       = v.serv_ciudad;
    if (v.serv_estado)         params.state      = v.serv_estado;

    setGeocodando(true);
    try {
      const data = await fetchNominatim(params);
      if (!data?.length) {
        message.warning('No se encontró la dirección. Intenta con menos datos o verifica la calle.', 4);
        return;
      }
      const r = extractAddress(data[0]);
      if (r.lat && r.lon) {
        form.setFieldsValue({ _latitud: r.lat, _longitud: r.lon });
        // Rellenar colonia si vino en la respuesta y el campo está vacío
        if (r.colonia && !form.getFieldValue('serv_colonia')) {
          form.setFieldValue('serv_colonia', r.colonia);
        }
        setCoords({ lat: r.lat, lon: r.lon });
        message.success('Dirección geolocalizada correctamente', 2);
      } else {
        message.warning('Se encontró la dirección pero sin coordenadas', 3);
      }
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        message.warning('Tiempo de espera agotado al geocodificar.', 3);
      } else {
        message.error('Error al geocodificar la dirección', 3);
      }
    } finally {
      setGeocodando(false);
    }
  };

  // ── Guardar ────────────────────────────────────────────────────────────────
  const handleOk = async () => {
    let values: any;
    try { values = await form.validateFields(); }
    catch { return; }

    setSaving(true);
    try {
      const payload: any = {
        nombre_comercial:    values.nombre_comercial.trim(),
        nombre_razon_social: values.nombre_comercial.trim(),
        rfc:                 (values.rfc ?? RFC_GENERICO).trim().toUpperCase(),
        regimen_fiscal:      REGIMEN_DEFAULT,
        codigo_postal:       (values.serv_codigo_postal ?? '00000').trim(),
        serv_calle:          values.serv_calle?.trim()          || undefined,
        serv_colonia:        values.serv_colonia?.trim()        || undefined,
        serv_ciudad:         values.serv_ciudad?.trim()         || undefined,
        serv_estado:         values.serv_estado?.trim()         || undefined,
        serv_codigo_postal:  values.serv_codigo_postal?.trim()  || undefined,
        latitud:             values._latitud  ?? undefined,
        longitud:            values._longitud ?? undefined,
        telefono:            values.telefono?.trim()  ? [values.telefono.trim()]  : undefined,
        email:               values.email?.trim()     ? [values.email.trim()]     : undefined,
        empresa_id:          selectedEmpresaId ? [selectedEmpresaId] : [],
      };

      const creado = await clienteService.createCliente(payload);
      message.success(`Cliente "${creado.nombre_comercial}" creado`);
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
  // Determinar si el botón de geocodificación está disponible
  const puedeGeocodificar = !geocodando && !buscandoCP;

  return (
    <Modal
      title="Nuevo cliente rápido"
      open={open}
      onCancel={onClose}
      afterOpenChange={(isOpen) => { if (isOpen) handleAfterOpen(); }}
      width={560}
      footer={[
        <Button key="cancel" onClick={onClose} disabled={saving}>Cancelar</Button>,
        <Button key="submit" type="primary" loading={saving} onClick={handleOk}>
          Crear cliente
        </Button>,
      ]}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" style={{ marginTop: 8 }}>

        {/* ── Identificación ────────────────────────────────────────────── */}
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
              initialValue={RFC_GENERICO}
              label={
                <span>RFC&nbsp;
                  <Tooltip title="XAXX010101000 = Público en general (sin datos fiscales)">
                    <InfoCircleOutlined style={{ color: '#aaa', fontSize: 12 }} />
                  </Tooltip>
                </span>
              }
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

        {/* ── Dirección de servicio ──────────────────────────────────────── */}
        <div style={{ borderTop: '1px solid #f0f0f0', margin: '4px 0 16px', paddingTop: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: '#595959' }}>
            <EnvironmentOutlined style={{ marginRight: 6 }} />
            Dirección de servicio
          </span>
        </div>

        <Row gutter={12}>
          <Col xs={24} sm={16}>
            <Form.Item name="serv_calle" label="Calle y número">
              <Input placeholder="Ej. Gladiolas 2942" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item
              name="serv_codigo_postal"
              label={
                <span>Código postal&nbsp;
                  <Tooltip title="Al ingresar 5 dígitos se auto-completarán ciudad y estado">
                    <InfoCircleOutlined style={{ color: '#1677ff', fontSize: 12 }} />
                  </Tooltip>
                </span>
              }
              rules={[{ required: true, message: 'CP requerido' }]}
            >
              <Input
                placeholder="Ej. 22850"
                maxLength={5}
                onChange={handleCPChange}
                suffix={
                  <span style={{ width: 14, display: 'inline-block' }}>
                    {buscandoCP
                      ? <AimOutlined spin style={{ color: '#1677ff' }} />
                      : null}
                  </span>
                }
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
              <Input placeholder="Auto-completado con CP" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item name="serv_estado" label="Estado">
              <Input placeholder="Auto-completado con CP" />
            </Form.Item>
          </Col>
        </Row>

        {/* ── Paso 2: Botón geolocalizar con dirección completa ─────────── */}
        <Form.Item style={{ marginBottom: 8 }}>
          <Tooltip title="Usa calle + CP + ciudad + estado para obtener coordenadas precisas">
            <Button
              icon={<AimOutlined />}
              loading={geocodando}
              disabled={!puedeGeocodificar}
              onClick={handleGeocodificar}
              block
            >
              Geolocalizar dirección
            </Button>
          </Tooltip>
        </Form.Item>

        {/* Latitud/Longitud — ocultas en el form, visibles como badge */}
        <Form.Item name="_latitud"  hidden><Input /></Form.Item>
        <Form.Item name="_longitud" hidden><Input /></Form.Item>

        {/* Badge de coordenadas obtenidas */}
        {coords && (
          <Alert
            style={{ marginBottom: 12 }}
            type="success"
            icon={<EnvironmentOutlined />}
            showIcon
            message={
              <span style={{ fontSize: 12 }}>
                <strong>{coords.lat.toFixed(6)}</strong>, <strong>{coords.lon.toFixed(6)}</strong>
                &nbsp;—&nbsp;
                <a
                  href={`https://www.google.com/maps?q=${coords.lat},${coords.lon}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Ver en mapa ↗
                </a>
              </span>
            }
          />
        )}

        <div style={{ fontSize: 12, color: '#8c8c8c' }}>
          Podrás completar los datos fiscales y dirección de facturación desde el módulo de Clientes.
        </div>
      </Form>
    </Modal>
  );
};

export default ClienteRapidoModal;
