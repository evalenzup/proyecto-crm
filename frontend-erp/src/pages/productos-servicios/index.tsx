// pages/productos-servicios/index.tsx

import React from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Popconfirm, Space, Input, Select, Tooltip, Card, theme, AutoComplete } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { debounce } from 'lodash';
import { Spin } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useProductoServicioList } from '@/hooks/useProductoServicioList'; // Importamos el hook
import { ProductoServicioOut, TipoProductoServicio, productoServicioService } from '@/services/productoServicioService'; // Importamos la interfaz ProductoServicioOut
import { EmpresaOut } from '@/services/empresaService'; // Importamos la interfaz EmpresaOut para el filtro
import { useTableHeight } from '@/hooks/useTableHeight';

const { Option } = Select;

const ProductosServiciosPage: React.FC = () => {
  const router = useRouter();
  const { token } = theme.useToken();
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
    empresasForFilter,
    empresaFiltro,
    setEmpresaFiltro,
    searchTerm,
    setSearchTerm,
    clearFilters,
    mapaClaves,
    isAdmin, // Nuevo
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
      <div className="app-content" ref={containerRef}>
        <Card size="small" variant="borderless" styles={{ body: { padding: 12 } }} style={{ marginBottom: 8 }}>
          <div style={{ position: 'sticky', top: 0, zIndex: 9, padding: '4px', background: token.colorBgContainer }}>
            <Space wrap>
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
                disabled={!isAdmin} // Deshabilitar si no es admin
              >
                {empresasForFilter.map((emp: EmpresaOut) => (
                  <Option key={emp.id} value={emp.id}>
                    {emp.nombre_comercial}
                  </Option>
                ))}
              </Select>
              <AutoComplete
                style={{ width: 500 }}
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
            </Space>
          </div>
        </Card>

        <Table<ProductoServicioOut>
          rowKey="id"
          columns={columns}
          dataSource={productosServicios}
          loading={loading}
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
