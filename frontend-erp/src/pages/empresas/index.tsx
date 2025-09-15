import React from 'react';
import { useRouter } from 'next/router';
import { Table, message, Button, Popconfirm, Space } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { EmpresaOut } from '@/services/empresaService'; // Usamos la interfaz del servicio
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEmpresasList } from '@/hooks/useEmpresasList'; // Importamos el hook

const EmpresasPage: React.FC = () => {
  const router = useRouter();
  const { empresas, loading, handleDelete } = useEmpresasList(); // Usamos el hook

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
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => router.push(`/empresas/form/${record.id}`)}
          />
          <Popconfirm
            title="¿Eliminar empresa?"
            onConfirm={() => handleDelete(record.id)}
            okText="Sí"
            cancelText="No"
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
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
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/empresas/form')}
          >
            Agregar
          </Button>
        </div>
      </div>
      <div className="app-content">
        <Table<EmpresaOut> // Usamos EmpresaOut
          rowKey="id"
          columns={columns}
          dataSource={empresas}
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: 'No hay empresas' }}
        />
      </div>
    </>
  );
};

export default EmpresasPage;