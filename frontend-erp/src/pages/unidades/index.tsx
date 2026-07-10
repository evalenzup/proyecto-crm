// pages/unidades/index.tsx

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
import {
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  SearchOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { debounce } from 'lodash';
import type { ColumnsType } from 'antd/es/table';
import { PageHeader } from '@/components/PageHeader';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import { useTableHeight } from '@/hooks/useTableHeight';
import { unidadService, UnidadOut, TipoUnidad } from '@/services/unidadService';

const { Option } = Select;

const TIPO_COLOR: Record<TipoUnidad, string> = {
  SEDAN: 'blue',
  PICKUP: 'orange',
  CAMIONETA: 'green',
  MOTOCICLETA: 'purple',
  VAN: 'cyan',
  CAMION: 'geekblue',
  OTRO: 'default',
};

const UnidadesPage: React.FC = () => {
  const router = useRouter();
  const { token } = theme.useToken();
  const { containerRef, tableY } = useTableHeight();
  const { selectedEmpresaId, empresas, isAdmin } = useEmpresaSelector();

  const [data, setData] = useState<UnidadOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchInput, setSearchInput] = useState('');
  const [q, setQ] = useState<string | undefined>(undefined);
  const [activoFiltro, setActivoFiltro] = useState<boolean | undefined>(undefined);
  const [sort, setSort] = useState<{ order_by?: string; order_dir?: 'asc' | 'desc' }>({});

  const fetchData = useCallback(
    async (page: number, size: number, query?: string, activo?: boolean) => {
      setLoading(true);
      try {
        const result = await unidadService.getUnidades({
          empresa_id: selectedEmpresaId ?? null,
          q: query,
          activo,
          limit: size,
          offset: (page - 1) * size,
          order_by: sort.order_by,
          order_dir: sort.order_dir,
        });
        setData(result.items);
        setTotal(result.total);
      } catch {
        message.error('Error al cargar unidades');
      } finally {
        setLoading(false);
      }
    },
    [selectedEmpresaId, sort]
  );

  const so = (key: string): 'ascend' | 'descend' | undefined =>
    sort.order_by === key ? (sort.order_dir === 'asc' ? 'ascend' : 'descend') : undefined;
  const handleTableChange = (_pag: any, _filters: any, sorter: any) => {
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    const next = s && s.order
      ? { order_by: String(s.columnKey ?? s.field), order_dir: (s.order === 'ascend' ? 'asc' : 'desc') as 'asc' | 'desc' }
      : {};
    if (next.order_by !== sort.order_by || next.order_dir !== sort.order_dir) {
      setSort(next);
      setCurrentPage(1);
    }
  };

  useEffect(() => {
    fetchData(currentPage, pageSize, q, activoFiltro);
  }, [fetchData, currentPage, pageSize, q, activoFiltro]);

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedEmpresaId]);

  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size) setPageSize(size);
  };

  const handleDelete = async (id: string) => {
    try {
      await unidadService.deleteUnidad(id);
      message.success('Unidad eliminada');
      fetchData(currentPage, pageSize, q, activoFiltro);
    } catch {
      message.error('Error al eliminar unidad');
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

  const columns: ColumnsType<UnidadOut> = [
    {
      title: 'Nombre',
      dataIndex: 'nombre',
      key: 'nombre',
      width: 180,
      sorter: true,
      sortOrder: so('nombre'),
    },
    {
      title: 'Placa',
      dataIndex: 'placa',
      key: 'placa',
      width: 120,
      sorter: true,
      sortOrder: so('placa'),
      render: (val?: string | null) =>
        val ?? <span style={{ color: token.colorTextDisabled }}>—</span>,
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      width: 130,
      sorter: true,
      sortOrder: so('tipo'),
      render: (val: TipoUnidad) => (
        <Tag color={TIPO_COLOR[val] ?? 'default'}>{val}</Tag>
      ),
    },
    {
      title: 'Max Servicios/Día',
      dataIndex: 'max_servicios_dia',
      key: 'max_servicios_dia',
      width: 150,
      render: (val?: number | null) =>
        val != null ? val : <span style={{ color: token.colorTextDisabled }}>—</span>,
    },
    {
      title: 'Servicios Compatibles',
      key: 'servicios_compatibles',
      width: 180,
      render: (_, record) => {
        const items = record.servicios_compatibles ?? [];
        return (
          <Tooltip title={items.map((s) => s.nombre).join(', ') || 'Ninguno'}>
            <Tag>{items.length} servicio{items.length !== 1 ? 's' : ''}</Tag>
          </Tooltip>
        );
      },
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
      width: 140,
      render: (_, record) => (
        <Space>
          <Tooltip title="Editar">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => router.push(`/unidades/form/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Mantenimientos">
            <Button
              type="link"
              icon={<ToolOutlined />}
              onClick={() => router.push(`/unidades/${record.id}/mantenimientos`)}
            />
          </Tooltip>
          <Tooltip title="Eliminar">
            <Popconfirm
              title="¿Eliminar esta unidad?"
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
        title="Unidades"
        extra={
          <>
            <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/unidades/form')}
          >
            Agregar
          </Button>
          </>
        }
      />
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
              <Input
                prefix={<SearchOutlined />}
                placeholder="Buscar (min 3 caracteres)"
                style={{ width: 260, minWidth: 170 }}
                value={searchInput}
                onChange={handleSearchChange}
                allowClear
              />
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
                <Option value={true}>Activos</Option>
                <Option value={false}>Inactivos</Option>
              </Select>
            </Space>
          </div>
        </Card>

        <Table<UnidadOut>
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          scroll={{ x: 1000, y: tableY }}
          onChange={handleTableChange}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            onChange: handlePageChange,
            showSizeChanger: true,
            showTotal: (t) => `${t} registros`,
          }}
          locale={{ emptyText: 'No hay unidades registradas' }}
        />
      </div>
    </>
  );
};

export default UnidadesPage;
