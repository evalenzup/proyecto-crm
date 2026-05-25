import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { Spin, Badge, Typography } from 'antd';
import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons';
import axios from 'axios';

const { Text } = Typography;

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'https://api.sistemas-erp.com/api').replace(/\/$/, '');

interface VerificacionData {
  id: string;
  nombre_completo: string;
  tipo_personal: string;
  area: string | null;
  puesto: string | null;
  activo: boolean;
  empresa_nombre: string;
  empresa_id: string;
  empresa_color: string;
}

const TIPO_LABEL: Record<string, string> = {
  TECNICO: 'Técnico',
  ADMINISTRATIVO: 'Administrativo',
  OPERATIVO: 'Operativo',
  SUPERVISOR: 'Supervisor',
  OTRO: 'Personal',
};

function hexToRgb(hex: string) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return { r, g, b };
}

function isDark(hex: string) {
  const { r, g, b } = hexToRgb(hex);
  return (r * 299 + g * 587 + b * 114) / 1000 < 128;
}

export default function VerificarTecnico() {
  const router = useRouter();
  const { id } = router.query;

  const [data, setData] = useState<VerificacionData | null>(null);
  const [fotoUrl, setFotoUrl] = useState<string | null>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [consultadoEn] = useState(() => new Date());

  useEffect(() => {
    if (!id || typeof id !== 'string') return;

    const load = async () => {
      setLoading(true);
      try {
        const { data: info } = await axios.get<VerificacionData>(
          `${API_BASE}/public/tecnicos/${id}/verificar`
        );
        setData(info);

        // Cargar foto y logo en paralelo (ignoran si no existen)
        const [fotoRes, logoRes] = await Promise.allSettled([
          axios.get(`${API_BASE}/public/tecnicos/${id}/foto`, { responseType: 'blob' }),
          axios.get(`${API_BASE}/public/empresas/${info.empresa_id}/logo`, { responseType: 'blob' }),
        ]);
        if (fotoRes.status === 'fulfilled') setFotoUrl(URL.createObjectURL(fotoRes.value.data));
        if (logoRes.status === 'fulfilled') setLogoUrl(URL.createObjectURL(logoRes.value.data));
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [id]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5', gap: 12 }}>
        <CloseCircleFilled style={{ fontSize: 64, color: '#ff4d4f' }} />
        <Text strong style={{ fontSize: 18 }}>Credencial no encontrada</Text>
        <Text type="secondary">El código QR no corresponde a ningún técnico registrado.</Text>
      </div>
    );
  }

  const color = data.empresa_color;
  const textOnColor = isDark(color) ? '#ffffff' : '#000000';
  const colorDark = `color-mix(in srgb, ${color} 70%, black)`;

  return (
    <>
      <Head>
        <title>Verificación de Credencial</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div style={{
        minHeight: '100vh',
        background: `linear-gradient(160deg, ${color} 0%, ${color}cc 40%, #1a1a2e 100%)`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px',
      }}>
        <div style={{ width: '100%', maxWidth: 360, borderRadius: 20, overflow: 'hidden', boxShadow: '0 16px 48px rgba(0,0,0,0.35)' }}>

          {/* Header compacto */}
          <div style={{ background: color, padding: '20px 24px 16px', textAlign: 'center' }}>
            {logoUrl && (
              <div style={{ background: '#fff', borderRadius: 10, padding: '8px 16px', display: 'inline-block', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
                <img src={logoUrl} alt="Logo" style={{ height: 44, maxWidth: 160, objectFit: 'contain', display: 'block' }} />
              </div>
            )}
            <div style={{ color: textOnColor, fontSize: 11, opacity: 0.9, letterSpacing: 1.5, textTransform: 'uppercase', fontWeight: 700, marginTop: 10 }}>
              {data.empresa_nombre}
            </div>
          </div>

          {/* Sección blanca */}
          <div style={{ background: '#fff', padding: '28px 24px 24px', textAlign: 'center' }}>

            {/* Foto */}
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
              <div style={{ width: 120, height: 150, borderRadius: 12, overflow: 'hidden', boxShadow: '0 4px 16px rgba(0,0,0,0.15)', background: '#f0f0f0', border: `3px solid ${color}` }}>
                {fotoUrl ? (
                  <img src={fotoUrl} alt="Foto" style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top center' }} />
                ) : (
                  <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb', fontSize: 12 }}>
                    Sin foto
                  </div>
                )}
              </div>
            </div>

            {/* Nombre y puesto */}
            <div style={{ fontWeight: 700, fontSize: 18, color: '#1a1a1a', lineHeight: 1.3 }}>
              {data.nombre_completo}
            </div>
            {data.puesto && (
              <div style={{ fontSize: 13, color: '#555', marginTop: 4 }}>{data.puesto}</div>
            )}
            <div style={{ fontSize: 12, color: '#999', marginTop: 3 }}>
              {TIPO_LABEL[data.tipo_personal] ?? data.tipo_personal}
              {data.area ? ` · ${data.area}` : ''}
            </div>

            {/* Badge de estado */}
            <div style={{ display: 'flex', justifyContent: 'center', margin: '20px 0' }}>
              {data.activo ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#f6ffed', border: '2px solid #52c41a', borderRadius: 32, padding: '12px 32px' }}>
                  <CheckCircleFilled style={{ fontSize: 24, color: '#52c41a' }} />
                  <span style={{ fontWeight: 800, fontSize: 18, color: '#389e0d', letterSpacing: 1 }}>VIGENTE</span>
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#fff2f0', border: '2px solid #ff4d4f', borderRadius: 32, padding: '12px 32px' }}>
                  <CloseCircleFilled style={{ fontSize: 24, color: '#ff4d4f' }} />
                  <span style={{ fontWeight: 800, fontSize: 18, color: '#cf1322', letterSpacing: 1 }}>NO VIGENTE</span>
                </div>
              )}
            </div>

            {/* Separador y pie */}
            <div style={{ height: 1, background: '#f0f0f0', margin: '0 0 14px' }} />
            <div style={{ fontSize: 11, color: '#bbb' }}>
              Consultado el {consultadoEn.toLocaleDateString('es-MX', { day: '2-digit', month: 'long', year: 'numeric' })} · {consultadoEn.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
            </div>
            <div style={{ fontSize: 10, color: '#ddd', marginTop: 2, letterSpacing: 0.5 }}>sistemas-erp.com</div>
          </div>

        </div>
      </div>
    </>
  );
}
