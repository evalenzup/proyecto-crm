// src/pages/egresos/index.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Space, Tag, message, Input, Select, DatePicker, Card, Pagination, Tooltip, theme, Grid } from 'antd';
import { PlusOutlined, EditOutlined, PaperClipOutlined, FileExcelOutlined } from '@ant-design/icons';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { getEgresos, Egreso, getEgresoEnums, exportEgresosExcel, searchProveedores } from '@/services/egresoService';
import { debounce } from 'lodash';
import { Spin } from 'antd';
import api from '@/lib/axios';
import { getEmpresas } from '@/services/facturaService';

const { RangePicker } = DatePicker;

import { useEmpresaSelector } from '@/hooks/useEmpresaSelector'; // Importar hook
import { useTableHeight } from '@/hooks/useTableHeight';
const { useToken } = theme;
const { useBreakpoint } = Grid;

const EgresosListPage: React.FC = () => {
  const router = useRouter();
  const { containerRef, tableY } = useTableHeight();
  const { token } = useToken();
  const screens = useBreakpoint();
  const [egresos, setEgresos] = useState<Egreso[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const {
    selectedEmpresaId,
    setSelectedEmpresaId,
    empresas,
    isAdmin
  } = useEmpresaSelector();

  const [filters, setFilters] = useState<any>({
    proveedor: null,
    categoria: null,
    estatus: null,
    fecha_desde: null,
    fecha_hasta: null,
  });

  // Data for filters
  // const [empresas, setEmpresas] = useState<{ label: string, value: string }[]>([]); // YA NO SE USA
  const [categorias, setCategorias] = useState<string[]>([]);
  const [estatusOptions, setEstatusOptions] = useState<string[]>([]);
  const [proveedorOptions, setProveedorOptions] = useState<string[]>([]);
  const [fetchingProveedores, setFetchingProveedores] = useState(false);

  // Debounced provider search
  const handleSearchProveedores = useMemo(() => {
    const loadOptions = async (value: string) => {
      if (value.length < 3) {
        setProveedorOptions([]);
        return;
      }
      setFetchingProveedores(true);
      try {
        const results = await searchProveedores(value);
        setProveedorOptions(results);
      } catch (error) {
        console.error(error);
      } finally {
        setFetchingProveedores(false);
      }
    };
    return debounce(loadOptions, 800);
  }, []);

  const fetchEgresos = async () => {
    if (!selectedEmpresaId) {
      setEgresos([]);
      setTotal(0);
      return;
    }

    setLoading(true);
    try {
      const response = await getEgresos({
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        empresa_id: selectedEmpresaId, // Usar del hook
        ...filters,
      });
      setEgresos(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('Error al cargar los egresos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Ya no usamos localStorage manual para empresa
    // if (selectedEmpresaId) {
    //   setFilters((prev: any) => ({ ...prev, empresa_id: selectedEmpresaId }));
    // }

    const fetchFilterData = async () => {
      try {
        const [enumsData] = await Promise.all([
          // getEmpresas(), // YA NO SE USA
          getEgresoEnums(),
        ]);
        // setEmpresas((empresasData || []).map((e: any) => ({ label: e.nombre_comercial || e.nombre, value: e.id })));
        setCategorias(enumsData.categorias);
        setEstatusOptions(enumsData.estatus);
      } catch (error) {
        message.error('Error al cargar datos para filtros.');
      }
    };
    fetchFilterData();
  }, []);

  useEffect(() => {
    fetchEgresos();
  }, [filters, currentPage, pageSize, selectedEmpresaId]); // Agregar dependency

  const handleFilterChange = (key: string, value: any) => {
    // Empresa se maneja aparte
    setFilters((prev: any) => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Reset page when filters change
  };

  const handleDateChange = (dates: any) => {
    setFilters((prev: any) => ({
      ...prev,
      fecha_desde: dates ? dates[0].format('YYYY-MM-DD') : null,
      fecha_hasta: dates ? dates[1].format('YYYY-MM-DD') : null,
    }));
    setCurrentPage(1); // Reset page when filters change
  };

  const handleExport = async () => {
    try {
      const blob = await exportEgresosExcel({
        empresa_id: selectedEmpresaId || undefined,
        proveedor: filters.proveedor || undefined,
        categoria: filters.categoria || undefined,
        estatus: filters.estatus || undefined,
        fecha_desde: filters.fecha_desde || undefined,
        fecha_hasta: filters.fecha_hasta || undefined,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'egresos.xlsx';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      message.error('Error al exportar egresos');
    }
  };



  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size && size !== pageSize) {
      setPageSize(size);
    }
  };

  const sumatoriaMostrada = React.useMemo(
    () => egresos.reduce((acc, r) => acc + (Number(r.monto) || 0), 0),
    [egresos]
  );

  const columns = [
    {
      title: 'Fecha',
      dataIndex: 'fecha_egreso',
      key: 'fecha_egreso',
      render: (text: string) => new Date(text).toLocaleDateString(),
    },
    {
      title: 'Proveedor',
      dataIndex: 'proveedor',
      key: 'proveedor',
    },
    {
      title: 'Descripción',
      dataIndex: 'descripcion',
      key: 'descripcion',
    },
    {
      title: 'Monto',
      dataIndex: 'monto',
      key: 'monto',
      align: 'right' as const,
      render: (amount: number, record: Egreso) =>
        `${amount.toLocaleString('es-MX', { style: 'currency', currency: record.moneda || 'MXN' })}`,
    },
    {
      title: 'Categoría',
      dataIndex: 'categoria',
      key: 'categoria',
    },
    {
      title: 'Estatus',
      dataIndex: 'estatus',
      key: 'estatus',
      render: (status: string) => {
        let color = 'default';
        if (status === 'Pagado') color = 'success';
        if (status === 'Cancelado') color = 'error';
        if (status === 'Pendiente') color = 'warning';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_: any, record: Egreso) => (
        <Space size="middle">
          <Tooltip title="Editar">
            <Button icon={<EditOutlined />} onClick={() => router.push(`/egresos/form/${record.id}`)} />
          </Tooltip>
          {record.path_documento && (
            <Tooltip title="Ver Documento">
              <Button
                icon={<PaperClipOutlined />}
                onClick={() => {
                  const apiUrl = api.defaults.baseURL || '';
                  const baseUrl = apiUrl.endsWith('/api') ? apiUrl.slice(0, -4) : apiUrl;
                  window.open(`${baseUrl}/data/${record.path_documento}`, '_blank');
                }}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">Egresos</h1>
        </div>
        <div className="app-page-header__right">
          <Space>
            <Button icon={<FileExcelOutlined />} style={{ color: 'green', borderColor: 'green' }} onClick={handleExport}>
              Exportar
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => router.push('/egresos/form')}
            >
              Nuevo Egreso
            </Button>
          </Space>
        </div>
      </div>
      <div className="app-content" ref={containerRef}>
        <Card size="small" variant="borderless" styles={{ body: { padding: 12 } }} style={{ marginBottom: 4 }}>
          <div style={{ position: 'sticky', top: 0, zIndex: 9, padding: screens.lg ? '4px' : '8px', background: token.colorBgContainer }}>
            <Space wrap>
              <Select
                placeholder="Empresa"
                style={{ width: 200 }}
                allowClear
                options={empresas.map(e => ({ label: e.nombre_comercial, value: e.id }))}
                value={selectedEmpresaId}
                onChange={setSelectedEmpresaId}
                disabled={!isAdmin}
              />
              <Select
                showSearch
                placeholder="Nombre Proveedor (min 3 letras)"
                style={{ width: 250 }}
                filterOption={false}
                onSearch={handleSearchProveedores}
                onChange={(value) => handleFilterChange('proveedor', value)}
                notFoundContent={fetchingProveedores ? <Spin size="small" /> : null}
                options={proveedorOptions.map(p => ({ label: p, value: p }))}
                allowClear
                onClear={() => {
                  setProveedorOptions([]);
                  handleFilterChange('proveedor', null);
                }}
                value={filters.proveedor || undefined}
              />
              <Select
                placeholder="Categoría"
                style={{ width: 200 }}
                allowClear
                options={categorias.map(c => ({ label: c, value: c }))}
                onChange={(value) => handleFilterChange('categoria', value)}
              />
              <Select
                placeholder="Estatus"
                style={{ width: 200 }}
                allowClear
                options={estatusOptions.map(s => ({ label: s, value: s }))}
                onChange={(value) => handleFilterChange('estatus', value)}
              />
              <RangePicker
                onChange={handleDateChange}
              />
            </Space>
          </div>
        </Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={egresos}
          columns={columns}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            onChange: handlePageChange,
            showSizeChanger: true,
          }}
          summary={() => (
            <Table.Summary>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={3} align="right">
                  <strong>Total mostrado:</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={3} align="right">
                  <strong>
                    {sumatoriaMostrada.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}
                  </strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={4} colSpan={3} />
              </Table.Summary.Row>
            </Table.Summary>
          )}
          scroll={{ x: 1000, y: tableY }}
          locale={{ emptyText: 'No hay egresos' }}
        />
      </div>
    </>
  );
};

export default EgresosListPage;
