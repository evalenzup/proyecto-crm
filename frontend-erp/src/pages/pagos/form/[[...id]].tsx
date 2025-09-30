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
} from '@ant-design/icons';

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
    clientes,
    formasPago,
    facturasPendientes,
    paymentAllocation,
    handleAllocationChange,
    onFinish,
    generarComplemento,
    enviarComplemento,
    cancelarComplemento,
    verPdf,
    descargarPdf,
    descargarXml,
  } = usePagoForm();

  const totalAllocated = React.useMemo(() => {
    return Object.values(paymentAllocation).reduce((sum, amount) => sum + (amount || 0), 0);
  }, [paymentAllocation]);

  useEffect(() => {
    form.setFieldsValue({ monto: totalAllocated });
  }, [totalAllocated, form]);

  useEffect(() => {
    if (pago) {
      form.setFieldsValue({
        uuid_cfdi: pago.uuid_cfdi,
        timbrado_at: pago.timbrado_at ? new Date(pago.timbrado_at).toLocaleString('es-MX') : undefined,
      });
    }
  }, [pago, form]);

  useEffect(() => {
    if (!id) {
      form.setFieldsValue({ folio: 1 });
    }
  }, [id, form]);

  if (loading) return <Spin style={{ margin: 48 }} />;

  const facturasColumns = [
    { title: 'Folio', dataIndex: 'folio', render: (val: any, rec: any) => `${rec.serie}-${val}` },
    { title: 'Fecha Emisión', dataIndex: 'fecha_emision', render: (val: string) => new Date(val).toLocaleDateString() },
    { title: 'Total Factura', dataIndex: 'total', align: 'right', render: (val: number) => val.toLocaleString('es-MX', {style: 'currency', currency: 'MXN'}) },
    {
      title: 'Monto a Pagar',
      dataIndex: 'id',
      key: 'monto_a_pagar',
      width: 180,
      render: (facturaId: string, record: FacturaPendiente) => (
        <InputNumber
          min={0}
          max={record.total} // A real saldo would be better
          value={paymentAllocation[facturaId]}
          onChange={(value) => handleAllocationChange(facturaId, value)}
          style={{ width: '100%' }}
          addonBefore="$"
          controls={false}
          disabled={!!pago?.timbrado_at}
        />
      ),
    },
  ];

  const isTimbrado = !!pago?.timbrado_at;
  const isCancelado = !!pago?.cancelado_at;

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
                <Form.Item label="Cliente" name="cliente_id" rules={[{ required: true }]}>
                  <Select options={clientes} showSearch filterOption={false} placeholder="Seleccione un cliente" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card size="small" title="Datos del Pago" style={{ marginBottom: 16 }}>
             <Row gutter={16}>
                <Col xs={24} md={8}>
                    <Form.Item label="Fecha de Pago" name="fecha_pago" rules={[{ required: true }]}>
                        <DatePicker style={{ width: '100%' }} />
                    </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                    <Form.Item label="Forma de Pago" name="forma_pago_p" rules={[{ required: true }]}>
                        <Select placeholder="Seleccione una forma de pago" options={formasPago} />
                    </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                    <Form.Item label="Monto" name="monto" rules={[{ required: true }]}>
                        <InputNumber min={0} style={{ width: '100%' }} addonBefore="$" disabled />
                    </Form.Item>
                </Col>
             </Row>
             <Row gutter={16}>
                <Col xs={24} md={8}>
                    <Form.Item label="Moneda" name="moneda_p" rules={[{ required: true }]}>
                        <Select options={[{label: 'MXN', value: 'MXN'}, {label: 'USD', value: 'USD'}]} />
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

          <Divider />

          <Space wrap>
            <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/pagos')}>Regresar</Button>
            <Button icon={<SaveOutlined />} type="primary" htmlType="submit" loading={saving} disabled={isTimbrado || isCancelado}>
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
              onClick={enviarComplemento}
              loading={accionLoading.enviando}
              disabled={!isTimbrado || isCancelado}
            >
              Enviar por Correo
            </Button>
            <Button
              icon={<FilePdfOutlined />}
              onClick={verPdf}
              loading={accionLoading.visualizando}
              disabled={!id || isCancelado}
            >
              Ver PDF
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={descargarPdf}
              loading={accionLoading.descargando}
              disabled={!id || isCancelado}
            >
              Descargar PDF
            </Button>
            <Button
              icon={<FileTextOutlined />}
              onClick={descargarXml}
              loading={accionLoading.descargando}
              disabled={!isTimbrado || isCancelado}
            >
              Descargar XML
            </Button>
            <Button
              icon={<DeleteOutlined />}
              danger
              onClick={cancelarComplemento}
              loading={accionLoading.cancelando}
              disabled={!isTimbrado || isCancelado}
            >
              Cancelar Complemento
            </Button>
          </Space>
        </Form>
      </div>
    </>
  );
};

export default PagoFormPage;
