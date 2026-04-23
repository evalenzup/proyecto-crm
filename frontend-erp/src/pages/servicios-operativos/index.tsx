// pages/servicios-operativos/index.tsx

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Table,
  Button,
  Popconfirm,
  Space,
  Input,
  Select,
  Tooltip,
  Card,
  Tag,
  Badge,
  message,
  theme,
} from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { debounce } from 'lodash';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import { useTableHeight } from '@/hooks/useTableHeight';
import {
  servicioOperativoService,
  ServicioOperativoOut,
} from '@/services/servicioOperativoService';

const { Option } = Select;

const ServiciosOperativosPage: React.FC = () => {
  const router = useRouter();
  const { token } = theme.useToken();
  const { containerRef, tableY } = useTableHeight();
  const { selectedEmpresaId, empresas, isAdmin } = useEmpresaSelector();

  const [data, setData] = useState<ServicioOperativoOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchInput, setSearchInput] = useState('');
  const [q, setQ] = useState<string | undefined>(undefined);
  const [activoFiltro, setActivoFiltro] = useState<boolean | undefined>(undefined);

  const fetchData = useCallback(async (page: number, size: number, query?: string, activo?: boolean) => {
    setLoading(true);
    try {
      const result = await servicioOperativoService.getServicios({
        empresa_id: selectedEmpresaId ?? null,
        q: query,
        activo,
        limit: size,
        offset: (page - 1) * size,
      });
      setData(result.items);
      setTotal(result.total);
    } catch (err) {
      message.error('Error al cargar servicios operativos');
    } finally {
      setLoading(false);
    }
  }, [selectedEmpresaId]);

  useEffect(() => {
    fetchData(currentPage, pageSize, q, activoFiltro);
  }, [fetchData, currentPage, pageSize, q, activoFiltro]);

  // Reset to page 1 when empresa changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedEmpresaId]);

  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size) setPageSize(size);
  };

  const handleDelete = async (id: string) => {
    try {
      await servicioOperativoService.deleteServicio(id);
      message.success('Servicio eliminado');
      fetchData(currentPage, pageSize, q, activoFiltro);
    } catch {
      message.error('Error al eliminar servicio');
    }
  };

  const debouncedSearch = React.useMemo(
    () =>
      debounce((value: string) => {
        if (value.length === 0 || value.length >= 3) {
          setQ(value || undefined);
          setCurrentPage(1);
        }
      }, 500),
    []
  );

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchInput(e.target.value);
    debouncedSearch(e.target.value);
  };

  const columns: ColumnsType<ServicioOperativoOut> = [
    {
      title: 'Nombre',
      dataIndex: 'nombre',
      key: 'nombre',
      width: 200,
    },
    {
      title: 'Descripción',
      dataIndex: 'descripcion',
      key: 'descripcion',
      ellipsis: true,
      render: (val?: string | null) =>
        val ? (
          <Tooltip title={val}>
            <span>{val}</span>
          </Tooltip>
        ) : (
          <span style={{ color: token.colorTextDisabled }}>—</span>
        ),
    },
    {
      title: 'Duración (min)',
      dataIndex: 'duracion_estimada_min',
      key: 'duracion_estimada_min',
      width: 130,
      render: (val?: number | null) =>
        val != null ? val : <span style={{ color: token.colorTextDisabled }}>—</span>,
    },
    {
      title: 'Personal Req.',
      dataIndex: 'personal_requerido',
      key: 'personal_requerido',
      width: 120,
    },
    {
      title: 'Requiere Vehículo',
      dataIndex: 'requiere_vehiculo',
      key: 'requiere_vehiculo',
      width: 150,
      render: (val: boolean) =>
        val ? <Tag color="blue">Sí</Tag> : <Tag>No</Tag>,
    },
    {
      title: 'Activo',
      dataIndex: 'activo',
      key: 'activo',
      width: 90,
      render: (val: boolean) =>
        val ? (
          <Badge status="success" text="Activo" />
        ) : (
          <Badge status="default" text="Inactivo" />
        ),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 100,
      render: (_, record) => (
        <Space>
          <Tooltip title="Editar">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => router.push(`/servicios-operativos/form/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Eliminar">
            <Popconfirm
              title="¿Eliminar este servicio?"
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
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">Servicios Operativos</h1>
        </div>
        <div className="app-page-header__right">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/servicios-operativos/form')}
          >
            Agregar
          </Button>
        </div>
      </div>
      <div className="app-content" ref={containerRef}>
        <Card size="small" variant="borderless" styles={{ body: { padding: 12 } }} style={{ marginBottom: 8 }}>
          <div
            style={{
              position: 'sticky',
              top: 0,
              zIndex: 9,
              padding: '4px',
              background: token.colorBgContainer,
            }}
          >
            <Space wrap>
              {isAdmin && (
                <Select
                  placeholder="Todas las empresas"
                  style={{ width: 220 }}
                  allowClear
                  value={selectedEmpresaId}
                  onChange={(val) => {
                    const { setSelectedEmpresaId } = require('@/hooks/useEmpresaSelector');
                    // empresa change is handled via context
                  }}
                  disabled
                >
                  {empresas.map((e) => (
                    <Option key={e.id} value={e.id}>
                      {e.nombre_comercial || e.nombre}
                    </Option>
                  ))}
                </Select>
              )}
              <Input
                prefix={<SearchOutlined />}
                placeholder="Buscar (min 3 caracteres)"
                style={{ width: 260 }}
                value={searchInput}
                onChange={handleSearchChange}
                allowClear
              />
              <Select
                placeholder="Estado"
                style={{ width: 140 }}
                allowClear
                onChange={(val: boolean | undefined) => {
                  setActivoFiltro(val);
                  setCurrentPage(1);
                }}
              >
                <Option value={undefined}>Todos</Option>
                <Option value={true}>Activos</Option>
                <Option value={false}>Inactivos</Option>
              </Select>
            </Space>
          </div>
        </Card>

        <Table<ServicioOperativoOut>
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          scroll={{ x: 900, y: tableY }}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            onChange: handlePageChange,
            showSizeChanger: true,
            showTotal: (t) => `${t} registros`,
          }}
          locale={{ emptyText: 'No hay servicios operativos' }}
        />
      </div>
    </>
  );
};

export default ServiciosOperativosPage;
