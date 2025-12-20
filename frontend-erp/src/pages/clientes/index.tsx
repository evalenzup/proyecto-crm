// src/pages/clientes/index.tsx

import React from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Popconfirm, Space, Select, Input, message, Tooltip, Card, theme, AutoComplete } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, SearchOutlined, FileExcelOutlined } from '@ant-design/icons';
import { debounce } from 'lodash';
import { Spin } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useClienteList } from '@/hooks/useClienteList'; // Importamos el hook
import { ClienteOut, clienteService } from '@/services/clienteService'; // Importamos la interfaz ClienteOut
import { EmpresaOut } from '@/services/empresaService'; // Importamos la interfaz EmpresaOut
import { useTableHeight } from '@/hooks/useTableHeight';

const { Option } = Select;

const ClientesPage: React.FC = () => {
  const router = useRouter();
  const { token } = theme.useToken();
  const { containerRef, tableY } = useTableHeight();
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
    isAdmin, // Nuevo
  } = useClienteList();

  const [clienteOptions, setClienteOptions] = React.useState<ClienteOut[]>([]);
  const [fetchingClientes, setFetchingClientes] = React.useState(false);

  const handleSearchClientes = React.useMemo(() => {
    const loadOptions = async (value: string) => {
      if (value.length < 3) {
        setClienteOptions([]);
        return;
      }
      setFetchingClientes(true); // set loading state
      try {
        // Buscamos clientes globalmente o por empresa seleccionada
        const results = await clienteService.buscarClientes(value, empresaFiltro || undefined);
        setClienteOptions(results);
      } catch (error) {
        console.error(error);
      } finally {
        setFetchingClientes(false);
      }
    };
    return debounce(loadOptions, 800);
  }, [empresaFiltro]);

  const handleExport = async () => {
    try {
      const blob = await clienteService.exportClientesExcel({
        empresa_id: empresaFiltro || undefined,
        rfc: rfcFiltro || undefined,
        nombre_comercial: nombreFiltro || undefined,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'clientes.xlsx';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      message.error('Error al exportar clientes');
    }
  };

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
          <Tooltip title="Editar">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => router.push(`/clientes/form/${record.id}`)}
            />
          </Tooltip>
          <Tooltip title="Eliminar">
            <Popconfirm
              title="¿Eliminar cliente?"
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
          <h1 className="app-title">Clientes</h1>
        </div>
        <div className="app-page-header__right">
          <Space>
            <Button icon={<FileExcelOutlined />} style={{ color: 'green', borderColor: 'green' }} onClick={handleExport}>
              Exportar
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => router.push('/clientes/form')}
            >
              Agregar
            </Button>
          </Space>
        </div>
      </div>
      <div className="app-content" ref={containerRef}>
        <Card size="small" variant="borderless" styles={{ body: { padding: 12 } }} style={{ marginBottom: 8 }}>
          <div style={{ position: 'sticky', top: 0, zIndex: 9, padding: '4px', background: token.colorBgContainer }}>
            <Space wrap>
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
              <Input
                placeholder="RFC (min 3 letras)"
                prefix={<SearchOutlined />}
                value={rfcFiltro}
                onChange={(e) => setRfcFiltro(e.target.value)}
                style={{ width: 200 }}
              />
              <AutoComplete
                style={{ width: 500 }}
                placeholder="Nombre Comercial (min 3 letras)"
                onSearch={handleSearchClientes}
                onChange={(val) => setNombreFiltro(val)}
                value={nombreFiltro}
                allowClear
                options={clienteOptions.map((c) => ({
                  value: c.nombre_comercial,
                  label: `${c.nombre_comercial} (${c.rfc})`,
                }))}
              />
            </Space>
          </div>
        </Card>

        <Table<ClienteOut>
          rowKey="id"
          columns={columns}
          dataSource={clientes}
          loading={loading}
          scroll={{ x: 1000, y: tableY }}
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
