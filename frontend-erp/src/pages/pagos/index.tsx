'use client';
import React, { useMemo, useRef } from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Space, Select, DatePicker, Card, Grid, theme, Modal } from 'antd';
import { PlusOutlined, EditOutlined, ReloadOutlined, SearchOutlined, ThunderboltOutlined, FileExcelOutlined, FilePdfOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { usePagosList } from '@/hooks/usePagosList';
import { PagoRow, timbrarPago, exportPagosExcel } from '@/services/pagoService';
import { message } from 'antd';

const { RangePicker } = DatePicker;
const { useToken } = theme;
const { useBreakpoint } = Grid;

const formatDateTijuana = (iso: string) => {
  if (!iso) return '';
  const utc = iso.endsWith('Z') ? iso : `${iso}Z`;
  return new Date(utc).toLocaleString('es-MX', {
    timeZone: 'America/Tijuana',
    dateStyle: 'short',
    timeStyle: 'medium',
  });
};

const useTableHeight = () => {
  const ref = useRef<HTMLDivElement | null>(null);
  const [y, setY] = React.useState<number | undefined>(undefined);

  React.useEffect(() => {
    const calc = () => {
      if (!ref.current) return setY(undefined);
      const rect = ref.current.getBoundingClientRect();
      const h = window.innerHeight - rect.top - 220;
      setY(h > 240 ? h : 240);
    };
    calc();
    window.addEventListener('resize', calc);
    return () => window.removeEventListener('resize', calc);
  }, []);

  return { containerRef: ref, tableY: y };
};

const PagosIndexPage: React.FC = () => {
  const router = useRouter();
  const { token } = useToken();
  const screens = useBreakpoint();
  const { containerRef, tableY } = useTableHeight();

  const { rows, totalRows, loading, pagination, fetchPagos, filters, verPdf, previewModalOpen, previewPdfUrl, previewRow, cerrarPreview } = usePagosList();

  const {
    empresaId, setEmpresaId, empresasOptions,
    clienteId, setClienteId, clienteOptions, clienteQuery, setClienteQuery, debouncedBuscarClientes,
    estatus, setEstatus,
    rangoFechas, setRangoFechas,
  } = filters;

  const aplicarFiltros = () => fetchPagos({ ...pagination, current: 1 });

  const handleTimbrar = async (pagoId: string) => {
    try {
      await timbrarPago(pagoId);
      message.success('Pago timbrado exitosamente (simulado)');
      fetchPagos(); // Refresh the list
    } catch (error: any) {
      const detail = error?.response?.data?.detail || 'Error al timbrar el pago.';
      message.error(detail);
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportPagosExcel({
        empresa_id: empresaId,
        cliente_id: clienteId,
        estatus: estatus || undefined,
        fecha_desde: rangoFechas?.[0]?.format('YYYY-MM-DD'),
        fecha_hasta: rangoFechas?.[1]?.format('YYYY-MM-DD'),
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'pagos.xlsx';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      message.error('Error al exportar pagos');
    }
  };

  const columns: ColumnsType<PagoRow> = [
    { title: 'Folio', key: 'folio', render: (_: any, r) => `${r.folio ?? ''}`, width: 110 },
    { title: 'Fecha Pago', dataIndex: 'fecha_pago', key: 'fecha_pago', render: (v: string) => formatDateTijuana(v), width: 180 },
    { title: 'Cliente', key: 'cliente', render: (_: any, r) => r.cliente?.nombre_comercial || '—' },
    { title: 'Estatus', dataIndex: 'estatus', key: 'estatus', width: 130 },
    {
      title: 'Monto',
      dataIndex: 'monto',
      key: 'monto',
      width: 140,
      align: 'right',
      render: (v: string | number) =>
        (Number(v) || 0).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' }),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 120,
      render: (_: any, r) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => router.push(`/pagos/form/${r.id}`)} />
          <Button type="link" icon={<FilePdfOutlined />} onClick={() => verPdf(r)} title="Ver PDF" />
          {r.estatus === 'BORRADOR' && (
            <Button
              type="link"
              icon={<ThunderboltOutlined />}
              onClick={() => handleTimbrar(r.id)}
              title="Timbrar"
            />
          )}
        </Space>
      ),
    },
  ];

  const sumatoriaMostrada = useMemo(
    () => rows.reduce((acc, r) => acc + (Number(r.monto) || 0), 0),
    [rows]
  );

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">Complementos de Pago</h1>
        </div>
        <div className="app-page-header__right">
          <Space wrap>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => router.push('/pagos/form')}>
              Nuevo Pago
            </Button>
            <Button icon={<FileExcelOutlined />} style={{ color: 'green', borderColor: 'green' }} onClick={handleExport}>
              Exportar
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => fetchPagos()}>
              Recargar
            </Button>
          </Space>
        </div>
      </div>
      <div className="app-content" ref={containerRef}>
        <Card size="small" bordered bodyStyle={{ padding: 12 }} style={{ marginTop: 4 }}>
          <div
            style={{
              position: 'sticky', top: 0, zIndex: 9,
              padding: screens.lg ? '8px 8px 12px' : '8px',
              marginBottom: 8,
              background: token.colorBgContainer,
              borderRadius: 8,
              boxShadow: token.boxShadowSecondary,
            }}
          >
            <Space wrap size={[8, 8]}>
              <Select
                allowClear placeholder="Empresa" style={{ width: 220 }}
                options={empresasOptions} value={empresaId}
                onChange={setEmpresaId} onClear={() => setEmpresaId(undefined)}
                disabled={!filters.isAdmin}
              />
              <Select
                allowClear showSearch placeholder="Cliente (escribe ≥ 3 letras)" style={{ width: 280 }}
                filterOption={false}
                onSearch={(val) => { setClienteQuery(val); debouncedBuscarClientes(val); }}
                onChange={(val) => setClienteId(val)}
                onClear={() => { setClienteQuery(''); setClienteId(undefined); }}
                notFoundContent={clienteQuery && clienteQuery.length < 3 ? 'Escribe al menos 3 caracteres' : undefined}
                options={clienteOptions}
                suffixIcon={<SearchOutlined />}
                value={clienteId}
              />
              <Select
                allowClear placeholder="Estatus" style={{ width: 180 }}
                value={estatus} onChange={setEstatus}
                options={[
                  { value: 'BORRADOR', label: 'BORRADOR' },
                  { value: 'TIMBRADO', label: 'TIMBRADO' },
                  { value: 'CANCELADO', label: 'CANCELADO' },
                ]}
              />
              <RangePicker
                onChange={(range) => setRangoFechas(range as any)}
                value={rangoFechas as any}
                placeholder={['Desde', 'Hasta']}
                allowClear
              />
              <Button type="primary" onClick={aplicarFiltros}>Aplicar filtros</Button>
            </Space>
          </div>

          <Table<PagoRow>
            size="small"
            rowKey="id"
            columns={columns}
            dataSource={rows}
            loading={loading}
            pagination={{
              ...pagination,
              total: totalRows,
              showTotal: (t) => `${t} pagos`,
            }}
            onChange={(pag) => fetchPagos(pag)}
            scroll={{ x: 980, y: tableY }}
            summary={() => (
              <Table.Summary>
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0} colSpan={4} align="right">
                    <strong>Total mostrado:</strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={4} align="right">
                    <strong>
                      {sumatoriaMostrada.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}
                    </strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={5} />
                </Table.Summary.Row>
              </Table.Summary>
            )}
            locale={{ emptyText: 'No hay pagos' }}
          />
        </Card>
      </div>
      <Modal
        title="Vista Previa de Pago"
        open={previewModalOpen}
        onCancel={cerrarPreview}
        footer={[
          <Button key="close" onClick={cerrarPreview}>Cerrar</Button>,
          <Button
            key="download"
            type="primary"
            icon={<FilePdfOutlined />}
            onClick={() => {
              if (previewPdfUrl && previewRow) {
                const a = document.createElement('a');
                a.href = previewPdfUrl;
                a.download = `pago-${previewRow.folio || previewRow.id}.pdf`;
                a.click();
              }
            }}
          >
            Descargar
          </Button>
        ]}
        width="90%"
        style={{ top: 20 }}
        bodyStyle={{ height: '80vh', padding: 0 }}
        destroyOnClose
      >
        {previewPdfUrl && (
          <iframe
            src={previewPdfUrl}
            style={{ width: '100%', height: '100%', border: 'none' }}
            title="Vista Previa PDF"
          />
        )}
      </Modal>
    </>
  );
};

export default PagosIndexPage;
