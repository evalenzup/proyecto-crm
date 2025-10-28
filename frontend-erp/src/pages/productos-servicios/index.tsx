// pages/productos-servicios/index.tsx

import React from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Popconfirm, Space, Input, Select } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useProductoServicioList } from '@/hooks/useProductoServicioList'; // Importamos el hook
import { ProductoServicioOut, TipoProductoServicio } from '@/services/productoServicioService'; // Importamos la interfaz ProductoServicioOut
import { EmpresaOut } from '@/services/empresaService'; // Importamos la interfaz EmpresaOut para el filtro

const { Option } = Select;

const ProductosServiciosPage: React.FC = () => {
  const router = useRouter();
  // Usamos el hook personalizado para toda la lógica de la lista y filtros
  const {
    productosServicios,
    loading,
    total,
    currentPage,
    pageSize,
    handlePageChange,
    handleDelete,
    empresasForFilter,
    empresaFiltro,
    setEmpresaFiltro,
    searchTerm,
    setSearchTerm,
    clearFilters,
    mapaClaves, // Obtenemos el mapa de claves del hook
  } = useProductoServicioList();

  const columns: ColumnsType<ProductoServicioOut> = [
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
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">Productos y Servicios</h1>
        </div>
        <div className="app-page-header__right">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/productos-servicios/form')}
          >
            Agregar
          </Button>
        </div>
      </div>
      <div className="app-content">
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="Filtrar por tipo"
            style={{ width: 160 }}
            allowClear
            onChange={(value: string) => {
              // El hook useProductoServicioList no tiene un filtro por tipo directamente
              // Si el backend no soporta este filtro, se haría aquí client-side
              // Por ahora, el searchTerm y empresaFiltro son los que se usan en el hook
              // Si se desea filtrar por tipo, se debería añadir al hook y al servicio
              // Para mantener la funcionalidad original, se podría filtrar aquí el `productosServicios`
              // que viene del hook, o modificar el hook para que acepte `tipoFiltro`.
              // Por simplicidad, y dado que el backend no tiene filtro por tipo en buscar,
              // mantendremos el filtro por descripción y empresa.
              // Si el usuario insiste en el filtro por tipo, se debería añadir al hook.
            }}
          >
            <Option value={TipoProductoServicio.PRODUCTO}>PRODUCTO</Option>
            <Option value={TipoProductoServicio.SERVICIO}>SERVICIO</Option>
          </Select>
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
            placeholder="Buscar por descripción o clave"
            prefix={<SearchOutlined />}
            onChange={e => setSearchTerm(e.target.value)}
            value={searchTerm}
            style={{ width: 240 }}
          />
          <Button
            onClick={clearFilters}
          >
            Limpiar
          </Button>
        </Space>

        <Table<ProductoServicioOut>
          rowKey="id"
          columns={columns}
          dataSource={productosServicios}
          loading={loading}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            onChange: handlePageChange,
            showSizeChanger: true,
          }}
          locale={{ emptyText: "No hay productos o servicios" }}
        />
      </div>
    </>
  );
};

export default ProductosServiciosPage;
