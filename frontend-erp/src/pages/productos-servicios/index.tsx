// pages/productos-servicios/index.tsx

import React, { useEffect, useState } from 'react';
import api from '@/lib/axios';
import { useRouter } from 'next/router';
import { Table, message, Button, Popconfirm, Space, Input, Select } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Layout } from '@/components/Layout';
import { PageContainer } from '@ant-design/pro-layout';
import { Breadcrumbs } from '@/components/Breadcrumb';

const { Option } = Select;

interface ProductoServicio {
  id: string;
  tipo: 'PRODUCTO' | 'SERVICIO';
  descripcion: string;
  clave_producto: string;
  clave_unidad: string;
}

const ProductosServiciosPage: React.FC = () => {
  const router = useRouter();
  const [items, setItems] = useState<ProductoServicio[]>([]);
  const [loading, setLoading] = useState(false);
  const [mapaClaves, setMapaClaves] = useState<Record<string, string>>({});
  const [tipoFiltro, setTipoFiltro] = useState<string | undefined>();
  const [descripcionFiltro, setDescripcionFiltro] = useState<string>("");

  const fetchDescripciones = async (items: ProductoServicio[]) => {
    const clavesProd = [...new Set(items.map(i => i.clave_producto))];
    const clavesUni = [...new Set(items.map(i => i.clave_unidad))];
    const mapa: Record<string, string> = {};

    try {
      const [prodData, uniData] = await Promise.all([
        Promise.all(clavesProd.map(c => api.get(`/catalogos/descripcion/producto/${c}`))),
        Promise.all(clavesUni.map(c => api.get(`/catalogos/descripcion/unidad/${c}`))),
      ]);

      for (const res of prodData) {
        mapa[res.data.clave] = res.data.descripcion;
      }
      for (const res of uniData) {
        mapa[res.data.clave] = res.data.descripcion;
      }
    } catch {
      message.warning('No se pudo obtener descripción de claves');
    }

    setMapaClaves(mapa);
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<ProductoServicio[]>(`${process.env.NEXT_PUBLIC_API_URL}/productos-servicios/`);
      setItems(data);
      await fetchDescripciones(data);
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

  const filteredItems = items.filter(item =>
    (!tipoFiltro || item.tipo === tipoFiltro) &&
    item.descripcion.toLowerCase().includes(descripcionFiltro.toLowerCase())
  );

  const columns: ColumnsType<ProductoServicio> = [
    { title: 'Tipo', dataIndex: 'tipo', key: 'tipo' },
    { title: 'Descripción', dataIndex: 'descripcion', key: 'descripcion' },
    {
      title: 'Clave Producto',
      dataIndex: 'clave_producto',
      key: 'clave_producto',
      render: (clave: string) => `${clave} - ${mapaClaves[clave] || '...'}`
    },
    {
      title: 'Unidad de Medida',
      dataIndex: 'clave_unidad',
      key: 'clave_unidad',
      render: (clave: string) => `${clave} - ${mapaClaves[clave] || '...'}`
    },
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
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="Filtrar por tipo"
            style={{ width: 160 }}
            allowClear
            onChange={setTipoFiltro}
          >
            <Option value="PRODUCTO">PRODUCTO</Option>
            <Option value="SERVICIO">SERVICIO</Option>
          </Select>
          <Input
            placeholder="Buscar por descripción"
            prefix={<SearchOutlined />}
            onChange={e => setDescripcionFiltro(e.target.value)}
            style={{ width: 240 }}
          />
        </Space>

        <Table<ProductoServicio>
          rowKey="id"
          columns={columns}
          dataSource={filteredItems}
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: 'No hay productos o servicios' }}
        />
      </PageContainer>
    </Layout>
  );
};

export default ProductosServiciosPage;