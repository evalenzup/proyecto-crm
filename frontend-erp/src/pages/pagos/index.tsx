// src/pages/pagos/index.tsx

'use client';
import React, { useMemo, useRef } from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Space, Select, DatePicker, Card, Grid, theme, Modal, Form, Input, message, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, ReloadOutlined, SearchOutlined, ThunderboltOutlined, FileExcelOutlined, FilePdfOutlined, MailOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { usePagosList } from '@/hooks/usePagosList';
import { PagoRow, timbrarPago, exportPagosExcel } from '@/services/pagoService';
import { useTableHeight } from '@/hooks/useTableHeight';

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

const PagosIndexPage: React.FC = () => {
  const router = useRouter();
  const { token } = useToken();
  const screens = useBreakpoint();
  const { containerRef, tableY } = useTableHeight();

  const {
    rows, totalRows, loading, pagination, fetchPagos, filters,
    verPdf, previewModalOpen, previewPdfUrl, previewRow, cerrarPreview,
    // Email
    emailModalOpen, emailRow, emailLoading, abrirEmailModal, cerrarEmailModal, enviarCorreo
  } = usePagosList();

  const [emailForm] = Form.useForm();

  React.useEffect(() => {
    if (emailModalOpen && emailRow) {
      // Pre-fill email
      const val = emailRow.cliente?.email;
      let initialEmails = '';
      if (Array.isArray(val)) {
        initialEmails = val.join(', ');
      } else if (typeof val === 'string') {
        initialEmails = val;
      }

      if (initialEmails) {
        emailForm.setFieldsValue({ recipient_emails: initialEmails });
      } else {
        emailForm.resetFields(['recipient_emails']);
      }
    }
  }, [emailModalOpen, emailRow, emailForm]);

  const handleEmailSubmit = (values: { recipient_emails: string }) => {
    if (!emailRow) return;
    const recips = (values.recipient_emails || '').split(/[;,\n]+/).map(r => r.trim()).filter(Boolean);
    enviarCorreo(emailRow.id, recips)
      .then(() => {
        message.success('Pago enviado por correo.');
        cerrarEmailModal();
        emailForm.resetFields();
      })
      .catch((e: any) => {
        const detail = e?.response?.data?.detail;
        message.error(typeof detail === 'string' ? detail : 'Error al enviar correo.');
      });
  };

  const {
    empresaId, setEmpresaId, empresasOptions,
    clienteId, setClienteId, clienteOptions, clienteQuery, setClienteQuery, debouncedBuscarClientes,
    estatus, setEstatus,
    rangoFechas, setRangoFechas, empresas,
  } = filters;

  // Auto-fetch on filter change
  React.useEffect(() => {
    fetchPagos({ ...pagination, current: 1 });
  }, [empresaId, clienteId, estatus, rangoFechas]);

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
          <Tooltip title="Editar">
            <Button type="link" icon={<EditOutlined />} onClick={() => router.push(`/pagos/form/${r.id}`)} />
          </Tooltip>
          <Tooltip title="Ver PDF">
            <Button type="link" icon={<FilePdfOutlined />} onClick={() => verPdf(r)} />
          </Tooltip>
          <Tooltip title="Enviar por Correo">
            <Button type="link" icon={<MailOutlined />} onClick={() => {
              const emp = empresas?.find((e: any) => e.id === r.empresa_id);
              if (emp && !emp.tiene_config_email) {
                Modal.warning({ title: 'Configuración faltante', content: 'La empresa emisora no tiene configurado el envío de correos.' });
                return;
              }
              abrirEmailModal(r);
            }} />
          </Tooltip>
          {r.estatus === 'BORRADOR' && (
            <Tooltip title="Timbrar">
              <Button
                type="link"
                icon={<ThunderboltOutlined />}
                onClick={() => handleTimbrar(r.id)}
              />
            </Tooltip>
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
        <Card size="small" variant="borderless" styles={{ body: { padding: 0 } }} style={{ marginTop: 4 }}>
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
        styles={{ body: { height: '80vh', padding: 0 } }}
        destroyOnHidden
      >
        {previewPdfUrl && (
          <iframe
            src={previewPdfUrl}
            style={{ width: '100%', height: '100%', border: 'none' }}
            title="Vista Previa PDF"
          />
        )}
      </Modal>

      {/* Modal Envío Correo */}
      <Modal
        title={`Enviar Pago ${emailRow?.folio || emailRow?.id || ''}`}
        open={emailModalOpen}
        onCancel={() => { cerrarEmailModal(); emailForm.resetFields(); }}
        onOk={() => emailForm.submit()}
        confirmLoading={emailLoading}
        okText="Enviar"
        cancelText="Cancelar"
      >
        <Form form={emailForm} layout="vertical" onFinish={handleEmailSubmit}>
          <Form.Item
            label="Correos del Destinatario (separados por coma)"
            name="recipient_emails"
            rules={[{ required: true, message: 'Ingrese al menos un destinatario' }]}
          >
            <Input.TextArea rows={4} placeholder="cliente@empresa.com, contador@empresa.com" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default PagosIndexPage;
