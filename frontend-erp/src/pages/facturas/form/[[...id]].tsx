// frontend-erp/src/pages/facturas/form/[[...id]].tsx
'use client';

import React from 'react';
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
  Checkbox,
  Row,
  Col,
  Popconfirm,
  Modal,
  Table,
  Alert,
  message,
  theme,
} from 'antd';
import {
  SaveOutlined,
  ArrowLeftOutlined,
  PlusOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  StopOutlined,
  PlusCircleOutlined,
  EditOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  FileOutlined,
  MailOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import {
  createFactura,
  getFacturaById,
  updateFactura,
  timbrarFactura,
  cancelarFactura,
  getPdfPreview,
  getPdf,
  sendEmail,
  sendPreviewEmail,
  duplicarFactura,
} from '@/services/facturaService';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useFacturaForm } from '@/hooks/useFacturaForm';
import { TipoProductoServicio } from '@/services/productoServicioService';
import api from '@/lib/axios';

const { Text } = Typography;

const FacturaFormPage: React.FC = () => {
  const router = useRouter();

  const [isSendingEmail, setIsSendingEmail] = React.useState(false);
  const [isSendingPreview, setIsSendingPreview] = React.useState(false); // New state
  const [isEmailModalOpen, setIsEmailModalOpen] = React.useState(false);
  const [emailForm] = Form.useForm();

  const {
    // estado
    id,
    loading,
    saving,
    accionLoading,
    cancelSubmitting,
    metadata,
    estatusCFDI,
    statusPago,
    rfcEmisor,

    // antd forms
    form,
    conceptoForm,
    psForm,
    cancelForm,

    // catálogos / opciones
    empresas,
    regimenes,
    metodosPago,
    formaPagoOptions,
    usosCfdi,
    tiposRelacion,
    motivosCancel,
    clienteOpts,
    psOpts,
    unidadOpts,
    claveSatOpts,

    // watchers / flags
    empresaId,
    moneda,
    isFormDisabled,
    fieldDisabled,
    fieldAlwaysEditable,
    puedeTimbrar,
    puedeCancelar,

    // datos conceptos
    conceptos,
    setConceptos,
    isConceptoModalOpen,
    setIsConceptoModalOpen,
    editingConcepto,
    setEditingConcepto,
    setEditingConceptoIndex,

    // cálculos
    resumen,

    // handlers (empresa/cliente/fechas)
    onFinish,
    onEmpresaChange,
    buscarClientes,
    onClienteChange,
    onFechaEmisionChange,

    // handlers (conceptos)
    buscarPS,
    onSelectPSInModal,
    handleSaveConcepto,

    // handlers (PS modal SAT)
    buscarClavesProductoSAT,
    buscarUnidadesSAT,
    psModalOpen,
    setPsModalOpen,
    psSaving,

    // modal cancelación
    cancelModalOpen,
    setCancelModalOpen,
    abrirModalCancelacion,
    submitCancel,

    // acciones (CFDI / archivos)
    timbrarFactura,
    verPDF,
    descargarPDF,
    descargarXML,
    currentEmpresa,
    previewModalOpen,
    previewPdfUrl,
    cerrarPreview,
  } = useFacturaForm();

  const handleSendEmail = async () => {
    if (!id) return;
    if (currentEmpresa && !currentEmpresa.tiene_config_email) {
      Modal.warning({
        title: 'Falta configuración de correo',
        content: 'La empresa no tiene configurado el servicio de correo electrónico. Por favor, realiza la configuración en el módulo de Empresas antes de enviar.',
      });
      return;
    }

    const clienteEmail = form.getFieldValue(['cliente', 'email']);
    emailForm.setFieldsValue({ recipient_emails: clienteEmail });
    setIsSendingPreview(false); // Ensure this is false for regular email
    setIsEmailModalOpen(true);
  };

  const handleSendPreviewEmail = async () => {
    if (!id) return;
    if (currentEmpresa && !currentEmpresa.tiene_config_email) {
      Modal.warning({
        title: 'Falta configuración de correo',
        content: 'La empresa no tiene configurado el servicio de correo electrónico. Por favor, realiza la configuración en el módulo de Empresas antes de enviar.',
      });
      return;
    }

    const clienteEmail = form.getFieldValue(['cliente', 'email']);
    emailForm.setFieldsValue({ recipient_emails: clienteEmail });
    setIsSendingPreview(true); // Set to true for preview email
    setIsEmailModalOpen(true);
  };

  const onEmailModalOk = async () => {
    try {
      const values = await emailForm.validateFields();
      const raw: string = values.recipient_emails || '';
      // Normaliza: admite comas, punto y coma y saltos de línea como separadores
      const recipients: string[] = Array.from(
        new Set(
          String(raw)
            .split(/[;,\n]+/)
            .map((e) => e.trim())
            .filter(Boolean)
        )
      );
      setIsSendingEmail(true);
      const endpoint = isSendingPreview ? `/facturas/${id}/send-preview-email` : `/facturas/${id}/send-email`;
      const successMessage = isSendingPreview
        ? `Vista previa de factura enviada correctamente a ${recipients.join(', ')}.`
        : `Factura enviada correctamente a ${recipients.join(', ')}.`;
      // Enviamos usando el campo 'recipients' (lista), el backend también acepta 'recipient_emails' CSV.
      await api.post(endpoint, { recipients });
      message.success(successMessage);
      setIsEmailModalOpen(false);
      emailForm.resetFields();
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      message.error(typeof detail === 'string' ? detail : 'Error al enviar factura por correo.');
    } finally {
      setIsSendingEmail(false);
      setIsSendingPreview(false); // Reset the state
    }
  };

  // Effect to populate email form when modal opens and invoice data is ready
  React.useEffect(() => {
    if (isEmailModalOpen && id) {
      const clienteEmail = form.getFieldValue(['cliente', 'email']);
      console.log('Cliente Email from main form:', clienteEmail);
      emailForm.setFieldsValue({ recipient_emails: clienteEmail });
    }
  }, [isEmailModalOpen, id, form, emailForm]);

  // Poblar formulario de concepto al abrir modal
  React.useEffect(() => {
    if (isConceptoModalOpen) {
      if (editingConcepto) {
        conceptoForm.setFieldsValue(editingConcepto);
      } else {
        conceptoForm.resetFields();
      }
    }
  }, [isConceptoModalOpen, editingConcepto, conceptoForm]);

  const handleDuplicate = async () => {
    if (!id) return;
    try {
      message.loading({ content: 'Duplicando factura...', key: 'duplicating' });
      const newFactura = await duplicarFactura(id as string);
      message.success({ content: 'Factura duplicada correctamente', key: 'duplicating' });
      router.push(`/facturas/form/${newFactura.id}`);
    } catch (error: any) {
      console.error(error);
      message.error({
        content: error.response?.data?.detail || 'Error al duplicar la factura',
        key: 'duplicating'
      });
    }
  };

  if (loading) return <Spin style={{ margin: 48 }} />;

  return (
    <>
      {/* Encabezado idéntico */}
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">{id ? 'Editar Factura' : 'Nueva Factura'}</h1>
        </div>
      </div>

      <div className="app-content">
        <Card>
          {metadata && (
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: '0.85em' }}>
                Creada: {metadata.creado_en} &nbsp;|&nbsp; Actualizada: {metadata.actualizado_en}
              </Text>
            </div>
          )}

          <Form form={form} layout="vertical" onFinish={onFinish}>
            {/* Emisor */}
            <Card size="small" title="Emisor" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item
                    label="Empresa"
                    name="empresa_id"
                    rules={[{ required: true, message: 'Requerido' }]}
                  >
                    <Select
                      options={empresas}
                      showSearch
                      optionFilterProp="label"
                      onChange={(v) => onEmpresaChange(v)}
                      disabled={fieldDisabled(false)}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Lugar de expedición (CP)" name="lugar_expedicion">
                    <Input disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    label="Folio"
                    name="folio"
                    rules={[{ required: true, message: 'Requerido' }]}
                  >
                    <InputNumber min={1} style={{ width: '100%' }} disabled={fieldDisabled(false)} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item label="Nombre fiscal (emisor)" name="nombre_fiscal_emisor">
                    <Input disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="Régimen fiscal (emisor)" name="regimen_fiscal_emisor">
                    <Select options={regimenes} disabled />
                  </Form.Item>
                </Col>
              </Row>
              {rfcEmisor ? <Text type="secondary">RFC: {rfcEmisor}</Text> : null}
            </Card>

            {/* Receptor */}
            <Card size="small" title="Receptor" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item label="Cliente" name="cliente_id" rules={[{ required: true, message: 'Requerido' }]}>
                    <Select
                      showSearch
                      filterOption={false}
                      onSearch={buscarClientes}
                      options={clienteOpts}            // ← antes había un hack con form.__INTERNAL__
                      disabled={fieldDisabled(!empresaId)}
                      onChange={(v) => onClienteChange(v)}
                      placeholder={!empresaId ? 'Selecciona una empresa' : 'Buscar cliente...'}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="Nombre fiscal (receptor)" name="nombre_fiscal_receptor">
                    <Input disabled />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item label="RFC receptor" name="rfc_receptor">
                    <Input disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Régimen fiscal (receptor)" name="regimen_fiscal_receptor">
                    <Select options={regimenes} disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="CP receptor" name="cp_receptor">
                    <Input disabled />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* Fechas y estados */}
            <Card size="small" title="Fechas y estados" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={24} md={6}>
                  <Form.Item
                    label="Fecha emisión"
                    name="fecha_emision"
                    rules={[{ required: true, message: 'Requerido' }]}
                  >
                    <DatePicker
                      style={{ width: '100%' }}
                      onChange={onFechaEmisionChange}
                      disabled={fieldDisabled(false)}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Fecha timbrado" name="fecha_timbrado">
                    <DatePicker style={{ width: '100%' }} disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Fecha pago (programada)" name="fecha_pago">
                    <DatePicker style={{ width: '100%' }} disabled={fieldDisabled(false)} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.status_pago !== currentValues.status_pago}>
                    {({ getFieldValue }) => (
                      <Form.Item
                        label="Fecha cobro (real)"
                        name="fecha_cobro"
                        rules={
                          getFieldValue('status_pago') === 'PAGADA'
                            ? [{ required: true, message: 'Captura la fecha de cobro' }]
                            : []
                        }
                      >
                        <DatePicker
                          style={{ width: '100%' }}
                          disabled={fieldAlwaysEditable('fecha_cobro')}
                        />
                      </Form.Item>
                    )}
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16} align="bottom">
                <Col xs={24} md={6}>
                  <Form.Item label="Estatus CFDI">
                    <Input value={estatusCFDI} disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Estatus de pago" name="status_pago" initialValue={statusPago}>
                    <Select
                      options={[
                        { value: 'NO_PAGADA', label: 'NO_PAGADA' },
                        { value: 'PAGADA', label: 'PAGADA' },
                      ]}
                      disabled={fieldAlwaysEditable('status_pago')}
                      onChange={(v) => form.setFieldValue('status_pago', v)}
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* CFDI */}
            <Card size="small" title="CFDI" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={24} md={6}>
                  <Form.Item
                    label="Moneda"
                    name="moneda"
                    rules={[{ required: true, message: 'Requerido' }]}
                  >
                    <Select
                      options={[
                        { value: 'MXN', label: 'MXN' },
                        { value: 'USD', label: 'USD' },
                      ]}
                      disabled={fieldDisabled(!empresaId)}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Tipo de cambio" name="tipo_cambio">
                    <InputNumber
                      min={0}
                      step={0.0001}
                      disabled={fieldDisabled(moneda !== 'USD' || !empresaId)}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Método de pago" name="metodo_pago">
                    <Select allowClear options={metodosPago} disabled={fieldDisabled(!empresaId)} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Forma de pago" name="forma_pago">
                    <Select allowClear options={formaPagoOptions} disabled={fieldDisabled(!empresaId)} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item label="Folio fiscal (UUID)" name="folio_fiscal">
                    <Input disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Uso CFDI" name="uso_cfdi">
                    <Select allowClear options={usosCfdi} disabled={fieldDisabled(!empresaId)} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Condiciones de pago" name="condiciones_pago">
                    <Input disabled={fieldDisabled(!empresaId)} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={6}>
                  <Form.Item valuePropName="checked" name="tiene_relacion" initialValue={false}>
                    <Checkbox disabled={fieldDisabled(!empresaId)}>¿Tiene relación CFDI?</Checkbox>
                  </Form.Item>
                </Col>
                <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.tiene_relacion !== currentValues.tiene_relacion}>
                  {({ getFieldValue }) => (
                    <>
                      <Col xs={24} md={9}>
                        <Form.Item label="Tipo relación" name="cfdi_relacionados_tipo">
                          <Select
                            allowClear
                            options={tiposRelacion}
                            disabled={fieldDisabled(!getFieldValue('tiene_relacion') || !empresaId)}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={9}>
                        <Form.Item
                          label="CFDIs relacionados"
                          name="cfdi_relacionados"
                          tooltip="Separados por coma o texto libre"
                        >
                          <Input disabled={fieldDisabled(!getFieldValue('tiene_relacion') || !empresaId)} />
                        </Form.Item>
                      </Col>
                    </>
                  )}
                </Form.Item>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={24}>
                  <Form.Item label="Observaciones" name="observaciones">
                    <Input.TextArea rows={3} disabled={fieldAlwaysEditable('observaciones')} />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* Conceptos */}
            <Card
              size="small"
              title="Conceptos"
              extra={
                <Space>
                  <Button
                    icon={<PlusOutlined />}
                    onClick={() => {
                      setEditingConcepto(null);
                      setEditingConceptoIndex(null);
                      setIsConceptoModalOpen(true);
                    }}
                    disabled={fieldDisabled(!empresaId)}
                  >
                    Agregar concepto
                  </Button>
                  <Button
                    icon={<PlusCircleOutlined />}
                    onClick={() => setPsModalOpen(true)}
                    disabled={fieldDisabled(!empresaId)}
                  >
                    Nuevo producto/servicio
                  </Button>
                </Space>
              }
            >
              <Table
                size="small"
                bordered
                dataSource={conceptos}
                rowKey={(r, i) => String((r as any).id ?? i)}
                pagination={false}
                columns={[
                  { title: 'Clave SAT', dataIndex: 'clave_producto', key: 'clave_producto' },
                  { title: 'Descripción', dataIndex: 'descripcion', key: 'descripcion' },
                  { title: 'Unidad SAT', dataIndex: 'clave_unidad', key: 'clave_unidad' },
                  { title: 'Cantidad', dataIndex: 'cantidad', key: 'cantidad', align: 'right' },
                  {
                    title: 'P. Unitario',
                    dataIndex: 'valor_unitario',
                    key: 'valor_unitario',
                    align: 'right',
                    render: (v) => Number(v).toFixed(2),
                  },
                  {
                    title: 'Tasa IVA',
                    dataIndex: 'iva_tasa',
                    key: 'iva_tasa',
                    align: 'right',
                    render: (v) => (v != null ? Number(v).toFixed(3) : '0.000'),
                  },
                  {
                    title: 'Ret IVA',
                    dataIndex: 'ret_iva_tasa',
                    key: 'ret_iva_tasa',
                    align: 'right',
                    render: (v) => (v != null ? Number(v).toFixed(6) : '0.000000'),
                  },
                  {
                    title: 'Ret ISR',
                    dataIndex: 'ret_isr_tasa',
                    key: 'ret_isr_tasa',
                    align: 'right',
                    render: (v) => (v != null ? Number(v).toFixed(6) : '0.000000'),
                  },
                  {
                    title: 'Importe',
                    key: 'importe',
                    align: 'right',
                    render: (_: any, r: any) => {
                      const cantidad = Number(r.cantidad || 0);
                      const valor_unitario = Number(r.valor_unitario || 0);
                      const descuento = Number(r.descuento || 0);
                      const iva_tasa = Number(r.iva_tasa || 0);
                      const ret_iva_tasa = Number(r.ret_iva_tasa || 0);
                      const ret_isr_tasa = Number(r.ret_isr_tasa || 0);
                      const base = Math.max(cantidad * valor_unitario - descuento, 0);
                      const iva = base * iva_tasa;
                      const ret_iva = base * ret_iva_tasa;
                      const ret_isr = base * ret_isr_tasa;
                      const importe = base + iva - ret_iva - ret_isr;
                      return importe.toFixed(2);
                    },
                  },
                  {
                    title: 'Acciones',
                    key: 'acciones',
                    align: 'center',
                    render: (_: any, record: any, index: number) => (
                      <Space>
                        <Button
                          type="link"
                          icon={<EditOutlined />}
                          onClick={() => {
                            setEditingConcepto(record);
                            setEditingConceptoIndex(index);
                            setIsConceptoModalOpen(true);
                          }}
                          disabled={fieldDisabled(!empresaId)}
                        />
                        <Popconfirm
                          title="¿Eliminar este concepto?"
                          onConfirm={() => {
                            const newConceptos = [...conceptos];
                            newConceptos.splice(index, 1);
                            setConceptos(newConceptos);
                          }}
                          disabled={fieldDisabled(false)}
                        >
                          <Button type="link" danger icon={<DeleteOutlined />} disabled={fieldDisabled(!empresaId)} />
                        </Popconfirm>
                      </Space>
                    ),
                  },
                ]}
              />

              <Divider />

              <Row justify="end" gutter={24}>
                <Col><Text>Subtotal: <b>{resumen.subtotal}</b></Text></Col>
                <Col><Text>Trasladados: <b>{resumen.traslados}</b></Text></Col>
                <Col><Text>Retenciones: <b>{resumen.retenciones}</b></Text></Col>
                <Col><Text>Total: <b>{resumen.total}</b></Text></Col>
              </Row>

            </Card>

            <Divider />

            {/* Botones */}
            <Space>
              <Button onClick={() => router.push('/facturas')}>Regresar</Button>
              <Button type="primary" htmlType="submit" loading={saving}>
                {id ? 'Actualizar' : 'Guardar'}
              </Button>
              <Button
                icon={<ThunderboltOutlined />}
                onClick={timbrarFactura}
                loading={accionLoading.timbrar}
                disabled={!puedeTimbrar}
              >
                Timbrar
              </Button>

              <Button
                danger
                icon={<StopOutlined />}
                onClick={abrirModalCancelacion}
                loading={accionLoading.cancelar || cancelSubmitting}
                disabled={!puedeCancelar}
              >
                Cancelar CFDI
              </Button>

              {id && (
                <Popconfirm
                  title="¿Duplicar factura?"
                  description="Se creará una copia en borrador con un nuevo folio."
                  onConfirm={handleDuplicate}
                  okText="Sí, duplicar"
                  cancelText="Cancelar"
                >
                  <Button icon={<CopyOutlined />}>Duplicar</Button>
                </Popconfirm>
              )}

              {/* Ver/Descargar PDF y XML */}
              <Button icon={<FilePdfOutlined />} onClick={verPDF} disabled={!id}>
                Ver PDF
              </Button>
            </Button>
              )} {/* Botón para enviar vista previa por correo (solo en borrador) */}
            {estatusCFDI === 'BORRADOR' && (
              <Button
                icon={<MailOutlined />}
                onClick={handleSendPreviewEmail}
                loading={isSendingEmail && isSendingPreview}
                disabled={!id}
              >
                Enviar Vista Previa por Correo
              </Button>
            )}

            {/* Botones para facturas timbradas o canceladas */}
            {(estatusCFDI === 'TIMBRADA' || estatusCFDI === 'CANCELADA') && (
              <>
                {estatusCFDI === 'TIMBRADA' && (
                  <Button icon={<FileExcelOutlined />} onClick={descargarXML}>Descargar XML</Button>
                )}

                <Button
                  icon={<MailOutlined />}
                  onClick={handleSendEmail}
                  loading={isSendingEmail && !isSendingPreview}
                  disabled={!id}
                >
                  Enviar por Correo
                </Button>
              </>
            )}
          </Space>
        </Form>
      </Card>

      {/* Campo serie oculto (como el original) */}
      <Form.Item name="serie" hidden>
        <Input />
      </Form.Item>
    </div >

      {/* Modal: Añadir/Editar Concepto */ }
      < Modal
  title = { editingConcepto? 'Editar Concepto': 'Añadir Concepto' }
  open = { isConceptoModalOpen }
  onOk = { handleSaveConcepto }
  onCancel = {() => setIsConceptoModalOpen(false)}
width = { 840}
destroyOnHidden
okButtonProps = {{ disabled: isFormDisabled }}
      >
  <Form form={conceptoForm} layout="vertical">
    <Form.Item
      label="Producto/Servicio (catálogo de tu empresa)"
      name="ps_lookup"
      rules={[{ required: true, message: 'Selecciona un producto/servicio' }]}
    >
      <Select
        showSearch
        placeholder="Buscar en catálogo de la empresa…"
        filterOption={false}
        onSearch={buscarPS}
        options={psOpts}
        onSelect={onSelectPSInModal}
        disabled={!empresaId || isFormDisabled}
      />
    </Form.Item>

    <Row gutter={16}>
      <Col span={12}>
        <Form.Item label="Clave SAT" name="clave_producto">
          <Input disabled />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item label="Unidad SAT" name="clave_unidad">
          <Input disabled />
        </Form.Item>
      </Col>
    </Row>

    <Form.Item label="Descripción" name="descripcion">
      <Input.TextArea rows={2} disabled />
    </Form.Item>

    <Row gutter={16}>
      <Col span={8}>
        <Form.Item label="Cantidad" name="cantidad" rules={[{ required: true }]} initialValue={1}>
          <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item label="Valor Unitario" name="valor_unitario" rules={[{ required: true }]}>
          <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item label="Descuento" name="descuento">
          <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
        </Form.Item>
      </Col>
    </Row>

    <Row gutter={16}>
      <Col span={8}>
        <Form.Item label="IVA Tasa" name="iva_tasa" initialValue={0.08}>
          <Select
            options={[
              { value: 0, label: '0%' },
              { value: 0.08, label: '8%' },
              { value: 0.16, label: '16%' },
            ]}
            disabled={isFormDisabled}
          />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item label="Ret. IVA Tasa" name="ret_iva_tasa" initialValue={0}>
          <Select
            options={[
              { value: 0, label: '0%' },
              { value: 0.106667, label: '10.6667% (2/3 del IVA)' },
            ]}
            disabled={isFormDisabled}
          />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item label="Ret. ISR Tasa" name="ret_isr_tasa" initialValue={0}>
          <Select
            options={[
              { value: 0, label: '0%' },
              { value: 0.1, label: '10% (honorarios/arrendamiento)' },
              { value: 0.0125, label: '1.25% (RESICO PF retenido por PM)' },
            ]}
            disabled={isFormDisabled}
          />
        </Form.Item>
      </Col>
    </Row>
  </Form>
      </Modal >

  {/* Modal: Cancelación CFDI */ }
  < Modal
title = "Cancelar CFDI"
open = { cancelModalOpen }
onCancel = {() => setCancelModalOpen(false)}
onOk = { submitCancel }
okText = "Enviar cancelación"
confirmLoading = { cancelSubmitting }
destroyOnClose
  >
        <Alert
          style={{ marginBottom: 12 }}
          type="info"
          message="Se enviará la solicitud de cancelación al PAC. Si el motivo es '01', debes indicar el folio fiscal del CFDI sustituto."
          showIcon
        />
        <Form form={cancelForm} layout="vertical">
          <Form.Item
            label="Motivo de cancelación"
            name="motivo"
            rules={[{ required: true, message: 'Selecciona un motivo' }]}
            tooltip="Si eliges 01 debes indicar el folio fiscal (UUID) del CFDI sustituto."
          >
            <Select
              options={motivosCancel}
              showSearch
              optionFilterProp="label"
              placeholder="Selecciona el motivo…"
            />
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(p, c) => p.motivo !== c.motivo}>
            {({ getFieldValue }) => {
              const motivo = String(getFieldValue('motivo') || '');
              const necesitaSustituto = motivo === '01';
              return (
                <Form.Item
                  label="Folio fiscal sustituto (UUID)"
                  name="folio_sustitucion"
                  rules={
                    necesitaSustituto
                      ? [
                        { required: true, message: 'Requerido cuando el motivo es 01' },
                        {
                          validator: (_, v) => {
                            if (!v) return Promise.resolve();
                            const ok = /^[0-9A-Fa-f-]{36}$/.test(String(v).trim());
                            return ok ? Promise.resolve() : Promise.reject(new Error('UUID inválido'));
                          },
                        },
                      ]
                      : []
                  }
                >
                  <Input
                    placeholder={
                      necesitaSustituto
                        ? 'Ej. ABC1147C-D41E-4596-9C3E-45629B090000'
                        : 'Opcional'
                    }
                    disabled={!necesitaSustituto}
                  />
                </Form.Item>
              );
            }}
          </Form.Item>
        </Form>
      </Modal >

  {/* Modal: Crear Producto/Servicio */ }
  < Modal
title = "Nuevo producto/servicio"
open = { psModalOpen }
onCancel = {() => setPsModalOpen(false)}
onOk = { async() => {
  try {
    const vals = await psForm.validateFields();
    const { createProductoServicio } = await import('@/services/facturaService');
    await createProductoServicio({
      tipo: vals.tipo,
      clave_producto: vals.clave_producto?.value ?? vals.clave_producto,
      clave_unidad: vals.clave_unidad?.value ?? vals.clave_unidad,
      descripcion: vals.descripcion,
      cantidad: vals.cantidad ?? null,
      valor_unitario: Number(vals.valor_unitario),
      empresa_id: form.getFieldValue('empresa_id'),
      stock_actual: vals.tipo === TipoProductoServicio.PRODUCTO ? Number(vals.stock_actual || 0) : 0,
      stock_minimo: vals.tipo === TipoProductoServicio.PRODUCTO ? Number(vals.stock_minimo || 0) : null,
      unidad_inventario: vals.tipo === TipoProductoServicio.PRODUCTO ? vals.unidad_inventario || null : null,
      ubicacion: vals.tipo === TipoProductoServicio.PRODUCTO ? vals.ubicacion || null : null,
      requiere_lote: vals.tipo === TipoProductoServicio.PRODUCTO ? Boolean(vals.requiere_lote) : false,
    });
    message.success('Producto/Servicio creado');
    setPsModalOpen(false);
    psForm.resetFields();
  } catch {
    // errores ya manejados
  }
}}
okButtonProps = {{ loading: psSaving, disabled: !empresaId || isFormDisabled }}
destroyOnClose
  >
  <Form form={psForm} layout="vertical">
    <Form.Item label="Tipo" name="tipo" rules={[{ required: true }]}>
      <Select
        options={[
          { value: TipoProductoServicio.PRODUCTO, label: 'Producto' },
          { value: TipoProductoServicio.SERVICIO, label: 'Servicio' },
        ]}
        disabled={isFormDisabled}
      />
    </Form.Item>

    <Form.Item label="Clave producto (SAT)" name="clave_producto" rules={[{ required: true }]}>
      <Select
        labelInValue
        showSearch
        filterOption={false}
        onSearch={buscarClavesProductoSAT}
        options={claveSatOpts}
        placeholder="Buscar en catálogo del SAT (mín. 3 caracteres)…"
        disabled={isFormDisabled}
      />
    </Form.Item>

    <Form.Item label="Unidad SAT" name="clave_unidad" rules={[{ required: true }]}>
      <Select
        labelInValue
        showSearch
        filterOption={false}
        onSearch={buscarUnidadesSAT}
        options={unidadOpts}
        disabled={isFormDisabled}
      />
    </Form.Item>

    <Form.Item label="Descripción" name="descripcion" rules={[{ required: true }]}>
      <Input.TextArea rows={2} disabled={isFormDisabled} />
    </Form.Item>

    <Form.Item label="Valor unitario" name="valor_unitario" rules={[{ required: true }]}>
      <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
    </Form.Item>

    {/* Campos de inventario condicionales (PRODUCTO) */}
    <Form.Item noStyle shouldUpdate={(p, c) => p.tipo !== c.tipo}>
      {({ getFieldValue }) =>
        getFieldValue('tipo') === TipoProductoServicio.PRODUCTO ? (
          <>
            <Form.Item label="Stock actual" name="stock_actual">
              <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
            </Form.Item>
            <Form.Item label="Stock mínimo" name="stock_minimo">
              <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
            </Form.Item>
            <Form.Item label="Unidad inventario" name="unidad_inventario">
              <Input maxLength={20} disabled={isFormDisabled} />
            </Form.Item>
            <Form.Item label="Ubicación" name="ubicacion">
              <Input maxLength={100} disabled={isFormDisabled} />
            </Form.Item>
            <Form.Item valuePropName="checked" name="requiere_lote" initialValue={false}>
              <Checkbox disabled={isFormDisabled}>¿Requiere lote?</Checkbox>
            </Form.Item>
          </>
        ) : null
      }
    </Form.Item>
  </Form>
      </Modal >

  {/* Modal: Crear Producto/Servicio */ }
  < Modal
title = "Nuevo producto/servicio"
open = { psModalOpen }
onCancel = {() => setPsModalOpen(false)}
onOk = { async() => {
  try {
    const vals = await psForm.validateFields();
    const { createProductoServicio } = await import('@/services/facturaService');
    await createProductoServicio({
      tipo: vals.tipo,
      clave_producto: vals.clave_producto?.value ?? vals.clave_producto,
      clave_unidad: vals.clave_unidad?.value ?? vals.clave_unidad,
      descripcion: vals.descripcion,
      cantidad: vals.cantidad ?? null,
      valor_unitario: Number(vals.valor_unitario),
      empresa_id: form.getFieldValue('empresa_id'),
      stock_actual: vals.tipo === TipoProductoServicio.PRODUCTO ? Number(vals.stock_actual || 0) : 0,
      stock_minimo: vals.tipo === TipoProductoServicio.PRODUCTO ? Number(vals.stock_minimo || 0) : null,
      unidad_inventario: vals.tipo === TipoProductoServicio.PRODUCTO ? vals.unidad_inventario || null : null,
      ubicacion: vals.tipo === TipoProductoServicio.PRODUCTO ? vals.ubicacion || null : null,
      requiere_lote: vals.tipo === TipoProductoServicio.PRODUCTO ? Boolean(vals.requiere_lote) : false,
    });
    message.success('Producto/Servicio creado');
    setPsModalOpen(false);
    psForm.resetFields();
  } catch {
    // errores ya manejados
  }
}}
okButtonProps = {{ loading: psSaving, disabled: !empresaId || isFormDisabled }}
destroyOnClose
  >
  <Form form={psForm} layout="vertical">
    <Form.Item label="Tipo" name="tipo" rules={[{ required: true }]}>
      <Select
        options={[
          { value: TipoProductoServicio.PRODUCTO, label: 'Producto' },
          { value: TipoProductoServicio.SERVICIO, label: 'Servicio' },
        ]}
        disabled={isFormDisabled}
      />
    </Form.Item>

    <Form.Item label="Clave producto (SAT)" name="clave_producto" rules={[{ required: true }]}>
      <Select
        labelInValue
        showSearch
        filterOption={false}
        onSearch={buscarClavesProductoSAT}
        options={claveSatOpts}
        placeholder="Buscar en catálogo del SAT (mín. 3 caracteres)…"
        disabled={isFormDisabled}
      />
    </Form.Item>

    <Form.Item label="Unidad SAT" name="clave_unidad" rules={[{ required: true }]}>
      <Select
        labelInValue
        showSearch
        filterOption={false}
        onSearch={buscarUnidadesSAT}
        options={unidadOpts}
        disabled={isFormDisabled}
      />
    </Form.Item>

    <Form.Item label="Descripción" name="descripcion" rules={[{ required: true }]}>
      <Input.TextArea rows={2} disabled={isFormDisabled} />
    </Form.Item>

    <Form.Item label="Valor unitario" name="valor_unitario" rules={[{ required: true }]}>
      <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
    </Form.Item>

    {/* Campos de inventario condicionales (PRODUCTO) */}
    <Form.Item noStyle shouldUpdate={(p, c) => p.tipo !== c.tipo}>
      {({ getFieldValue }) =>
        getFieldValue('tipo') === TipoProductoServicio.PRODUCTO ? (
          <>
            <Form.Item label="Stock actual" name="stock_actual">
              <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
            </Form.Item>
            <Form.Item label="Stock mínimo" name="stock_minimo">
              <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
            </Form.Item>
            <Form.Item label="Unidad inventario" name="unidad_inventario">
              <Input maxLength={20} disabled={isFormDisabled} />
            </Form.Item>
            <Form.Item label="Ubicación" name="ubicacion">
              <Input maxLength={100} disabled={isFormDisabled} />
            </Form.Item>
            <Form.Item valuePropName="checked" name="requiere_lote" initialValue={false}>
              <Checkbox disabled={isFormDisabled}>¿Requiere lote?</Checkbox>
            </Form.Item>
          </>
        ) : null
      }
    </Form.Item>
  </Form>
      </Modal >

  {/* Modal: Cancelación CFDI */ }
  < Modal
title = "Cancelar CFDI"
open = { cancelModalOpen }
onCancel = {() => setCancelModalOpen(false)}
onOk = { submitCancel }
okText = "Enviar cancelación"
confirmLoading = { cancelSubmitting }
destroyOnClose
  >
        <Alert
          style={{ marginBottom: 12 }}
          type="info"
          message="Se enviará la solicitud de cancelación al PAC. Si el motivo es '01', debes indicar el folio fiscal del CFDI sustituto."
          showIcon
        />
        <Form form={cancelForm} layout="vertical">
          <Form.Item
            label="Motivo de cancelación"
            name="motivo"
            rules={[{ required: true, message: 'Selecciona un motivo' }]}
            tooltip="Si eliges 01 debes indicar el folio fiscal (UUID) del CFDI sustituto."
          >
            <Select
              options={motivosCancel}
              showSearch
              optionFilterProp="label"
              placeholder="Selecciona el motivo…"
            />
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(p, c) => p.motivo !== c.motivo}>
            {({ getFieldValue }) => {
              const motivo = String(getFieldValue('motivo') || '');
              const necesitaSustituto = motivo === '01';
              return (
                <Form.Item
                  label="Folio fiscal sustituto (UUID)"
                  name="folio_sustitucion"
                  rules={
                    necesitaSustituto
                      ? [
                        { required: true, message: 'Requerido cuando el motivo es 01' },
                        {
                          validator: (_, v) => {
                            if (!v) return Promise.resolve();
                            const ok = /^[0-9A-Fa-f-]{36}$/.test(String(v).trim());
                            return ok ? Promise.resolve() : Promise.reject(new Error('UUID inválido'));
                          },
                        },
                      ]
                      : []
                  }
                >
                  <Input
                    placeholder={
                      necesitaSustituto
                        ? 'Ej. ABC1147C-D41E-4596-9C3E-45629B090000'
                        : 'Opcional'
                    }
                    disabled={!necesitaSustituto}
                  />
                </Form.Item>
              );
            }}
          </Form.Item>
        </Form>
      </Modal >

  {/* Modal: Enviar Correo */ }
  < Modal
title = "Enviar Factura por Correo"
open = { isEmailModalOpen }
onCancel = {() => setIsEmailModalOpen(false)}
onOk = { onEmailModalOk }
okText = "Enviar"
confirmLoading = { isSendingEmail }
destroyOnClose
  >
  <Form form={emailForm} layout="vertical">
    <Form.Item
      label="Correos del Destinatario (separados por coma)"
      name="recipient_emails"
      rules={[
        { required: true, message: 'Por favor ingresa al menos un correo del destinatario' },
        {
          validator: (_, value) => {
            if (!value) return Promise.resolve();
            // Acepta comas, punto y coma y saltos de línea como separadores
            const emails: string[] = String(value)
              .split(/[;,\n]+/)
              .map((email: string) => email.trim())
              .filter(Boolean);
            // Regex más permisivo (permite +, TLD > 4, etc.)
            const simpleEmail = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/i;
            const invalidEmails = emails.filter((email: string) => !simpleEmail.test(email));
            if (invalidEmails.length > 0) {
              return Promise.reject(new Error(`Los siguientes correos no son válidos: ${invalidEmails.join(',')}`));
            }
            return Promise.resolve();
          },
        },
      ]}
    >
      <Input.TextArea rows={4} placeholder="correo1@dominio.com, correo2@dominio.com (también puedes usar ; o saltos de línea)" />
    </Form.Item>
  </Form>
      </Modal >
  {/* Modal: Vista Previa PDF */ }
  < Modal
title = "Vista Previa de Factura"
open = { previewModalOpen }
onCancel = { cerrarPreview }
footer = {
  [
  <Button key="close" onClick={cerrarPreview}>
    Cerrar
  </Button>,
  <Button key="download" type="primary" icon={<FilePdfOutlined />} onClick={descargarPDF}>
    Descargar
  </Button>,
        ]}
width = "90%"
style = {{ top: 20 }}
styles = {{ body: { height: '80vh', padding: 0 } }}
destroyOnHidden
  >
  { previewPdfUrl && (
    <iframe
      src={previewPdfUrl}
      style={{ width: '100%', height: '100%', border: 'none' }}
      title="Vista Previa PDF"
    />
  )}
      </Modal >
    </>
  );
};

export default FacturaFormPage;