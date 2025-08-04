import React, { useEffect, useState } from 'react';
import api from '@/lib/axios';
import { useRouter } from 'next/router';
import { Table, message, Button, Popconfirm, Space, Select, Input } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Layout } from '@/components/Layout';
import { PageContainer } from '@ant-design/pro-layout';
import type { Cliente } from '@/types/clientes';
import { Breadcrumbs } from '@/components/Breadcrumb';

const { Option } = Select;

interface Empresa {
  id: string;
  nombre_comercial: string;
}

const ClientesPage: React.FC = () => {
  const router = useRouter();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(false);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [empresaFiltro, setEmpresaFiltro] = useState<string | null>(null);
  const [rfcFiltro, setRfcFiltro] = useState<string>('');
  const [nombreComercialFiltro, setNombreComercialFiltro] = useState<string>('');

  const fetchAllClientes = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Cliente[]>('/clientes/all');
      setClientes(data);
    } catch {
      message.error('Error al cargar clientes');
    } finally {
      setLoading(false);
    }
  };

  const fetchEmpresas = async () => {
    try {
      const { data } = await api.get<Empresa[]>('/empresas');
      setEmpresas(data);
    } catch {
      message.error('Error al cargar empresas');
    }
  };

  useEffect(() => {
    fetchAllClientes();
    fetchEmpresas();
  }, []);

  const filteredClientes = clientes.filter(cliente => {
    if (empresaFiltro && !cliente.empresas.includes(empresaFiltro)) {
      return false;
    }
    if (rfcFiltro && !cliente.rfc.toLowerCase().includes(rfcFiltro.toLowerCase())) {
      return false;
    }
    if (nombreComercialFiltro && !cliente.nombre_comercial.toLowerCase().includes(nombreComercialFiltro.toLowerCase())) {
      return false;
    }
    return true;
  });

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/clientes/${id}`);
      message.success('Cliente eliminado');
      fetchAllClientes();
    } catch {
      message.error('Error al eliminar cliente');
    }
  };

  const columns: ColumnsType<Cliente> = [
    { title: 'Nombre Comercial', dataIndex: 'nombre_comercial', key: 'nombre_comercial' },
    { title: 'Nombre Fiscal', dataIndex: 'nombre_razon_social', key: 'nombre_razon_social' },
    { title: 'RFC', dataIndex: 'rfc', key: 'rfc' },
    { title: 'Teléfono', dataIndex: 'telefono', key: 'telefono' },
    { title: 'Actividad', dataIndex: 'actividad', key: 'actividad' },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => router.push(`/clientes/form/${record.id}`)}
          />
          <Popconfirm
            title="¿Eliminar cliente?"
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
        title="Lista de Clientes Registrados"
        subTitle=""
        extra={
          <>
            <Breadcrumbs items={[{ path: '/clientes', label: 'Clientes' }]} />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => router.push('/clientes/form')}
              style={{ marginLeft: 12 }}
            >
              Agregar
            </Button>
          </>
        }
      >
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="Filtrar por Empresa"
            style={{ width: 200 }}
            allowClear
            onChange={setEmpresaFiltro}
            value={empresaFiltro}
          >
            {empresas.map(empresa => (
              <Option key={empresa.id} value={empresa.id}>
                {empresa.nombre_comercial}
              </Option>
            ))}
          </Select>
          <Input
            placeholder="Buscar por RFC"
            prefix={<SearchOutlined />}
            value={rfcFiltro}
            onChange={e => setRfcFiltro(e.target.value)}
            style={{ width: 200 }}
          />
          <Input
            placeholder="Buscar por Nombre Comercial"
            prefix={<SearchOutlined />}
            value={nombreComercialFiltro}
            onChange={e => setNombreComercialFiltro(e.target.value)}
            style={{ width: 200 }}
          />
           <Button onClick={() => {
            setEmpresaFiltro(null);
            setRfcFiltro('');
            setNombreComercialFiltro('');
          }}>
            Limpiar
          </Button>
        </Space>
        <Table<Cliente>
          rowKey="id"
          columns={columns}
          dataSource={filteredClientes}
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: 'No hay clientes' }}
        />
      </PageContainer>
    </Layout>
  );
};

export default ClientesPage;
