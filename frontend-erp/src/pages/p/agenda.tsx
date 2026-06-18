// pages/p/agenda.tsx
// Página pública de agenda para técnicos — sin autenticación
import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { Spin, Tag } from 'antd';
import {
  LeftOutlined,
  RightOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
  UserOutlined,
  FileTextOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import 'dayjs/locale/es';
dayjs.locale('es');

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'https://api.sistemas-erp.com/api').replace(/\/$/, '');

// ── Tipos ─────────────────────────────────────────────────────────────────────

interface AgendaEmpresa {
  nombre: string;
  color: string;
}

interface AgendaItem {
  id: string;
  folio_os: string;
  fecha_programada: string;
  hora_inicio: string | null;
  hora_fin: string | null;
  estado: string;
  prioridad: string;
  cliente_nombre: string | null;
  tecnico_nombre: string | null;
  servicio_nombre: string | null;
  direccion_servicio: string | null;
  notas_tecnico: string | null;
  precio_acordado: number | null;
}

// ── Constantes de estilo ──────────────────────────────────────────────────────

const ESTADO_COLOR: Record<string, string> = {
  PENDIENTE:   '#d48806',
  ASIGNADO:    '#1677ff',
  EN_CAMINO:   '#08979c',
  EN_PROGRESO: '#2f54eb',
  COMPLETADO:  '#389e0d',
  CANCELADO:   '#cf1322',
  REAGENDADO:  '#d46b08',
};

const ESTADO_BG: Record<string, string> = {
  PENDIENTE:   '#fffbe6',
  ASIGNADO:    '#e6f4ff',
  EN_CAMINO:   '#e6fffb',
  EN_PROGRESO: '#f0f5ff',
  COMPLETADO:  '#f6ffed',
  CANCELADO:   '#fff2f0',
  REAGENDADO:  '#fff7e6',
};

const ESTADO_LABEL: Record<string, string> = {
  PENDIENTE:   'Pendiente',
  ASIGNADO:    'Asignado',
  EN_CAMINO:   'En camino',
  EN_PROGRESO: 'En progreso',
  COMPLETADO:  'Completado',
  CANCELADO:   'Cancelado',
  REAGENDADO:  'Reagendado',
};

const PRIORIDAD_COLOR: Record<string, string> = {
  BAJA:    '#52c41a',
  MEDIA:   '#1677ff',
  ALTA:    '#fa8c16',
  URGENTE: '#f5222d',
};

// ── Componente ────────────────────────────────────────────────────────────────

export default function AgendaPublica() {
  const router = useRouter();
  const [items, setItems] = useState<AgendaItem[]>([]);
  const [empresa, setEmpresa] = useState<AgendaEmpresa | null>(null);
  const [loading, setLoading] = useState(true);
  const [fecha, setFecha] = useState('');
  const [empresaId, setEmpresaId] = useState('');
  const [error, setError] = useState(false);

  // Inicializar fecha y token desde query params
  useEffect(() => {
    if (!router.isReady) return;
    // Acepta agenda_token (nuevo) o empresa_id (legacy) para compatibilidad
    const token = (router.query.agenda_token || router.query.empresa_id) as string;
    const f     = router.query.fecha as string;
    if (!token) { setError(true); setLoading(false); return; }
    setEmpresaId(token);  // reutilizamos el estado — ahora contiene el token
    setFecha(f && dayjs(f).isValid() ? f : dayjs().format('YYYY-MM-DD'));
  }, [router.isReady, router.query]);

  // Cargar agenda
  const cargar = useCallback(async (eid: string, f: string) => {
    if (!eid || !f) return;
    setLoading(true);
    setError(false);
    try {
      const { data } = await axios.get(`${API_BASE}/public/agenda`, {
        params: { agenda_token: eid, fecha: f },
      });
      setItems(data.items ?? []);
      if (data.empresa) setEmpresa(data.empresa);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (empresaId && fecha) cargar(empresaId, fecha);
  }, [empresaId, fecha, cargar]);

  const cambiarDia = (delta: number) => {
    const nuevaFecha = dayjs(fecha).add(delta, 'day').format('YYYY-MM-DD');
    setFecha(nuevaFecha);
    router.replace({ query: { ...router.query, fecha: nuevaFecha } }, undefined, { shallow: true });
  };

  const esHoy = fecha === dayjs().format('YYYY-MM-DD');
  const fechaLabel = dayjs(fecha).format('dddd D [de] MMMM [de] YYYY');

  // ── Error: sin empresa_id ──────────────────────────────────────────────────
  if (!loading && error && !empresaId) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5', padding: 24 }}>
        <div style={{ textAlign: 'center', color: '#999' }}>
          <CalendarOutlined style={{ fontSize: 48, marginBottom: 12 }} />
          <div style={{ fontSize: 16, fontWeight: 600, color: '#333' }}>Enlace inválido</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>Falta el parámetro agenda_token en la URL</div>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>{empresa ? `Agenda · ${empresa.nombre}` : 'Agenda del día'}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <meta name="theme-color" content="#0a5c91" />
      </Head>

      <div style={{ minHeight: '100vh', background: '#f0f4f8', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' }}>

        {/* ── Header ── */}
        <div style={{
          background: empresa
            ? `linear-gradient(135deg, ${empresa.color}dd 0%, ${empresa.color} 100%)`
            : 'linear-gradient(135deg, #0D2137 0%, #0a5c91 100%)',
          padding: '16px 16px 20px',
          color: '#fff',
        }}>
          <div style={{ fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', opacity: 0.7, marginBottom: 4 }}>
            {empresa ? empresa.nombre : 'Agenda de servicios'}
          </div>

          {/* Navegación de fecha */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <button
              onClick={() => cambiarDia(-1)}
              style={{ background: 'rgba(255,255,255,0.15)', border: 'none', borderRadius: 8, width: 36, height: 36, cursor: 'pointer', color: '#fff', fontSize: 16, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <LeftOutlined />
            </button>

            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: 17, fontWeight: 700, lineHeight: 1.2, textTransform: 'capitalize' }}>
                {fechaLabel}
              </div>
              {esHoy && (
                <span style={{ fontSize: 11, background: '#02C39A', color: '#fff', borderRadius: 10, padding: '1px 8px', marginTop: 4, display: 'inline-block', fontWeight: 600 }}>
                  HOY
                </span>
              )}
            </div>

            <button
              onClick={() => cambiarDia(1)}
              style={{ background: 'rgba(255,255,255,0.15)', border: 'none', borderRadius: 8, width: 36, height: 36, cursor: 'pointer', color: '#fff', fontSize: 16, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <RightOutlined />
            </button>
          </div>

          {/* Contador */}
          {!loading && (
            <div style={{ textAlign: 'center', marginTop: 10, fontSize: 12, opacity: 0.8 }}>
              {items.length === 0 ? 'Sin servicios programados' : `${items.length} servicio${items.length !== 1 ? 's' : ''} programado${items.length !== 1 ? 's' : ''}`}
            </div>
          )}
        </div>

        {/* ── Contenido ── */}
        <div style={{ padding: '16px 12px', maxWidth: 640, margin: '0 auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', paddingTop: 60 }}>
              <Spin size="large" />
              <div style={{ marginTop: 12, color: '#888', fontSize: 13 }}>Cargando agenda…</div>
            </div>
          ) : error ? (
            <div style={{ textAlign: 'center', paddingTop: 60, color: '#999' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>⚠️</div>
              <div style={{ fontWeight: 600, color: '#333' }}>No se pudo cargar la agenda</div>
              <div style={{ fontSize: 13, marginTop: 4 }}>Verifica tu conexión e intenta de nuevo</div>
              <button
                onClick={() => cargar(empresaId, fecha)}
                style={{ marginTop: 16, padding: '8px 20px', background: '#0a5c91', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14 }}
              >
                Reintentar
              </button>
            </div>
          ) : items.length === 0 ? (
            <div style={{ textAlign: 'center', paddingTop: 60, color: '#aaa' }}>
              <CalendarOutlined style={{ fontSize: 48, marginBottom: 12 }} />
              <div style={{ fontSize: 15, fontWeight: 600, color: '#555' }}>Sin servicios para este día</div>
              <div style={{ fontSize: 13, marginTop: 4 }}>Navega a otro día con las flechas</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {items.map((item) => (
                <ServiceCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div style={{ textAlign: 'center', padding: '20px 16px', color: '#ccc', fontSize: 11 }}>
          sistemas-erp.com
        </div>
      </div>
    </>
  );
}

// ── Card de servicio ──────────────────────────────────────────────────────────

function ServiceCard({ item }: { item: AgendaItem }) {
  const color  = ESTADO_COLOR[item.estado]  ?? '#888';
  const bg     = ESTADO_BG[item.estado]     ?? '#fafafa';
  const label  = ESTADO_LABEL[item.estado]  ?? item.estado;
  const priColor = PRIORIDAD_COLOR[item.prioridad] ?? '#888';

  return (
    <div style={{
      background: '#fff',
      borderRadius: 12,
      overflow: 'hidden',
      boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
      borderLeft: `4px solid ${color}`,
    }}>
      {/* Cabecera: folio + hora + estado */}
      <div style={{ padding: '12px 14px 8px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div>
          <div style={{ fontSize: 11, color: '#999', fontWeight: 600, letterSpacing: 0.5 }}>
            {item.folio_os}
          </div>
          {(item.hora_inicio || item.hora_fin) && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
              <ClockCircleOutlined style={{ fontSize: 11, color: '#888' }} />
              <span style={{ fontSize: 13, fontWeight: 700, color: '#333' }}>
                {item.hora_inicio ?? '—'}
                {item.hora_fin ? ` – ${item.hora_fin}` : ''}
              </span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <span style={{
            fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
            background: bg, color: color, border: `1px solid ${color}44`,
          }}>
            {label}
          </span>
          {item.prioridad !== 'MEDIA' && (
            <span style={{ fontSize: 10, color: priColor, fontWeight: 600 }}>
              {item.prioridad}
            </span>
          )}
          {item.precio_acordado != null && (
            <span style={{
              fontSize: 14, fontWeight: 800, color: '#237804',
              background: '#f6ffed', border: '1px solid #b7eb8f',
              borderRadius: 8, padding: '2px 10px',
            }}>
              {item.precio_acordado.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}
            </span>
          )}
        </div>
      </div>

      {/* Cuerpo */}
      <div style={{ padding: '0 14px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {/* Cliente */}
        {item.cliente_nombre && (
          <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', lineHeight: 1.3 }}>
            {item.cliente_nombre}
          </div>
        )}

        {/* Tipo de servicio */}
        {item.servicio_nombre && (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 5, alignSelf: 'flex-start',
            fontSize: 13, fontWeight: 600, color: '#0a5c91',
            background: '#e6f4ff', border: '1px solid #91caff',
            borderRadius: 6, padding: '2px 8px',
          }}>
            <FileTextOutlined style={{ fontSize: 12 }} />
            {item.servicio_nombre}
          </div>
        )}

        {/* Técnico */}
        {item.tecnico_nombre && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 13, color: '#555' }}>
            <UserOutlined style={{ fontSize: 11, color: '#888' }} />
            {item.tecnico_nombre}
          </div>
        )}

        {/* Dirección */}
        {item.direccion_servicio && (
          <a
            href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(item.direccion_servicio)}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ display: 'flex', alignItems: 'flex-start', gap: 5, fontSize: 13, color: '#0a5c91', textDecoration: 'none' }}
          >
            <EnvironmentOutlined style={{ fontSize: 12, marginTop: 2, flexShrink: 0 }} />
            <span>{item.direccion_servicio}</span>
          </a>
        )}

        {/* Notas al técnico */}
        {item.notas_tecnico && (
          <div style={{
            display: 'flex', alignItems: 'flex-start', gap: 5,
            background: '#fffbe6', border: '1px solid #ffe58f',
            borderRadius: 6, padding: '6px 8px', marginTop: 2,
          }}>
            <FileTextOutlined style={{ fontSize: 11, color: '#d48806', marginTop: 2, flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: '#614700', lineHeight: 1.4 }}>
              {item.notas_tecnico}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
