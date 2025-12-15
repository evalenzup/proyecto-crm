// src/pages/presupuestos/index.tsx

import React, { useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Dropdown, Space, Tag, Modal, Form, Input, Card, Grid, theme, Select, DatePicker, Upload } from 'antd';
import type { MenuProps } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined, MailOutlined, ReloadOutlined, SearchOutlined, FileDoneOutlined, MoreOutlined, TagOutlined, UploadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { usePresupuestoList } from '@/hooks/usePresupuestoList';
import { useTableHeight } from '@/hooks/useTableHeight';
import { PresupuestoSimpleOut } from '@/services/presupuestoService';
import { formatCurrency } from '@/utils/format';

const { RangePicker } = DatePicker;
const { useToken } = theme;



const PresupuestosPage: React.FC = () => {
  const router = useRouter();
  const { token } = useToken();
  const { containerRef, tableY } = useTableHeight();

  const [isSendModalVisible, setIsSendModalVisible] = useState(false);
  const [isAcceptanceModalVisible, setIsAcceptanceModalVisible] = useState(false);
  const [selectedPresupuesto, setSelectedPresupuesto] = useState<PresupuestoSimpleOut | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [sendForm] = Form.useForm();

  const {
    rows,
    totalRows,
    loading,
    pagination,
    fetchPresupuestos,
    filters,
    handleDelete,
    sendMutation,
    conversionMutation,
    statusUpdateMutation,
    uploadEvidenciaMutation,
  } = usePresupuestoList();

  const {
    empresaId, setEmpresaId, empresasOptions,
    clienteId, setClienteId, clienteOptions, clienteQuery, setClienteQuery, debouncedBuscarClientes,
    estatus, setEstatus,
    rangoFechas, setRangoFechas,
  } = filters;

  // Auto-fetch on filter change
  React.useEffect(() => {
    fetchPresupuestos({ ...pagination, current: 1 });
  }, [empresaId, clienteId, estatus, rangoFechas]);

  // --- Modal Handlers ---
  const showSendModal = (presupuesto: PresupuestoSimpleOut) => {
    setSelectedPresupuesto(presupuesto);
    setIsSendModalVisible(true);
    sendForm.setFieldsValue({ email: '' });
  };

  const handleSendEmail = async () => {
    try {
      const values = await sendForm.validateFields();
      if (selectedPresupuesto) {
        sendMutation.mutate({ id: selectedPresupuesto.id, email: values.email });
        setIsSendModalVisible(false);
        sendForm.resetFields();
      }
    } catch (error) {
      console.error('Validation Failed:', error);
    }
  };

  const showAcceptanceModal = (presupuesto: PresupuestoSimpleOut) => {
    setSelectedPresupuesto(presupuesto);
    setIsAcceptanceModalVisible(true);
  };

  const handleAcceptance = () => {
    if (!selectedPresupuesto) return;

    const file = fileList[0]?.originFileObj;

    if (file) {
      uploadEvidenciaMutation.mutate({ id: selectedPresupuesto.id, file });
    } else {
      statusUpdateMutation.mutate({ id: selectedPresupuesto.id, estado: 'ACEPTADO' });
    }
    setIsAcceptanceModalVisible(false);
    setFileList([]);
  };

  const handleConvertToFactura = (id: string) => {
    Modal.confirm({
      title: '¿Convertir a Factura?',
      content: 'Esta acción creará una nueva factura en estado BORRADOR a partir de este presupuesto. El presupuesto será marcado como FACTURADO.',
      onOk: () => conversionMutation.mutate(id),
      okText: 'Convertir',
      cancelText: 'Cancelar',
    });
  };

  // --- UI Definitions ---
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'BORRADOR': return 'default';
      case 'ENVIADO': return 'processing';
      case 'ACEPTADO': return 'success';
      case 'RECHAZADO': return 'error';
      case 'FACTURADO': return 'gold';
      case 'CADUCADO': return 'warning';
      case 'ARCHIVADO': return 'orange';
      default: return 'default';
    }
  };

  const columns: ColumnsType<PresupuestoSimpleOut> = [
    { title: 'Folio', dataIndex: 'folio', key: 'folio', width: 150, render: (text, record) => <Button type="link" onClick={() => router.push(`/presupuestos/form/${record.id}`)} style={{ padding: 0 }}><strong>{text}</strong></Button> },
    { title: 'Cliente', dataIndex: ['cliente', 'nombre_comercial'], key: 'cliente' },
    { title: 'Fecha Emisión', dataIndex: 'fecha_emision', key: 'fecha_emision', width: 120 },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 140,
      render: (value) => formatCurrency(value),
      align: 'right',
    },
    {
      title: 'Estado',
      dataIndex: 'estado',
      key: 'estado',
      width: 130,
      render: (status) => <Tag color={getStatusColor(status)}>{status}</Tag>
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 80,
      align: 'center',
      render: (_, record) => {
        const items: MenuProps['items'] = [
          {
            key: 'edit',
            label: 'Editar / Ver',
            icon: <EditOutlined />,
            onClick: () => router.push(`/presupuestos/form/${record.id}`),
          },
          {
            key: 'send',
            label: 'Enviar por correo',
            icon: <MailOutlined />,
            onClick: () => showSendModal(record),
          },
          {
            key: 'status',
            label: 'Cambiar Estado',
            icon: <TagOutlined />,
            children: [
              {
                key: 'status-aceptado',
                label: 'Aceptado...',
                onClick: () => showAcceptanceModal(record),
              },
              {
                key: 'status-rechazado',
                label: 'Rechazado',
                onClick: () => statusUpdateMutation.mutate({ id: record.id, estado: 'RECHAZADO' }),
              },
              {
                key: 'status-borrador',
                label: 'Borrador',
                onClick: () => statusUpdateMutation.mutate({ id: record.id, estado: 'BORRADOR' }),
              },
            ],
          },
          {
            type: 'divider',
          },
          {
            key: 'convert',
            label: 'Convertir a Factura',
            icon: <FileDoneOutlined />,
            disabled: record.estado !== 'ACEPTADO',
            onClick: () => handleConvertToFactura(record.id),
          },
          {
            key: 'delete',
            label: <span style={{ color: token.colorError }}>Eliminar</span>,
            icon: <DeleteOutlined style={{ color: token.colorError }} />,
            onClick: (e) => {
              e.domEvent.stopPropagation();
              Modal.confirm({
                title: '¿Eliminar presupuesto?',
                content: 'Esta acción no se puede deshacer.',
                okText: 'Sí, eliminar',
                okType: 'danger',
                cancelText: 'No',
                onOk: () => handleDelete(record.id),
              });
            },
          },
        ];

        return (
          <Dropdown menu={{ items }} trigger={['click']}>
            <Button type="text" icon={<MoreOutlined />} onClick={e => e.preventDefault()} />
          </Dropdown>
        );
      },
    },
  ];

  const sumatoriaMostrada = useMemo(
    () => rows.reduce((acc: number, r: PresupuestoSimpleOut) => acc + (Number(r.total) || 0), 0),
    [rows]
  );

  const uploadProps: UploadProps = {
    onRemove: () => {
      setFileList([]);
    },
    beforeUpload: file => {
      setFileList([file]);
      return false; // Prevent auto-upload
    },
    fileList,
    maxCount: 1,
  };

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">Presupuestos</h1>
        </div>
        <div className="app-page-header__right">
          <Space wrap>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => router.push('/presupuestos/form')}>
              Nuevo Presupuesto
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => fetchPresupuestos()}>
              Recargar
            </Button>
          </Space>
        </div>
      </div>
      <div className="app-content" ref={containerRef}>
        <Card size="small" bordered bodyStyle={{ padding: 12 }} style={{ marginTop: 4 }}>
          <div style={{ position: 'sticky', top: 0, zIndex: 9, padding: '8px', marginBottom: 8, background: token.colorBgContainer, borderRadius: 8, boxShadow: token.boxShadowSecondary }}>
            <Space wrap size={[8, 8]}>
              <Select allowClear placeholder="Empresa" style={{ width: 220 }} options={empresasOptions.map(e => ({ label: e.nombre_comercial, value: e.id }))} value={empresaId} onChange={setEmpresaId} />
              <Select
                allowClear showSearch placeholder="Cliente (escribe ≥ 3 letras)" style={{ width: 280 }}
                filterOption={false}
                onSearch={debouncedBuscarClientes}
                onChange={setClienteId}
                notFoundContent={clienteQuery.length < 3 ? 'Escribe al menos 3 caracteres' : null}
                options={clienteOptions}
                value={clienteId}
              />
              <Select
                allowClear placeholder="Estado" style={{ width: 180 }}
                value={estatus} onChange={setEstatus}
                options={[
                  { value: 'BORRADOR', label: 'BORRADOR' },
                  { value: 'ENVIADO', label: 'ENVIADO' },
                  { value: 'ACEPTADO', label: 'ACEPTADO' },
                  { value: 'RECHAZADO', label: 'RECHAZADO' },
                  { value: 'FACTURADO', label: 'FACTURADO' },
                  { value: 'CADUCADO', label: 'CADUCADO' },
                ]}
              />
              <RangePicker onChange={(dates) => setRangoFechas(dates)} value={rangoFechas} placeholder={['Desde', 'Hasta']} />
            </Space>
          </div>

          <Table<PresupuestoSimpleOut>
            size="small"
            rowKey="id"
            columns={columns}
            dataSource={rows}
            loading={loading}
            pagination={{ ...pagination, total: totalRows, showTotal: (t) => `${t} presupuestos` }}
            onChange={(pag: any) => fetchPresupuestos(pag)}
            scroll={{ x: 980, y: tableY }}
            summary={() => (
              <Table.Summary>
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0} colSpan={3} align="right"><strong>Total mostrado:</strong></Table.Summary.Cell>
                  <Table.Summary.Cell index={3} align="right"><strong>{formatCurrency(sumatoriaMostrada)}</strong></Table.Summary.Cell>
                  <Table.Summary.Cell index={4} colSpan={2} />
                </Table.Summary.Row>
              </Table.Summary>
            )}
            locale={{ emptyText: "No hay presupuestos" }}
          />
        </Card>
      </div>

      {/* Modal para Enviar por Correo */}
      <Modal
        title="Enviar Presupuesto por Correo"
        open={isSendModalVisible}
        onOk={handleSendEmail}
        onCancel={() => setIsSendModalVisible(false)}
        confirmLoading={sendMutation.isPending}
      >
        <Form form={sendForm} layout="vertical">
          <Form.Item name="email" label="Correo del Destinatario" rules={[{ required: true, type: 'email', message: 'Por favor ingresa un correo válido' }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      {/* Modal para Aceptar con Evidencia */}
      <Modal
        title="Aceptar Presupuesto"
        open={isAcceptanceModalVisible}
        onOk={handleAcceptance}
        onCancel={() => setIsAcceptanceModalVisible(false)}
        confirmLoading={uploadEvidenciaMutation.isPending || statusUpdateMutation.isPending}
        okText="Confirmar Aceptación"
      >
        <p>El presupuesto se marcará como ACEPTADO. Opcionalmente, puedes adjuntar un archivo como evidencia (ej. la cotización firmada).</p>
        <br />
        <Upload {...uploadProps}>
          <Button icon={<UploadOutlined />}>Seleccionar Archivo</Button>
        </Upload>
      </Modal>
    </>
  );
};

export default PresupuestosPage;
