import React, { useEffect, useState } from 'react';
import api from '@/lib/axios';
import { useRouter } from 'next/router';
import { Table, message, Button, Popconfirm, Space } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Empresa } from '@/types/empresa';
import { Breadcrumbs } from '@/components/Breadcrumb';

const EmpresasPage: React.FC = () => {
  const router = useRouter();
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchEmpresas = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Empresa[]>(
        `${process.env.NEXT_PUBLIC_API_URL}/empresas/`
      );
      setEmpresas(data);
    } catch {
      message.error('Error al cargar empresas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmpresas();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await api.delete(
        `${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}`
      );
      message.success('Empresa eliminada');
      fetchEmpresas();
    } catch {
      message.error('Error al eliminar empresa');
    }
  };

  const columns: ColumnsType<Empresa> = [
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
        <Table<Empresa>
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
