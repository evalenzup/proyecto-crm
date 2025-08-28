// src/pages/clientes/index.tsx

import React, { useEffect, useState } from 'react';
import api from '@/lib/axios';
import { useRouter } from 'next/router';
import { Table, message, Button, Popconfirm, Space, Select, Input } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';

const { Option } = Select;

interface Empresa {
  id: string;
  nombre_comercial: string;
}

interface Cliente {
  id: string;
  nombre_comercial: string;
  nombre_razon_social: string;
  rfc: string;
  telefono?: string[];        // o string[], según tu schema
  actividad?: string;
  empresas: Empresa[];        // ahora sabemos que vienen como objetos
}

const ClientesPage: React.FC = () => {
  const router = useRouter();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(false);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [empresaFiltro, setEmpresaFiltro] = useState<string | null>(null);
  const [rfcFiltro, setRfcFiltro] = useState<string>('');
  const [nombreFiltro, setNombreFiltro] = useState<string>('');

  const fetchAllClientes = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Cliente[]>('/clientes/');
      setClientes(data);
    } catch {
      message.error('Error al cargar clientes');
    } finally {
      setLoading(false);
    }
  };

  const fetchEmpresas = async () => {
    try {
      const { data } = await api.get<Empresa[]>('/empresas/');
      setEmpresas(data);
    } catch {
      message.error('Error al cargar empresas');
    }
  };

  useEffect(() => {
    fetchAllClientes();
    fetchEmpresas();
  }, []);

  const filteredClientes = clientes.filter((cliente) => {
    // Filtrar por empresa seleccionada
    if (empresaFiltro) {
      const pertenece = cliente.empresas.some((e) => e.id === empresaFiltro);
      if (!pertenece) return false;
    }
    // Filtrar por RFC
    if (rfcFiltro && !cliente.rfc.toLowerCase().includes(rfcFiltro.toLowerCase())) {
      return false;
    }
    // Filtrar por nombre comercial
    if (
      nombreFiltro &&
      !cliente.nombre_comercial.toLowerCase().includes(nombreFiltro.toLowerCase())
    ) {
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
    {
      title: 'Teléfono',
      dataIndex: 'telefono',
      key: 'telefono',
      render: (t) => (t ? t.join(', ') : ''),
    },
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
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">Clientes</h1>
        </div>
        <div className="app-page-header__right">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/clientes/form')}
          >
            Agregar
          </Button>
        </div>
      </div>
      <div className="app-content">
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="Filtrar por Empresa"
            style={{ width: 220 }}
            allowClear
            onChange={setEmpresaFiltro}
            value={empresaFiltro}
          >
            {empresas.map((emp) => (
              <Option key={emp.id} value={emp.id}>
                {emp.nombre_comercial}
              </Option>
            ))}
          </Select>
          <Input
            placeholder="Buscar por RFC"
            prefix={<SearchOutlined />}
            value={rfcFiltro}
            onChange={(e) => setRfcFiltro(e.target.value)}
            style={{ width: 200 }}
          />
          <Input
            placeholder="Buscar por Nombre Comercial"
            prefix={<SearchOutlined />}
            value={nombreFiltro}
            onChange={(e) => setNombreFiltro(e.target.value)}
            style={{ width: 200 }}
          />
          <Button
            onClick={() => {
              setEmpresaFiltro(null);
              setRfcFiltro('');
              setNombreFiltro('');
            }}
          >
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
      </div>
    </>
  );
};

export default ClientesPage;