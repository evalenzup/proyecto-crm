// src/pages/facturas/index.tsx

'use client';
import React, { useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Space, Select, DatePicker, Modal, Form, Input, message, Tooltip, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, ReloadOutlined, SearchOutlined, FileExcelOutlined, FilePdfOutlined, MailOutlined, CopyOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { PageHeader } from '@/components/PageHeader';
import { SkeletonTable } from '@/components/SkeletonTable';
import { FilterBar } from '@/components/FilterBar';
import { useFacturasList } from '@/hooks/useFacturasList';
import { useTableHeight } from '@/hooks/useTableHeight';
import { FacturaRow, exportFacturasExcel, duplicarFactura } from '@/services/facturaService';
import { AcuseCancelacionModal } from '@/components/AcuseCancelacionModal';

const { RangePicker } = DatePicker;

import { formatDate, formatDateOnly } from '@/utils/formatDate';


const FacturasIndexPage: React.FC = () => {
  const router = useRouter();
  const { containerRef, tableY } = useTableHeight();

  const {
    rows, totalRows, loading, pagination, fetchFacturas, filters, sort, handleTableChange,
    verPdf, previewModalOpen, previewPdfUrl, previewRow, cerrarPreview,
    // Email
    emailModalOpen, cerrarEmailModal, abrirEmailModal, emailRow, enviarCorreo, emailLoading
  } = useFacturasList();

  const [emailForm] = Form.useForm();

  const handleDuplicate = async (id: string) => {
    try {
      message.loading({ content: 'Duplicando factura...', key: 'duplicating' });
      const newFactura = await duplicarFactura(id);
      message.success({ content: 'Factura duplicada correctamente', key: 'duplicating' });
      router.push(`/facturas/form/${newFactura.id}`);
    } catch (error: any) {
      console.error(error);
      if (!error?._handled) message.error({
        content: error.response?.data?.detail || 'Error al duplicar la factura',
        key: 'duplicating'
      });
    }
  };

  // Efecto para cargar email del cliente al abrir modal
  React.useEffect(() => {
    if (emailModalOpen && emailRow) {
      // Intentar obtener email del cliente de la fila si existe
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
        message.success('Factura enviada por correo.');
        cerrarEmailModal();
        emailForm.resetFields();
      })
      .catch((e: any) => {
        if (!e?._handled) {
          const detail = e?.response?.data?.detail;
          message.error(typeof detail === 'string' ? detail : 'Error al enviar correo.');
        }
      });
  };

  const {
    empresaId,
    clienteId, setClienteId,
    clienteOptionsComercial, clienteOptionsFiscal,
    debouncedBuscarClientesComercial, debouncedBuscarClientesFiscal,
    setClienteQuery, // Unused for reading here
    estatus, setEstatus,
    estatusPago, setEstatusPago,
    rangoFechas, setRangoFechas, empresas,
    setFolio,
  } = filters;

  // Auto-fetch on filter change
  React.useEffect(() => {
    fetchFacturas({ ...pagination, current: 1 });
  }, [empresaId, clienteId, estatus, estatusPago, rangoFechas]);

  const handleExport = async () => {
    try {
      const blob = await exportFacturasExcel({
        empresa_id: empresaId,
        cliente_id: clienteId,
        estatus: estatus || undefined,
        status_pago: estatusPago || undefined,
        fecha_desde: rangoFechas?.[0]?.format('YYYY-MM-DD'),
        fecha_hasta: rangoFechas?.[1]?.format('YYYY-MM-DD'),
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'facturas.xlsx';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
    }
  };

  const [acuseRow, setAcuseRow] = useState<FacturaRow | null>(null);

  // Orden actual (servidor) → sortOrder de la columna correspondiente
  const so = (key: string): 'ascend' | 'descend' | undefined =>
    sort?.order_by === key ? (sort.order_dir === 'asc' ? 'ascend' : 'descend') : undefined;

  const columns: ColumnsType<FacturaRow> = [
    { title: 'Folio', key: 'serie_folio', render: (_: any, r) => `${r.serie ?? ''}-${r.folio ?? ''}`, width: 110, sorter: true, sortOrder: so('serie_folio') },
    { title: 'Fecha', dataIndex: 'creado_en', key: 'fecha', render: (v: string) => formatDateOnly(v), width: 120, sorter: true, sortOrder: so('fecha') },
    { title: 'Cliente', key: 'cliente', render: (_: any, r) => r.cliente?.nombre_comercial || '—' },
    { title: 'Estatus CFDI', dataIndex: 'estatus', key: 'estatus', width: 130 },
    { title: 'Estatus Pago', dataIndex: 'status_pago', key: 'status_pago', width: 130 },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 140,
      align: 'right',
      sorter: true,
      sortOrder: so('total'),
      render: (v: string | number) =>
        (Number(v) || 0).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' }),
    },
    {
      title: 'Fecha Pago (Prog.)',
      dataIndex: 'fecha_pago',
      key: 'fecha_pago',
      render: (val: string) => val ? formatDate(val).split(',')[0] : '-',
      width: 120,
    },
    {
      title: 'Fecha Pago (Real)',
      dataIndex: 'fecha_cobro',
      key: 'fecha_cobro',
      render: (val: string) => val ? formatDate(val).split(',')[0] : '-',
      width: 120,
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 210,
      fixed: 'right',
      render: (_: any, r) => (
        <Space>
          <Tooltip title="Editar">
            <Button type="link" icon={<EditOutlined />} onClick={() => router.push(`/facturas/form/${r.id}`)} />
          </Tooltip>
          <Popconfirm
            title="¿Duplicar factura?"
            description="Se creará una copia en borrador con un nuevo folio."
            onConfirm={() => handleDuplicate(r.id)}
            okText="Sí, duplicar"
            cancelText="Cancelar"
          >
            <Tooltip title="Duplicar">
              <Button type="link" icon={<CopyOutlined />} />
            </Tooltip>
          </Popconfirm>
          <Tooltip title="Ver PDF">
            <Button type="link" icon={<FilePdfOutlined />} onClick={() => verPdf(r)} />
          </Tooltip>
          {(r.estatus === 'EN_CANCELACION' || r.estatus === 'CANCELADA') && (
            <Tooltip title="Acuse de cancelación (SAT)">
              <Button type="link" icon={<SafetyCertificateOutlined />} onClick={() => setAcuseRow(r)} />
            </Tooltip>
          )}
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
        </Space>
      ),
    },
  ];

  const sumatoriaMostrada = useMemo(
    () => rows.reduce((acc, r) => {
      if (r.estatus === 'CANCELADA') return acc;
      return acc + (Number(r.total) || 0);
    }, 0),
    [rows]
  );

  return (
    <>
      <PageHeader
        title="Facturas"
        extra={
          <>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => router.push('/facturas/form')}>
              Nueva factura
            </Button>
            <Button icon={<FileExcelOutlined />} onClick={handleExport}>
              Exportar
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => fetchFacturas()}>
              Recargar
            </Button>
          </>
        }
      />
      <div className="app-content" ref={containerRef}>
          <FilterBar>
              <Select
                showSearch allowClear placeholder="Nombre Comercial" style={{ width: 220, minWidth: 160 }}
                filterOption={false}
                onSearch={(val) => { setClienteQuery(val); debouncedBuscarClientesComercial(val); }}
                onChange={(val) => setClienteId(val)}
                onClear={() => { setClienteQuery(''); setClienteId(undefined); }}
                options={clienteOptionsComercial}
                suffixIcon={<SearchOutlined />}
                value={clienteId}
                notFoundContent={null}
              />
              <Select
                showSearch allowClear placeholder="Razón Social" style={{ width: 220, minWidth: 160 }}
                filterOption={false}
                onSearch={(val) => { setClienteQuery(val); debouncedBuscarClientesFiscal(val); }}
                onChange={(val) => setClienteId(val)}
                onClear={() => { setClienteQuery(''); setClienteId(undefined); }}
                options={clienteOptionsFiscal}
                suffixIcon={<SearchOutlined />}
                value={clienteId}
                notFoundContent={null}
              />
              <Select
                allowClear placeholder="Estatus CFDI" style={{ width: 160, minWidth: 140 }}
                value={estatus} onChange={setEstatus}
                options={[
                  { value: 'BORRADOR', label: 'BORRADOR' },
                  { value: 'TIMBRADA', label: 'TIMBRADA' },
                  { value: 'CANCELADA', label: 'CANCELADA' },
                ]}
              />
              <Select
                allowClear placeholder="Estatus Pago" style={{ width: 160, minWidth: 140 }}
                value={estatusPago} onChange={setEstatusPago}
                options={[
                  { value: 'PAGADA', label: 'PAGADA' },
                  { value: 'NO_PAGADA', label: 'NO_PAGADA' },
                ]}
              />
              <RangePicker
                onChange={(range) => setRangoFechas(range as any)}
                value={rangoFechas as any}
                placeholder={['Desde', 'Hasta']}
                allowClear
                style={{ minWidth: 200 }}
              />
              <Input
                placeholder="Folio (Enter)"
                style={{ width: 120, minWidth: 100 }}
                onPressEnter={(e) => setFolio(e.currentTarget.value)}
                allowClear
                onChange={(e) => { if (!e.target.value) setFolio(''); }}
              />
          </FilterBar>

          {loading && rows.length === 0 ? (
          <SkeletonTable />
          ) : (
          <Table<FacturaRow>
            size="small"
            rowKey="id"
            columns={columns}
            dataSource={rows}
            loading={loading}
            pagination={{
              ...pagination,
              total: totalRows,
              showTotal: (t) => `${t} facturas`,
            }}
            onChange={handleTableChange}
            scroll={{ x: 980, y: tableY }}
            summary={() => (
              <Table.Summary>
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0} colSpan={5} align="right">
                    <strong>Total mostrado:</strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={5} align="right">
                    <strong>
                      {sumatoriaMostrada.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}
                    </strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={6} />
                </Table.Summary.Row>
              </Table.Summary>
            )}
            locale={{ emptyText: 'No hay facturas' }}
          />
          )}
      </div>
      <Modal
        title="Vista Previa de Factura"
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
                a.download = `factura-${previewRow.serie || ''}${previewRow.folio || previewRow.id}.pdf`;
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

      {/* Modal de Envío de Correo */}
      <Modal
        title={`Enviar Factura ${emailRow?.serie || ''}${emailRow?.folio || ''}`
        }
        open={emailModalOpen}
        onCancel={() => {
          cerrarEmailModal();
          emailForm.resetFields();
        }}
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

      <AcuseCancelacionModal
        facturaId={acuseRow?.id ?? null}
        serie={acuseRow?.serie}
        folio={acuseRow?.folio}
        open={!!acuseRow}
        onClose={() => setAcuseRow(null)}
      />
    </>
  );
};

export default FacturasIndexPage;