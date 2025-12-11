import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Space, Tag, message, Input, Select, DatePicker, Row, Col, Card, Pagination } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { getEgresos, deleteEgreso, Egreso, getEgresoEnums } from '@/services/egresoService';
import { getEmpresas } from '@/services/facturaService';

const { RangePicker } = DatePicker;

import { useEmpresaSelector } from '@/hooks/useEmpresaSelector'; // Importar hook

const EgresosListPage: React.FC = () => {
  const router = useRouter();
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

  const handleDelete = async (id: string) => {
    try {
      await deleteEgreso(id);
      message.success('Egreso eliminado con éxito.');
      fetchEgresos();
    } catch (error) {
      message.error('Error al eliminar el egreso.');
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
          <Button icon={<EditOutlined />} onClick={() => router.push(`/egresos/form/${record.id}`)} />
          <Button icon={<DeleteOutlined />} danger onClick={() => handleDelete(record.id)} />
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className="app-page-header">
        <Breadcrumbs />
        <h1 className="app-title">Egresos</h1>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => router.push('/egresos/form')}
        >
          Nuevo Egreso
        </Button>
      </div>
      <div className="app-content">
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col>
              <Select
                placeholder="Empresa"
                style={{ width: 200 }}
                allowClear
                options={empresas.map(e => ({ label: e.nombre_comercial, value: e.id }))}
                value={selectedEmpresaId}
                onChange={setSelectedEmpresaId}
                disabled={!isAdmin}
              />
            </Col>
            <Col>
              <Input
                placeholder="Proveedor"
                style={{ width: 200 }}
                onChange={(e) => handleFilterChange('proveedor', e.target.value)}
              />
            </Col>
            <Col>
              <Select
                placeholder="Categoría"
                style={{ width: 200 }}
                allowClear
                options={categorias.map(c => ({ label: c, value: c }))}
                onChange={(value) => handleFilterChange('categoria', value)}
              />
            </Col>
            <Col>
              <Select
                placeholder="Estatus"
                style={{ width: 200 }}
                allowClear
                options={estatusOptions.map(s => ({ label: s, value: s }))}
                onChange={(value) => handleFilterChange('estatus', value)}
              />
            </Col>
            <Col>
              <RangePicker
                onChange={handleDateChange}
              />
            </Col>
          </Row>
        </Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={egresos}
          columns={columns}
          bordered
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
        />
      </div>
    </>
  );
};

export default EgresosListPage;
