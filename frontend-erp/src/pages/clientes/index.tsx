// src/pages/clientes/index.tsx

import React from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Popconfirm, Space, Select, Input } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useClienteList } from '@/hooks/useClienteList'; // Importamos el hook
import { ClienteOut } from '@/services/clienteService'; // Importamos la interfaz ClienteOut
import { EmpresaOut } from '@/services/empresaService'; // Importamos la interfaz EmpresaOut

const { Option } = Select;

const ClientesPage: React.FC = () => {
  const router = useRouter();
  // Usamos el hook personalizado para toda la lógica de la lista y filtros
  const {
    clientes,
    loading,
    total,
    currentPage,
    pageSize,
    handlePageChange,
    handleDelete,
    empresasForFilter,
    empresaFiltro,
    setEmpresaFiltro,
    rfcFiltro,
    setRfcFiltro,
    nombreFiltro,
    setNombreFiltro,
    clearFilters,
  } = useClienteList();

  const columns: ColumnsType<ClienteOut> = [
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
            {empresasForFilter.map((emp: EmpresaOut) => (
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
            onClick={clearFilters} // Usamos la función del hook
          >
            Limpiar
          </Button>
        </Space>

        <Table<ClienteOut>
          rowKey="id"
          columns={columns}
          dataSource={clientes}
          loading={loading}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            onChange: handlePageChange,
            showSizeChanger: true,
          }}
          locale={{ emptyText: "No hay clientes" }}
        />
      </div>
    </>
  );
};

export default ClientesPage;
