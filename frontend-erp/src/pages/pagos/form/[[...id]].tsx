'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import {
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Spin,
  Card,
  Space,
  Typography,
  Divider,
  DatePicker,
  Row,
  Col,
  Table,
  Tag,
  Modal,
  Radio,
} from 'antd';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { usePagoForm } from '@/hooks/usePagoForm';
import { FacturaPendiente } from '@/services/pagoService';
import {
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ArrowLeftOutlined,
  SaveOutlined,
  ThunderboltOutlined,
  MailOutlined,
  FilePdfOutlined,
  DownloadOutlined,
  FileTextOutlined,
  DeleteOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;

const PagoFormPage: React.FC = () => {
  const router = useRouter();
  const {
    id,
    form,
    pago,
    loading,
    saving,
    accionLoading,
    empresas,
    clientesComercial,
    clientesFiscal,
    buscarClientesComercial,
    buscarClientesFiscal,
    formasPago,
    facturasPendientes,
    paymentAllocation,
    handleAllocationChange,
    handleMetadataChange,
    onFinish,
    generarComplemento,
    enviarComplemento,
    verPdf,
    verFacturaPdf,
    descargarPdf,
    descargarXml,
    previewModalOpen,
    previewPdfUrl,
    previewTitle,
    cerrarPreview,
    // Cancelacion
    cancelacionModalOpen,
    abrirCancelacion,
    cerrarCancelacion,
    confirmarCancelacion,
    // Email
    emailModalOpen,
    abrirEmailModal,
    cerrarEmailModal,
    confirmarEnvioCorreo,
    clienteEmail,
    currentEmpresa,
    crossCompanyMode,
    setCrossCompanyMode,
  } = usePagoForm();

  // Formulario para email
  const [emailForm] = Form.useForm();

  const handleEmailSubmit = (values: { recipient_emails: string }) => {
    // Split recipients by comma
    const recips = (values.recipient_emails || '').split(/[;,\n]+/).map((r: string) => r.trim()).filter(Boolean);
    confirmarEnvioCorreo(recips, "Envío de Complemento de Pago", "Se adjunta el complemento de recepción de pagos en formato XML y PDF.");
    emailForm.resetFields();
  };

  // Formulario independiente para el modal de cancelación
  const [cancelacionForm] = Form.useForm();

  const handleCancelacionSubmit = (values: { motivo: string; folio_sustituto?: string }) => {
    confirmarCancelacion(values.motivo, values.folio_sustituto);
    cancelacionForm.resetFields();
  };

  // Watch motivo to show/hide folio sustituto
  const motivo = Form.useWatch('motivo', cancelacionForm);

  const totalAllocated = React.useMemo<number>(() => {
    return Object.values(paymentAllocation).reduce((sum: number, amount) => sum + Number(amount || 0), 0);
  }, [paymentAllocation]);

  useEffect(() => {
    form.setFieldsValue({ monto: totalAllocated });
  }, [totalAllocated, form]);

  // Sincroniza campos informativos con los nombres reales del backend
  useEffect(() => {
    if (pago) {
      form.setFieldsValue({
        uuid_cfdi: pago.uuid,
        timbrado_at: pago.fecha_timbrado ? new Date(pago.fecha_timbrado).toLocaleString('es-MX') : undefined,
      });
    }
  }, [pago, form]);

  useEffect(() => {
    if (!id) {
      form.setFieldsValue({ folio: 1 });
    }
  }, [id, form]);


  if (loading) return <Spin style={{ margin: 48 }} />;

  const facturasColumns: ColumnsType<FacturaPendiente> = [
    {
      title: 'Folio',
      dataIndex: 'folio',
      render: (val: any, rec: any) => (
        <Button
          type="link"
          size="small"
          onClick={() => verFacturaPdf(rec.id, `${rec.serie}-${val}`)}
          style={{ padding: 0 }}
        >
          {`${rec.serie}-${val}`}
        </Button>
      )
    },
    { title: 'Fecha Em.', dataIndex: 'fecha_emision', render: (val: string) => new Date(val).toLocaleDateString() },
    {
      title: 'Saldo Anterior',
      dataIndex: 'saldo_pendiente',
      width: 140,
      render: (val: number, rec: FacturaPendiente) => (
        <InputNumber
          min={0}
          step={0.01}
          precision={2}
          value={val}
          onChange={(v) => handleMetadataChange(rec.id, 'saldo_pendiente', Number(v))}
          disabled={isTimbrado || isCancelado}
          controls={false}
        />
      )
    },
    {
      title: 'Parcialidad',
      dataIndex: 'parcialidad_actual',
      width: 80,
      render: (val: number, rec: FacturaPendiente) => (
        <InputNumber
          min={1}
          step={1}
          precision={0}
          value={val}
          onChange={(v) => handleMetadataChange(rec.id, 'parcialidad_actual', Number(v))}
          disabled={isTimbrado || isCancelado}
          style={{ width: '100%' }}
          controls={false}
        />
      )
    },
    {
      title: 'Total Fact.',
      dataIndex: 'total',
      align: 'right',
      render: (val: number) => <Text type="secondary" style={{ fontSize: '0.85em' }}>{val.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}</Text>
    },
    {
      title: 'Monto a Pagar',
      dataIndex: 'id',
      key: 'monto_a_pagar',
      width: 200,
      render: (facturaId: string, record: FacturaPendiente) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <InputNumber
            min={0}
            // max constraint removed to allow rounding differences (e.g. 215.68 vs 215.676)
            precision={2}
            value={paymentAllocation[facturaId]}
            onChange={(value) => handleAllocationChange(facturaId, value)}
            style={{ width: '100%' }}
            addonBefore="$"
            controls={false}
            disabled={isTimbrado || isCancelado}
          />
          <Button
            icon={<CopyOutlined />}
            size="small"
            onClick={() => handleAllocationChange(facturaId, record.saldo_pendiente || 0)}
            disabled={isTimbrado || isCancelado}
            title="Copiar Saldo"
          />
        </div>
      ),
    },
  ];

  // Estado calculado conforme al esquema del backend
  const isTimbrado = pago?.estatus === 'TIMBRADO' || !!pago?.uuid || !!pago?.fecha_timbrado;
  const isCancelado = pago?.estatus === 'CANCELADO';

  const getStatusTag = () => {
    if (isCancelado) {
      return <Tag icon={<CloseCircleOutlined />} color="error">Cancelado</Tag>;
    }
    if (isTimbrado) {
      return <Tag icon={<CheckCircleOutlined />} color="success">Timbrado</Tag>;
    }
    if (id) {
      return <Tag icon={<ExclamationCircleOutlined />} color="warning">Guardado sin timbrar</Tag>;
    }
    return <Tag icon={<SyncOutlined spin />} color="processing">Nuevo</Tag>;
  };

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">{id ? 'Editar Pago' : 'Nuevo Pago'}</h1>
        </div>
        <div className="app-page-header__right">
          {getStatusTag()}
        </div>
      </div>

      <div className="app-content">
        <Form form={form} layout="vertical" onFinish={onFinish} disabled={isTimbrado}>
          <Card size="small" title="Emisor y Receptor" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label="Empresa" name="empresa_id" rules={[{ required: true }]}>
                  <Select options={empresas} placeholder="Seleccione una empresa" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="Buscar por Nombre Comercial" name="cliente_id_comercial">
                  <Select
                    options={clientesComercial}
                    showSearch
                    filterOption={false}
                    onSearch={buscarClientesComercial}
                    placeholder="Escribe al menos 3 letras..."
                    onChange={(val) => form.setFieldValue('cliente_id', val)}
                    value={form.getFieldValue('cliente_id')}
                  />
                </Form.Item>
                <Form.Item label="Buscar por Razón Social" name="cliente_id_fiscal">
                  <Select
                    options={clientesFiscal}
                    showSearch
                    filterOption={false}
                    onSearch={buscarClientesFiscal}
                    placeholder="Escribe al menos 3 letras..."
                    onChange={(val) => form.setFieldValue('cliente_id', val)}
                    value={form.getFieldValue('cliente_id')}
                  />
                </Form.Item>
                <Form.Item name="cliente_id" hidden rules={[{ required: true, message: 'Seleccione un cliente' }]}>
                  <Input />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card size="small" title="Datos del Pago" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} md={6}>
                <Form.Item label="Fecha de Pago (Real)" name="fecha_pago" rules={[{ required: true }]}>
                  <DatePicker style={{ width: '100%' }} showTime format="YYYY-MM-DD HH:mm:ss" />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label="Fecha Emisión (CFDI)" name="fecha_emision" tooltip="Fecha legal del comprobante. Máximo 72h hacia el pasado. Si vacío, se usa fecha actual.">
                  <DatePicker style={{ width: '100%' }} showTime format="YYYY-MM-DD HH:mm:ss" />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label="Forma de Pago" name="forma_pago_p" rules={[{ required: true }]}>
                  <Select placeholder="Seleccione una forma de pago" options={formasPago} />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label="Monto" name="monto" rules={[{ required: true }]}>
                  <InputNumber min={0} style={{ width: '100%' }} addonBefore="$" disabled />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={8}>
                <Form.Item label="Moneda" name="moneda_p" rules={[{ required: true }]}>
                  <Select options={[{ label: 'MXN', value: 'MXN' }, { label: 'USD', value: 'USD' }]} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Folio" name="folio" rules={[{ required: true }]}>
                  <Input disabled />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label="Folio Fiscal (UUID)" name="uuid_cfdi">
                  <Input disabled />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="Fecha y Hora de Timbrado" name="timbrado_at">
                  <Input disabled />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card size="small" title="Facturas a Pagar">
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 8 }}>
              <span>Mostrar facturas de:</span>
              <Radio.Group
                value={crossCompanyMode}
                onChange={(e) => setCrossCompanyMode(e.target.value)}
                buttonStyle="solid"
                size="small"
                disabled={!!id} // Disable in edit mode to avoid confusion? Or allow? Logic says reload replaces list. Let's allow if not timbrado.
              >
                <Radio.Button value={false}>Solo esta Sucursal</Radio.Button>
                <Radio.Button value={true}>Todas (Mismo RFC)</Radio.Button>
              </Radio.Group>
            </div>
            <Table
              rowKey="id"
              dataSource={facturasPendientes}
              columns={facturasColumns}
              pagination={false}
              bordered
              size="small"
              summary={() => (
                <Table.Summary>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={3} align="right">
                      <strong>Total Aplicado:</strong>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={3} align="left">
                      <Text type={totalAllocated > form.getFieldValue('monto') ? 'danger' : 'success'} strong>
                        {totalAllocated.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}
                      </Text>
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                </Table.Summary>
              )}
            />
          </Card>
        </Form>

        <Divider />

        <Space wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/pagos')}>Regresar</Button>
          <Button icon={<SaveOutlined />} type="primary" onClick={() => form.submit()} loading={saving} disabled={isTimbrado || isCancelado}>
            {id ? 'Actualizar Pago' : 'Guardar Borrador'}
          </Button>
          <Button
            icon={<ThunderboltOutlined />}
            onClick={generarComplemento}
            loading={accionLoading.timbrando}
            disabled={!id || isTimbrado || isCancelado}
          >
            Timbrar
          </Button>
          <Button
            icon={<MailOutlined />}
            onClick={() => {
              if (currentEmpresa && !currentEmpresa.tiene_config_email) {
                Modal.warning({
                  title: 'Falta configuración de correo',
                  content: 'La empresa no tiene configurado el servicio de correo electrónico. Por favor, realiza la configuración en el módulo de Empresas antes de enviar.',
                });
                return;
              }

              const clientEmail = form.getFieldValue(['cliente', 'email']) || clienteEmail;
              emailForm.setFieldsValue({ recipient_emails: clientEmail });
              abrirEmailModal();
            }}
            loading={accionLoading.enviando}
            disabled={!isTimbrado && !isCancelado}
          >
            Enviar por Correo
          </Button>
          <Button
            icon={<FilePdfOutlined />}
            onClick={verPdf}
            loading={accionLoading.visualizando}
            disabled={!id}
          >
            Ver PDF
          </Button>
          <Button
            icon={<FileTextOutlined />}
            onClick={descargarXml}
            loading={accionLoading.descargando}
            disabled={!isTimbrado}
          >
            Descargar XML
          </Button>
          <Button
            icon={<DeleteOutlined />}
            danger
            onClick={abrirCancelacion}
            loading={accionLoading.cancelando}
            disabled={!isTimbrado || isCancelado}
          >
          </Button>
        </Space>
      </div>

      {/* Modal: Confirmar Cancelación */}
      <Modal
        title="Cancelar Complemento de Pago"
        open={cancelacionModalOpen}
        onCancel={() => {
          cerrarCancelacion();
          cancelacionForm.resetFields();
        }}
        onOk={() => cancelacionForm.submit()}
        confirmLoading={accionLoading.cancelando}
        okText="Confirmar Cancelación"
        okType="danger"
        cancelText="Cerrar"
      >
        <Form form={cancelacionForm} layout="vertical" onFinish={handleCancelacionSubmit}>
          <div style={{ marginBottom: 16, color: '#faad14' }}>
            <ExclamationCircleOutlined /> Esta acción solicitará la cancelación ante el SAT.
          </div>

          <Form.Item
            label="Motivo de Cancelación"
            name="motivo"
            rules={[{ required: true, message: 'Seleccione un motivo' }]}
            initialValue="02"
          >
            <Select>
              <Select.Option value="01">01 - Comprobante emitido con errores con relación</Select.Option>
              <Select.Option value="02">02 - Comprobante emitido con errores sin relación</Select.Option>
              <Select.Option value="03">03 - No se llevó a cabo la operación</Select.Option>
              <Select.Option value="04">04 - Operación nominativa relacionada en la factura global</Select.Option>
            </Select>
          </Form.Item>

          {motivo === '01' && (
            <Form.Item
              label="Folio Fiscal Sustituto (UUID)"
              name="folio_sustituto"
              rules={[{ required: true, message: 'El folio sustituto es obligatorio para motivo 01' }]}
            >
              <Input placeholder="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" />
            </Form.Item>
          )}
        </Form>
      </Modal >

      {/* Modal: Vista Previa PDF */}
      < Modal
        title={previewTitle}
        open={previewModalOpen}
        onCancel={cerrarPreview}
        footer={
          [
            <Button key="close" onClick={cerrarPreview}>
              Cerrar
            </Button>,
            <Button key="download" type="primary" icon={<FilePdfOutlined />} onClick={descargarPdf}>
              Descargar
            </Button>,
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

      {/* Modal: Enviar Correo (Homologado con Facturación) */}
      <Modal
        title="Enviar Complemento por Correo"
        open={emailModalOpen}
        onCancel={() => {
          cerrarEmailModal();
          emailForm.resetFields();
        }}
        onOk={() => emailForm.submit()}
        confirmLoading={accionLoading.enviando}
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

export default PagoFormPage;
