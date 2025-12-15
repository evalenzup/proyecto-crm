// src/pages/empresas/index.tsx

import React from 'react';
import { useRouter } from 'next/router';
import { Table, message, Button, Popconfirm, Space, Tooltip, Input, Card, theme } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { EmpresaOut } from '@/services/empresaService'; // Usamos la interfaz del servicio
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEmpresasList } from '@/hooks/useEmpresasList'; // Importamos el hook
import { useAuth } from '@/context/AuthContext';
import { useTableHeight } from '@/hooks/useTableHeight';

const EmpresasPage: React.FC = () => {
  const router = useRouter();
  const { empresas, loading, handleDelete } = useEmpresasList(); // Usamos el hook
  const { token } = theme.useToken();
  const { user } = useAuth();
  const { containerRef, tableY } = useTableHeight();
  const [searchTerm, setSearchTerm] = React.useState('');

  const filteredEmpresas = React.useMemo(() => {
    if (!searchTerm) return empresas;
    const lower = searchTerm.toLowerCase();
    return empresas.filter(e =>
      (e.nombre_comercial || '').toLowerCase().includes(lower) ||
      (e.nombre || '').toLowerCase().includes(lower) ||
      (e.rfc || '').toLowerCase().includes(lower)
    );
  }, [empresas, searchTerm]);

  const columns: ColumnsType<EmpresaOut> = [
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    { title: 'Nombre Comercial', dataIndex: 'nombre_comercial', key: 'nombre_comercial' },
    { title: 'RFC', dataIndex: 'rfc', key: 'rfc' },
    { title: 'Teléfono', dataIndex: 'telefono', key: 'telefono' },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <Space>
          <Tooltip title="Editar">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => router.push(`/empresas/form/${record.id}`)}
            />
          </Tooltip>
          {user?.rol === 'admin' && (
            <Tooltip title="Eliminar">
              <Popconfirm
                title="¿Eliminar empresa?"
                onConfirm={() => handleDelete(record.id)}
                okText="Sí"
                cancelText="No"
              >
                <Button type="link" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">Empresas</h1>
        </div>
        <div className="app-page-header__right">
          {user?.rol === 'admin' && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => router.push('/empresas/form')}
            >
              Agregar
            </Button>
          )}
        </div>
      </div>
      <div className="app-content" ref={containerRef}>
        <Card size="small" bordered bodyStyle={{ padding: 12 }} style={{ marginBottom: 8 }}>
          <div style={{ position: 'sticky', top: 0, zIndex: 9, padding: '4px', background: token.colorBgContainer }}>
            <Input
              prefix={<SearchOutlined />}
              placeholder="Buscar por Nombre o RFC"
              style={{ width: 300 }}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              allowClear
            />
          </div>
        </Card>
        <Table<EmpresaOut> // Usamos EmpresaOut
          rowKey="id"
          columns={columns}
          dataSource={filteredEmpresas}
          loading={loading}
          scroll={{ x: 800, y: tableY }}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: 'No hay empresas' }}
        />
      </div>
    </>
  );
};

export default EmpresasPage;