// src/pages/auditoria/index.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Table,
  Select,
  Input,
  DatePicker,
  Card,
  Space,
  Tag,
  Tooltip,
  Typography,
  Result,
  theme,
  Grid,
} from 'antd';
import { SearchOutlined, AuditOutlined } from '@ant-design/icons';
import { Breadcrumbs } from '@/components/Breadcrumb';
import {
  getAuditoria,
  AuditoriaLog,
  ACCIONES_AUDITORIA,
  canViewAuditoria,
} from '@/services/auditoriaService';
import { useAuth } from '@/context/AuthContext';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import { useTableHeight } from '@/hooks/useTableHeight';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { useToken } = theme;
const { useBreakpoint } = Grid;

// Color por tipo de acción
const getAccionColor = (accion: string): string => {
  if (accion.startsWith('CREAR')) return 'green';
  if (accion.startsWith('ACTUALIZAR') || accion.startsWith('CAMBIAR')) return 'blue';
  if (accion.startsWith('ELIMINAR') || accion.startsWith('CANCELAR')) return 'red';
  if (accion.startsWith('TIMBRAR')) return 'purple';
  if (accion.startsWith('ENVIAR')) return 'cyan';
  if (accion.startsWith('EXPORTAR')) return 'orange';
  if (accion === 'LOGIN') return 'geekblue';
  return 'default';
};

const AuditoriaPage: React.FC = () => {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  const { containerRef, tableY } = useTableHeight();
  const { token } = useToken();
  const screens = useBreakpoint();

  const [logs, setLogs] = useState<AuditoriaLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Empresa global del sidebar
  const { selectedEmpresaId } = useEmpresaSelector();
  const empresaId = selectedEmpresaId ?? null;

  // Filtros
  const [usuarioEmail, setUsuarioEmail] = useState<string>('');
  const [accion, setAccion] = useState<string | null>(null);
  const [fechaDesde, setFechaDesde] = useState<string | null>(null);
  const [fechaHasta, setFechaHasta] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    // El backend requiere empresa_id — esperar a que esté seleccionada
    if (!empresaId) return;

    setLoading(true);
    try {
      const response = await getAuditoria({
        empresa_id: empresaId,
        accion: accion || null,
        entidad: null,
        fecha_desde: fechaDesde || null,
        fecha_hasta: fechaHasta || null,
        offset: (currentPage - 1) * pageSize,
        limit: pageSize,
      });
      setLogs(response.items);
      setTotal(response.total);
    } catch {
      // silencio — el interceptor de axios ya notifica errores graves
    } finally {
      setLoading(false);
    }
  }, [empresaId, accion, fechaDesde, fechaHasta, currentPage, pageSize]);

  useEffect(() => {
    if (!authLoading && canViewAuditoria(user?.rol)) {
      fetchLogs();
    }
  }, [fetchLogs, authLoading, user]);

  // Reset página al cambiar filtros
  const handleFilterChange = (setter: (v: any) => void) => (value: any) => {
    setter(value ?? null);
    setCurrentPage(1);
  };

  const handleDateChange = (dates: any) => {
    setFechaDesde(dates ? dates[0].format('YYYY-MM-DD') : null);
    setFechaHasta(dates ? dates[1].format('YYYY-MM-DD') : null);
    setCurrentPage(1);
  };

  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size && size !== pageSize) {
      setPageSize(size);
    }
  };

  // Guard de acceso — no redirigir hasta que auth termine de cargar
  if (authLoading) {
    return null;
  }

  if (!canViewAuditoria(user?.rol)) {
    return (
      <div style={{ padding: 48 }}>
        <Result
          status="403"
          title="Acceso restringido"
          subTitle="No tienes permisos para ver el registro de auditoría."
        />
      </div>
    );
  }

  const columns = [
    {
      title: 'Fecha / Hora',
      dataIndex: 'creado_en',
      key: 'creado_en',
      width: 170,
      render: (val: string) => {
        if (!val) return '—';
        return dayjs(val).format('DD/MM/YYYY HH:mm:ss');
      },
    },
    {
      title: 'Usuario',
      dataIndex: 'usuario_email',
      key: 'usuario_email',
      width: 220,
      render: (email: string) => (
        <Typography.Text ellipsis={{ tooltip: email }} style={{ maxWidth: 200, display: 'block' }}>
          {email || '—'}
        </Typography.Text>
      ),
    },
    {
      title: 'Acción',
      dataIndex: 'accion',
      key: 'accion',
      width: 200,
      render: (accion: string) => (
        <Tag color={getAccionColor(accion)} style={{ whiteSpace: 'nowrap' }}>
          {accion}
        </Tag>
      ),
    },
    {
      title: 'Entidad',
      dataIndex: 'entidad',
      key: 'entidad',
      width: 110,
      render: (val: string) => val || '—',
    },
    {
      title: 'ID Entidad',
      dataIndex: 'entidad_id',
      key: 'entidad_id',
      width: 130,
      render: (val: string) =>
        val ? (
          <Typography.Text
            copyable={{ text: val }}
            ellipsis={{ tooltip: val }}
            style={{ maxWidth: 110, display: 'block', fontFamily: 'monospace', fontSize: '0.8em' }}
          >
            {val.slice(0, 8)}…
          </Typography.Text>
        ) : (
          '—'
        ),
    },
    {
      title: 'Detalle',
      dataIndex: 'detalle',
      key: 'detalle',
      render: (detalle: string | null) => {
        if (!detalle) return '—';
        let parsed: any = detalle;
        try {
          if (typeof detalle === 'string') parsed = JSON.parse(detalle);
        } catch {
          // uso el string como está
        }
        const preview =
          typeof parsed === 'object'
            ? Object.entries(parsed)
                .map(([k, v]) => `${k}: ${v}`)
                .join(' · ')
            : String(parsed);

        return (
          <Tooltip
            title={
              <pre style={{ margin: 0, fontSize: '0.8em', maxWidth: 400, whiteSpace: 'pre-wrap' }}>
                {typeof parsed === 'object' ? JSON.stringify(parsed, null, 2) : String(parsed)}
              </pre>
            }
          >
            <Typography.Text ellipsis style={{ maxWidth: 280, display: 'block', cursor: 'default' }}>
              {preview}
            </Typography.Text>
          </Tooltip>
        );
      },
    },
    {
      title: 'IP',
      dataIndex: 'ip',
      key: 'ip',
      width: 130,
      render: (val: string) => val || '—',
    },
  ];

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">
            <AuditOutlined style={{ marginRight: 8 }} />
            Auditoría
          </h1>
        </div>
      </div>

      <div className="app-content" ref={containerRef}>
        <Card size="small" variant="borderless" styles={{ body: { padding: 12 } }} style={{ marginBottom: 4 }}>
          <div
            style={{
              position: 'sticky',
              top: 0,
              zIndex: 9,
              padding: screens.lg ? '4px' : '8px',
              background: token.colorBgContainer,
            }}
          >
            <Space wrap>
              <Input
                prefix={<SearchOutlined />}
                placeholder="Email usuario"
                style={{ width: 220 }}
                allowClear
                value={usuarioEmail}
                onChange={(e) => {
                  setUsuarioEmail(e.target.value);
                  setCurrentPage(1);
                }}
              />
              <Select
                placeholder="Acción"
                style={{ width: 220 }}
                allowClear
                showSearch
                optionFilterProp="label"
                options={ACCIONES_AUDITORIA}
                value={accion ?? undefined}
                onChange={handleFilterChange(setAccion)}
              />
              <RangePicker
                onChange={handleDateChange}
                value={
                  fechaDesde && fechaHasta
                    ? [dayjs(fechaDesde), dayjs(fechaHasta)]
                    : null
                }
              />
            </Space>
          </div>
        </Card>

        <Table
          rowKey="id"
          loading={loading}
          dataSource={
            usuarioEmail.trim().length >= 3
              ? logs.filter((l) =>
                  (l.usuario_email ?? '').toLowerCase().includes(usuarioEmail.trim().toLowerCase())
                )
              : logs
          }
          columns={columns}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            onChange: handlePageChange,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50', '100'],
            showTotal: (t) => `${t} registros`,
          }}
          virtual
          scroll={{ x: 1200, y: tableY }}
          locale={{ emptyText: 'Sin registros de auditoría' }}
          size="small"
        />
      </div>
    </>
  );
};

export default AuditoriaPage;
