// src/pages/presupuestos/form/[[...id]].tsx

import React, { useMemo } from 'react';
import { useRouter } from 'next/router';
import {
  Form,
  Button,
  Input,
  Select,
  DatePicker,
  Row,
  Col,
  Card,
  Space,
  Table,
  InputNumber,
  Popconfirm,
  Divider,
  Typography,
  Modal,
  Tag,
  Dropdown,
  Upload,
  message,
} from 'antd';
import type { MenuProps } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, FilePdfOutlined, DownOutlined, UploadOutlined, PaperClipOutlined, FileDoneOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd/es/upload/interface';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { usePresupuestoForm } from '@/hooks/usePresupuestoForm';
import { formatCurrency } from '@/utils/format';
import { PresupuestoDetalle } from '@/models/presupuesto';
import dayjs from 'dayjs';
import api from '@/lib/axios';

const { TextArea } = Input;
const { Text } = Typography;

const PresupuestoFormPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const presupuestoId = Array.isArray(id) ? id[0] : id;

  const {
    form,
    isSubmitting,
    loading,
    presupuesto,
    onFinish,
    clientesOptions,
    empresasOptions,
    empresaId,
    onEmpresaChange,
    buscarClientes,
    onFechaEmisionChange,
    // Versioning
    versionHistory,
    selectedVersionId,
    setSelectedVersionId,
    // Status Change
    statusUpdateMutation,
    uploadEvidenciaMutation,
    conversionMutation,
    // Conceptos
    conceptos,
    setConceptos,
    isConceptoModalOpen,
    setIsConceptoModalOpen,
    editingConcepto,
    setEditingConcepto,
    setEditingConceptoIndex,
    conceptoForm,
    buscarPS,
    psOpts,
    onSelectPSInModal,
    handleSaveConcepto,
    // Quick Cliente
    isClienteModalOpen,
    setIsClienteModalOpen,
    quickClienteForm,
    handleSaveQuickCliente,
    verPDF,
  } = usePresupuestoForm(presupuestoId);

  const isReadOnly = useMemo(() => {
    if (!presupuesto || !versionHistory.length) return false;
    const latestVersion = versionHistory.reduce((prev, current) => (prev.version > current.version) ? prev : current);
    return presupuesto.id !== latestVersion.id;
  }, [presupuesto, versionHistory]);

  const subtotal = useMemo(() =>
    conceptos.reduce((acc, item) => acc + (item.cantidad || 0) * (item.precio_unitario || 0), 0),
    [conceptos]
  );
  const impuestos = useMemo(() =>
    conceptos.reduce((acc, item) => acc + (item.cantidad || 0) * (item.precio_unitario || 0) * (item.tasa_impuesto || 0), 0),
    [conceptos]
  );
  const total = subtotal + impuestos;

  const handleStatusChange = (estado: string) => {
    if (!selectedVersionId) return;
    statusUpdateMutation.mutate({ id: selectedVersionId, estado });
  };

  const statusMenuItems: MenuProps['items'] = [
    {
      key: 'ACEPTADO',
      label: 'Aceptar',
      onClick: () => handleStatusChange('ACEPTADO'),
    },
    {
      key: 'RECHAZADO',
      label: 'Rechazar',
      onClick: () => handleStatusChange('RECHAZADO'),
    },
    {
      key: 'BORRADOR',
      label: 'Poner en Borrador',
      onClick: () => handleStatusChange('BORRADOR'),
    },
  ];

  const uploadProps: UploadProps = {
    beforeUpload: file => {
      if (selectedVersionId) {
        uploadEvidenciaMutation.mutate({ id: selectedVersionId, file });
      } else {
        message.error("No se ha seleccionado un presupuesto para adjuntar la evidencia.");
      }
      return false; // Prevent auto-upload
    },
    showUploadList: false,
  };

  // Helper para obtener la URL base (sin /api)
  const getBaseUrl = () => {
    const apiUrl = api.defaults.baseURL || '';
    return apiUrl.endsWith('/api') ? apiUrl.slice(0, -4) : apiUrl;
  };

  const detalleColumns = [
    { title: 'Descripción', dataIndex: 'descripcion', key: 'descripcion' },
    { title: 'Cantidad', dataIndex: 'cantidad', key: 'cantidad', align: 'right' as const },
    {
      title: 'Precio Unitario',
      dataIndex: 'precio_unitario',
      key: 'precio_unitario',
      align: 'right' as const,
      render: (value: number) => formatCurrency(value),
    },
    {
      title: 'Importe',
      key: 'importe',
      align: 'right' as const,
      render: (_: unknown, record: PresupuestoDetalle) => formatCurrency(record.importe),
    },
    {
      title: 'Acciones',
      key: 'action',
      width: 100,
      align: 'center' as const,
      render: (_: unknown, record: PresupuestoDetalle, index: number) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            disabled={isReadOnly}
            onClick={() => {
              setEditingConcepto(record);
              setEditingConceptoIndex(index);
              conceptoForm.setFieldsValue(record);
              setIsConceptoModalOpen(true);
            }}
          />
          <Popconfirm
            title="¿Eliminar línea?"
            disabled={isReadOnly}
            onConfirm={() => {
              setConceptos(conceptos.filter((_, i) => i !== index));
            }}
          >
            <Button type="link" danger icon={<DeleteOutlined />} disabled={isReadOnly} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">{presupuestoId ? `Presupuesto: ${presupuesto?.folio || ''}` : 'Nuevo Presupuesto'}</h1>
        </div>
      </div>
      <div className="app-content">

        {/* Version Selector outside the form */}
        {presupuestoId && (
          <Card size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} md={16}>
                <Form.Item label="Versión del Presupuesto" style={{ marginBottom: 0 }}>
                  {versionHistory.length > 0 ? (
                    <Select
                      value={selectedVersionId}
                      onChange={(value) => setSelectedVersionId(value)}
                      options={versionHistory.map(v => ({
                        value: v.id,
                        label: `Versión ${v.version} (${v.estado}) - ${dayjs(v.creado_en).format('DD/MM/YY HH:mm')}`
                      }))}
                    />
                  ) : (
                    <Input value={presupuesto?.version || 1} disabled />
                  )}
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Estado Actual" style={{ marginBottom: 0 }}>
                  <Tag color={presupuesto?.estado === 'ARCHIVADO' ? 'orange' : 'blue'} style={{ fontSize: 14, padding: '4px 8px' }}>{presupuesto?.estado || 'BORRADOR'}</Tag>
                </Form.Item>
              </Col>
            </Row>
          </Card>
        )}

        <Form form={form} layout="vertical" onFinish={onFinish} disabled={loading || isReadOnly}>
          <Card size="small" title="Datos Generales" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} md={8}>
                <Form.Item name="folio" label="Folio">
                  <Input disabled />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item name="empresa_id" label="Empresa Emisora" rules={[{ required: true }]}>
                  <Select
                    placeholder="Seleccionar empresa"
                    options={empresasOptions}
                    onChange={onEmpresaChange}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Cliente" required>
                  <Space.Compact style={{ width: '100%' }}>
                    <Form.Item name="cliente_id" noStyle rules={[{ required: true, message: 'Selecciona un cliente' }]}>
                      <Select
                        showSearch
                        filterOption={false}
                        placeholder={!empresaId ? 'Selecciona una empresa primero' : 'Buscar cliente...'}
                        options={clientesOptions}
                        onSearch={buscarClientes}
                        disabled={!empresaId || isReadOnly}
                        notFoundContent={null}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                    <Button
                      icon={<PlusOutlined />}
                      onClick={() => setIsClienteModalOpen(true)}
                      disabled={!empresaId || isReadOnly}
                    />
                  </Space.Compact>
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={8}>
                <Form.Item label="Evidencia de Aceptación">
                  {presupuesto?.firma_cliente ? (
                    <Space>
                      <Button icon={<PaperClipOutlined />} href={`${getBaseUrl()}/${presupuesto.firma_cliente}`} target="_blank">
                        Ver Evidencia
                      </Button>
                      <Upload {...uploadProps} disabled={isReadOnly}>
                        <Button icon={<UploadOutlined />} disabled={isReadOnly}>Reemplazar</Button>
                      </Upload>
                    </Space>
                  ) : (
                    <Upload {...uploadProps} disabled={isReadOnly}>
                      <Button icon={<UploadOutlined />} disabled={isReadOnly}>Subir Evidencia</Button>
                    </Upload>
                  )}
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item name="fecha_emision" label="Fecha de Emisión" rules={[{ required: true }]}>
                  <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" onChange={onFechaEmisionChange} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item name="fecha_vencimiento" label="Fecha de Vencimiento">
                  <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item name="condiciones_comerciales" label="Condiciones Comerciales">
                  <TextArea rows={2} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item name="notas_internas" label="Notas Internas">
                  <TextArea rows={2} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card
            size="small"
            title="Conceptos"
            extra={
              <Button icon={<PlusOutlined />} onClick={() => {
                setEditingConcepto(null);
                setEditingConceptoIndex(null);
                conceptoForm.resetFields();
                setIsConceptoModalOpen(true);
              }}
                disabled={!empresaId || isReadOnly}
              >
                Agregar Concepto
              </Button>
            }
          >
            <Table
              size="small"
              columns={detalleColumns}
              dataSource={conceptos}
              rowKey="id"
              pagination={false}
              locale={{ emptyText: 'Agrega conceptos al presupuesto' }}
            />
            <Divider />
            <Row justify="end" gutter={24}>
              <Col><Text>Subtotal: <b>{formatCurrency(subtotal)}</b></Text></Col>
              <Col><Text>Impuestos: <b>{formatCurrency(impuestos)}</b></Text></Col>
              <Col><Text>Total: <b>{formatCurrency(total)}</b></Text></Col>
            </Row>
          </Card>

          <Divider />

          <Row justify="end">
            <Space>
              <Button onClick={() => router.push('/presupuestos')}>Cancelar</Button>
              <Button icon={<FilePdfOutlined />} onClick={verPDF} disabled={!selectedVersionId}>
                Ver PDF
              </Button>

              {presupuesto?.estado === 'ACEPTADO' && (
                <Button
                  icon={<FileDoneOutlined />}
                  onClick={() => {
                    Modal.confirm({
                      title: '¿Convertir a Factura?',
                      content: 'Esta acción creará una nueva factura en estado BORRADOR a partir de este presupuesto. El presupuesto será marcado como FACTURADO.',
                      onOk: () => selectedVersionId && conversionMutation.mutate(selectedVersionId),
                      okText: 'Convertir',
                      cancelText: 'Cancelar',
                    });
                  }}
                  loading={conversionMutation.isPending}
                  disabled={isReadOnly}
                >
                  Convertir a Factura
                </Button>
              )}

              <Dropdown menu={{ items: statusMenuItems }} disabled={isReadOnly || !selectedVersionId}>
                <Button>
                  Cambiar Estado <DownOutlined />
                </Button>
              </Dropdown>
              <Button type="primary" htmlType="submit" loading={isSubmitting} disabled={isReadOnly}>
                {presupuestoId ? 'Crear Nueva Versión' : 'Crear Presupuesto'}
              </Button>
            </Space>
          </Row>
        </Form>
      </div>

      <Modal
        title={editingConcepto ? 'Editar Concepto' : 'Añadir Concepto'}
        open={isConceptoModalOpen}
        onOk={handleSaveConcepto}
        onCancel={() => setIsConceptoModalOpen(false)}
        width={840}
        destroyOnClose
      >
        <Form form={conceptoForm} layout="vertical">
          <Form.Item label="Producto/Servicio (catálogo)">
            <Select
              showSearch
              placeholder="Buscar en catálogo de la empresa…"
              filterOption={false}
              onSearch={buscarPS}
              options={psOpts}
              onSelect={onSelectPSInModal}
              disabled={!empresaId}
            />
          </Form.Item>
          <Form.Item label="Descripción" name="descripcion" rules={[{ required: true }]}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="Cantidad" name="cantidad" rules={[{ required: true }]} initialValue={1}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Precio Unitario" name="precio_unitario" rules={[{ required: true }]} initialValue={0}>
                <InputNumber<number> min={0} style={{ width: '100%' }} formatter={value => `$ ${value}`} parser={value => value!.replace(/\$\s?|(,*)/g, '') as unknown as number} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Tasa de Impuesto" name="tasa_impuesto" rules={[{ required: true }]} initialValue={0.08}>
                <Select
                  options={[
                    { value: 0, label: '0%' },
                    { value: 0.08, label: '8%' },
                    { value: 0.16, label: '16%' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Modal para creación rápida de cliente */}
      <Modal
        title="Crear Cliente Rápido"
        open={isClienteModalOpen}
        onOk={handleSaveQuickCliente}
        onCancel={() => setIsClienteModalOpen(false)}
        destroyOnClose
      >
        <Form form={quickClienteForm} layout="vertical">
          <Form.Item
            name="nombre_comercial"
            label="Nombre Comercial"
            rules={[{ required: true, message: 'El nombre comercial es obligatorio' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email de Contacto">
            <Input type="email" />
          </Form.Item>
          <Form.Item name="telefono" label="Teléfono de Contacto">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default PresupuestoFormPage;
