// pages/productos-servicios/index.tsx

import React from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Popconfirm, Space, Input, Select, Tooltip, AutoComplete } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { debounce } from 'lodash';
import { Spin } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PageHeader } from '@/components/PageHeader';
import { FilterBar } from '@/components/FilterBar';
import { useProductoServicioList } from '@/hooks/useProductoServicioList'; // Importamos el hook
import { ProductoServicioOut, TipoProductoServicio, productoServicioService } from '@/services/productoServicioService'; // Importamos la interfaz ProductoServicioOut
import { useTableHeight } from '@/hooks/useTableHeight';

const { Option } = Select;

const ProductosServiciosPage: React.FC = () => {
  const router = useRouter();
  const { containerRef, tableY } = useTableHeight();
  // Usamos el hook personalizado para toda la lógica de la lista y filtros
  const {
    productosServicios,
    loading,
    total,
    currentPage,
    pageSize,
    handlePageChange,
    handleDelete,
    empresaFiltro,
    searchTerm,
    setSearchTerm,
    clearFilters,
    mapaClaves,
  } = useProductoServicioList();

  const [productOptions, setProductOptions] = React.useState<ProductoServicioOut[]>([]);
  const [fetchingProducts, setFetchingProducts] = React.useState(false);

  const handleSearchProducts = React.useMemo(() => {
    const loadOptions = async (value: string) => {
      if (value.length < 3) {
        setProductOptions([]);
        return;
      }
      setFetchingProducts(true);
      try {
        const results = await productoServicioService.buscarProductoServicios(value, empresaFiltro || undefined);
        setProductOptions(results);
      } catch (error) {
        console.error(error);
      } finally {
        setFetchingProducts(false);
      }
    };
    return debounce(loadOptions, 800);
  }, [empresaFiltro]);

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
          <Tooltip title="Editar">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => router.push(`/productos-servicios/form/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Eliminar">
            <Popconfirm
              title="¿Eliminar?"
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
      <PageHeader
        title="Productos y Servicios"
        extra={
          <>
            <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/productos-servicios/form')}
          >
            Agregar
          </Button>
          </>
        }
      />
      <div className="app-content" ref={containerRef}>
        <FilterBar>
          <Select
            placeholder="Filtrar por tipo"
            style={{ width: 160, minWidth: 140 }}
            allowClear
            onChange={(value: string) => {
              // El hook useProductoServicioList no tiene un filtro por tipo directamente
              // Si el backend no soporta este filtro, se haría aquí client-side
              // Por ahora, el searchTerm y empresaFiltro son los que se usan en el hook
            }}
          >
            <Option value={TipoProductoServicio.PRODUCTO}>PRODUCTO</Option>
            <Option value={TipoProductoServicio.SERVICIO}>SERVICIO</Option>
          </Select>
          <AutoComplete
            style={{ width: 500, minWidth: 200 }}
            placeholder="Descripción/Clave (min 3 letras)"
            onSearch={handleSearchProducts}
            onChange={(val: string) => setSearchTerm(val)}
            value={searchTerm}
            allowClear
            options={productOptions.map((p) => ({
              value: p.descripcion,
              label: `${p.clave_producto} - ${p.descripcion}`,
            }))}
          />
        </FilterBar>

        <Table<ProductoServicioOut>
          rowKey="id"
          columns={columns}
          dataSource={productosServicios}
          loading={loading}
          virtual
          scroll={{ x: 1000, y: tableY }}
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
