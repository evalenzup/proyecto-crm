// pages/tecnicos/index.tsx

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
import { tecnicoService, TecnicoOut, TipoPersonal } from '@/services/tecnicoService';

const { Option } = Select;

const TecnicosPage: React.FC = () => {
  const router = useRouter();
  const { token } = theme.useToken();
  const { containerRef, tableY } = useTableHeight();
  const { selectedEmpresaId, empresas, isAdmin } = useEmpresaSelector();

  const [data, setData] = useState<TecnicoOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchInput, setSearchInput] = useState('');
  const [q, setQ] = useState<string | undefined>(undefined);
  const [tipoPersonalFilter, setTipoPersonalFilter] = useState<TipoPersonal | undefined>(undefined);

  const fetchData = useCallback(
    async (page: number, size: number, query?: string) => {
      setLoading(true);
      try {
        const result = await tecnicoService.getTecnicos({
          empresa_id: selectedEmpresaId ?? null,
          q: query,
          tipo_personal: tipoPersonalFilter,
          limit: size,
          offset: (page - 1) * size,
        });
        setData(result.items);
        setTotal(result.total);
      } catch {
        message.error('Error al cargar el personal');
      } finally {
        setLoading(false);
      }
    },
    [selectedEmpresaId]
  );

  useEffect(() => {
    fetchData(currentPage, pageSize, q);
  }, [fetchData, currentPage, pageSize, q]);

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedEmpresaId, tipoPersonalFilter]);

  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size) setPageSize(size);
  };

  const handleDelete = async (id: string) => {
    try {
      await tecnicoService.deleteTecnico(id);
      message.success('Registro eliminado');
      fetchData(currentPage, pageSize, q);
    } catch {
      message.error('Error al eliminar el registro');
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

  const TIPO_PERSONAL_COLOR: Record<string, string> = {
    TECNICO: 'geekblue',
    ADMINISTRATIVO: 'purple',
    OPERATIVO: 'cyan',
    SUPERVISOR: 'orange',
    OTRO: 'default',
  };
  const TIPO_PERSONAL_LABEL: Record<string, string> = {
    TECNICO: 'Técnico',
    ADMINISTRATIVO: 'Administrativo',
    OPERATIVO: 'Operativo',
    SUPERVISOR: 'Supervisor',
    OTRO: 'Otro',
  };

  const columns: ColumnsType<TecnicoOut> = [
    {
      title: 'Nombre',
      dataIndex: 'nombre_completo',
      key: 'nombre_completo',
      width: 220,
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo_personal',
      key: 'tipo_personal',
      width: 130,
      render: (val: string) => (
        <Tag color={TIPO_PERSONAL_COLOR[val] ?? 'default'}>
          {TIPO_PERSONAL_LABEL[val] ?? val}
        </Tag>
      ),
    },
    {
      title: 'Puesto',
      dataIndex: 'puesto',
      key: 'puesto',
      width: 160,
      render: (val?: string | null) =>
        val ?? <span style={{ color: token.colorTextDisabled }}>—</span>,
    },
    {
      title: 'Celular',
      dataIndex: 'celular',
      key: 'celular',
      width: 130,
      render: (val?: string | null) =>
        val ?? <span style={{ color: token.colorTextDisabled }}>—</span>,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 200,
      render: (val?: string | null) =>
        val ?? <span style={{ color: token.colorTextDisabled }}>—</span>,
    },
    {
      title: 'Especialidades',
      key: 'especialidades',
      render: (_, record) => {
        const items = record.especialidades ?? [];
        const visible = items.slice(0, 2);
        const remaining = items.length - visible.length;
        return (
          <Space size={4} wrap>
            {visible.map((e) => (
              <Tag key={e.id} color="geekblue">
                {e.nombre}
              </Tag>
            ))}
            {remaining > 0 && (
              <Tooltip title={items.slice(2).map((e) => e.nombre).join(', ')}>
                <Tag>+{remaining}</Tag>
              </Tooltip>
            )}
          </Space>
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
      width: 100,
      render: (_, record) => (
        <Space>
          <Tooltip title="Editar">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => router.push(`/tecnicos/form/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Eliminar">
            <Popconfirm
              title="¿Eliminar este registro?"
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
          <h1 className="app-title">Personal</h1>
        </div>
        <div className="app-page-header__right">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/tecnicos/form')}
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
              <Input
                prefix={<SearchOutlined />}
                placeholder="Buscar por nombre (min 3 caracteres)"
                style={{ width: 280, minWidth: 180 }}
                value={searchInput}
                onChange={handleSearchChange}
                allowClear
              />
              <Select
                allowClear
                placeholder="Tipo de personal"
                style={{ width: 180, minWidth: 150 }}
                value={tipoPersonalFilter}
                onChange={(val) => {
                  setTipoPersonalFilter(val);
                  setCurrentPage(1);
                }}
              >
                <Option value="TECNICO">Técnico</Option>
                <Option value="ADMINISTRATIVO">Administrativo</Option>
                <Option value="OPERATIVO">Operativo</Option>
                <Option value="SUPERVISOR">Supervisor</Option>
                <Option value="OTRO">Otro</Option>
              </Select>
            </Space>
          </div>
        </Card>

        <Table<TecnicoOut>
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          scroll={{ x: 1000, y: tableY }}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            onChange: handlePageChange,
            showSizeChanger: true,
            showTotal: (t) => `${t} registros`,
          }}
          locale={{ emptyText: 'No hay personal registrado' }}
        />
      </div>
    </>
  );
};

export default TecnicosPage;
