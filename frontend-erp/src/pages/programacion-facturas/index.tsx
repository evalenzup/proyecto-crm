// pages/programacion-facturas/index.tsx
import React, { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import {
  Table, Button, Popconfirm, Space, Tag, Badge, Tooltip,
  Card, Switch, message, Select, theme,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  PlayCircleOutlined, PauseOutlined, CarryOutOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { PageHeader } from '@/components/PageHeader';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import { useTableHeight } from '@/hooks/useTableHeight';
import {
  programacionFacturaService,
  ProgramacionFacturaOut,
  PERIODICIDAD_LABELS,
} from '@/services/programacionFacturaService';

const { Option } = Select;

const PERIODICIDAD_COLOR: Record<string, string> = {
  unica:      'default',
  semanal:    'cyan',
  quincenal:  'blue',
  mensual:    'geekblue',
  bimestral:  'purple',
  trimestral: 'volcano',
  semestral:  'orange',
  anual:      'gold',
};

const ProgramacionFacturasPage: React.FC = () => {
  const router = useRouter();
  const { token } = theme.useToken();
  const { containerRef, tableY } = useTableHeight();
  const { selectedEmpresaId } = useEmpresaSelector();

  const [data, setData] = useState<ProgramacionFacturaOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [activoFiltro, setActivoFiltro] = useState<boolean | undefined>(undefined);

  const fetchData = useCallback(async (page: number, size: number, activo?: boolean) => {
    setLoading(true);
    try {
      const result = await programacionFacturaService.list({
        empresa_id: selectedEmpresaId ?? undefined,
        activo,
        limit: size,
        offset: (page - 1) * size,
      });
      setData(result.items);
      setTotal(result.total);
    } catch {
      message.error('Error al cargar programaciones');
    } finally {
      setLoading(false);
    }
  }, [selectedEmpresaId]);

  useEffect(() => { fetchData(currentPage, pageSize, activoFiltro); },
    [fetchData, currentPage, pageSize, activoFiltro]);

  useEffect(() => { setCurrentPage(1); }, [selectedEmpresaId]);

  const handleDelete = async (id: string) => {
    try {
      await programacionFacturaService.delete(id);
      message.success('Programación eliminada');
      fetchData(currentPage, pageSize, activoFiltro);
    } catch {
      message.error('Error al eliminar');
    }
  };

  const handleToggleActivo = async (record: ProgramacionFacturaOut) => {
    try {
      await programacionFacturaService.update(record.id, { activo: !record.activo });
      message.success(record.activo ? 'Programación pausada' : 'Programación reactivada');
      fetchData(currentPage, pageSize, activoFiltro);
    } catch {
      message.error('Error al actualizar');
    }
  };

  const handleEjecutarAhora = async (id: string) => {
    try {
      message.loading({ content: 'Ejecutando...', key: 'exec' });
      await programacionFacturaService.ejecutarAhora(id);
      message.success({ content: 'Ejecutado correctamente', key: 'exec' });
      fetchData(currentPage, pageSize, activoFiltro);
    } catch {
      message.error({ content: 'Error al ejecutar', key: 'exec' });
    }
  };

  const columns: ColumnsType<ProgramacionFacturaOut> = [
    {
      title: 'Nombre / Cliente',
      key: 'nombre_cliente',
      width: 220,
      render: (_, r) => (
        <div>
          <div style={{ fontWeight: 600 }}>{r.nombre || r.cliente_nombre || '—'}</div>
          {r.nombre && (
            <div style={{ fontSize: 12, color: token.colorTextSecondary }}>{r.cliente_nombre}</div>
          )}
        </div>
      ),
    },
    {
      title: 'Periodicidad',
      dataIndex: 'periodicidad',
      key: 'periodicidad',
      width: 130,
      render: (val: string) => (
        <Tag color={PERIODICIDAD_COLOR[val] ?? 'default'}>
          {PERIODICIDAD_LABELS[val as keyof typeof PERIODICIDAD_LABELS] ?? val}
        </Tag>
      ),
    },
    {
      title: 'Próxima ejecución',
      dataIndex: 'proxima_ejecucion',
      key: 'proxima_ejecucion',
      width: 150,
      render: (val: string, r) => {
        if (!r.activo) return <span style={{ color: token.colorTextDisabled }}>—</span>;
        const hoy = new Date().toISOString().slice(0, 10);
        const vencida = val < hoy;
        return (
          <span style={{ color: vencida ? token.colorError : undefined }}>
            {val}
            {vencida && <Tag color="red" style={{ marginLeft: 4, fontSize: 10 }}>Pendiente</Tag>}
          </span>
        );
      },
    },
    {
      title: 'Auto',
      key: 'auto',
      width: 120,
      render: (_, r) => (
        <Space size={4}>
          {r.auto_timbrar && <Tag color="blue" style={{ fontSize: 10 }}>Timbra</Tag>}
          {r.auto_enviar  && <Tag color="green" style={{ fontSize: 10 }}>Envía</Tag>}
          {!r.auto_timbrar && !r.auto_enviar && (
            <span style={{ color: token.colorTextDisabled, fontSize: 12 }}>Manual</span>
          )}
        </Space>
      ),
    },
    {
      title: 'Generadas',
      dataIndex: 'facturas_generadas',
      key: 'facturas_generadas',
      width: 90,
      align: 'center',
    },
    {
      title: 'Fecha fin',
      dataIndex: 'fecha_fin',
      key: 'fecha_fin',
      width: 110,
      render: (val?: string | null) =>
        val ? <span style={{ fontSize: 12 }}>{val}</span>
            : <span style={{ color: token.colorTextDisabled }}>Indefinido</span>,
    },
    {
      title: 'Estado',
      dataIndex: 'activo',
      key: 'activo',
      width: 90,
      render: (val: boolean) =>
        val ? <Badge status="success" text="Activa" />
            : <Badge status="default" text="Pausada" />,
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 160,
      render: (_, record) => (
        <Space>
          <Tooltip title="Ejecutar ahora">
            <Popconfirm
              title="¿Ejecutar esta programación ahora?"
              onConfirm={() => handleEjecutarAhora(record.id)}
              okText="Sí"
              cancelText="No"
            >
              <Button type="link" icon={<CarryOutOutlined />} />
            </Popconfirm>
          </Tooltip>
          <Tooltip title={record.activo ? 'Pausar' : 'Reactivar'}>
            <Button
              type="link"
              icon={record.activo ? <PauseOutlined /> : <PlayCircleOutlined />}
              onClick={() => handleToggleActivo(record)}
            />
          </Tooltip>
          <Tooltip title="Editar">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => router.push(`/programacion-facturas/form/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Eliminar">
            <Popconfirm
              title="¿Eliminar esta programación?"
              onConfirm={() => handleDelete(record.id)}
              okText="Sí"
              cancelText="No"
            >
              <Button type="link" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Programación de Facturas"
        extra={
          <>
            <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/programacion-facturas/form')}
          >
            Nueva Programación
          </Button>
          </>
        }
      />

      <div className="app-content" ref={containerRef}>
        <Card size="small" variant="borderless" styles={{ body: { padding: 12 } }} style={{ marginBottom: 8 }}>
          <div style={{ background: token.colorBgContainer, padding: 4 }}>
            <Space wrap>
              <Select
                placeholder="Estado"
                style={{ width: 140, minWidth: 120 }}
                allowClear
                onChange={(val: boolean | undefined) => {
                  setActivoFiltro(val);
                  setCurrentPage(1);
                }}
              >
                <Option value={undefined}>Todos</Option>
                <Option value={true}>Activas</Option>
                <Option value={false}>Pausadas</Option>
              </Select>
            </Space>
          </div>
        </Card>

        <Table<ProgramacionFacturaOut>
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          scroll={{ x: 1000, y: tableY }}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            onChange: (page, size) => {
              setCurrentPage(page);
              if (size) setPageSize(size);
            },
            showSizeChanger: true,
            showTotal: (t) => `${t} programaciones`,
          }}
          locale={{ emptyText: 'No hay programaciones configuradas' }}
        />
      </div>
    </>
  );
};

export default ProgramacionFacturasPage;
