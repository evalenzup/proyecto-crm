// pages/productos-servicios/index.tsx

import React, { useEffect, useState } from 'react';
import api from '@/lib/axios';
import { useRouter } from 'next/router';
import { Table, message, Button, Popconfirm, Space } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Layout } from '@/components/Layout';
import { PageContainer } from '@ant-design/pro-layout';
import { Breadcrumbs } from '@/components/Breadcrumb';

interface ProductoServicio {
  id: string;
  tipo: 'PRODUCTO' | 'SERVICIO';
  descripcion: string;
  cantidad: number;
  valor_unitario: number;
}

const ProductosServiciosPage: React.FC = () => {
  const router = useRouter();
  const [items, setItems] = useState<ProductoServicio[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<ProductoServicio[]>(
        `${process.env.NEXT_PUBLIC_API_URL}/productos-servicios/`
      );
      setItems(data);
    } catch {
      message.error('Error al cargar productos y servicios');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`${process.env.NEXT_PUBLIC_API_URL}/productos-servicios/${id}`);
      message.success('Eliminado correctamente');
      fetchData();
    } catch {
      message.error('Error al eliminar');
    }
  };

  const columns: ColumnsType<ProductoServicio> = [
    { title: 'Tipo', dataIndex: 'tipo', key: 'tipo' },
    { title: 'Descripción', dataIndex: 'descripcion', key: 'descripcion' },
    { title: 'Cantidad', dataIndex: 'cantidad', key: 'cantidad' },
    { title: 'Valor Unitario', dataIndex: 'valor_unitario', key: 'valor_unitario' },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => router.push(`/productos-servicios/form/${record.id}`)}
          />
          <Popconfirm
            title="¿Eliminar?"
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
    <Layout>
      <PageContainer
        title="Productos y Servicios"
        extra={
          <>
            <Breadcrumbs items={[{ path: '/productos-servicios', label: 'Productos y Servicios' }]} />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => router.push('/productos-servicios/form')}
              style={{ marginLeft: 12 }}
            >
              Agregar
            </Button>
          </>
        }
      >
        <Table<ProductoServicio>
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: 'No hay productos o servicios' }}
        />
      </PageContainer>
    </Layout>
  );
};

export default ProductosServiciosPage;
