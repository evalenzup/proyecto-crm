// src/pages/egresos/form/[[...id]].tsx
'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/router';
import {
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Spin,
  Card,
  DatePicker,
  Row,
  Col,
  Space,
  Upload,
  message,
} from 'antd';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEgresoForm } from '@/hooks/useEgresoForm';
import { SaveOutlined, ArrowLeftOutlined, UploadOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';

const EgresoFormPage: React.FC = () => {
  const router = useRouter();
  const { id, form, loading, saving, empresas, categorias, estatus, metodosPago, onFinish, egreso } = useEgresoForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  React.useEffect(() => {
    if (egreso && egreso.path_documento) {
      setFileList([
        {
          uid: '-1',
          name: egreso.path_documento.split('/').pop() || 'documento',
          status: 'done',
          url: `http://localhost:8000/${egreso.path_documento}`,
        },
      ]);
    }
    if (egreso) {
      form.setFieldsValue({
        metodo_pago: egreso.metodo_pago,
      });
    }
  }, [egreso]);

  const categoriaOptions = categorias.map(c => ({ label: c, value: c }));
  const estatusOptions = estatus.map(e => ({ label: e, value: e }));

  const uploadProps: UploadProps = {
    name: 'file',
    action: 'http://localhost:8000/api/egresos/upload-documento/',
    fileList,
    maxCount: 1,
    onChange(info) {
      setFileList(info.fileList);
      if (info.file.status === 'done') {
        message.success(`${info.file.name} file uploaded successfully`);
        form.setFieldsValue({ path_documento: info.file.response.path_documento });
      } else if (info.file.status === 'error') {
        message.error(`${info.file.name} file upload failed.`);
      }
    },
    onRemove: (file) => {
      form.setFieldsValue({ path_documento: null });
      return true;
    },
  };

  if (loading) return <Spin style={{ margin: 48 }} />;

  return (
    <>
      <div className="app-page-header">
        <Breadcrumbs />
        <h1 className="app-title">{id ? 'Editar Egreso' : 'Nuevo Egreso'}</h1>
      </div>

      <div className="app-content">
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Card>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label="Empresa" name="empresa_id" rules={[{ required: true }]}>
                  <Select options={empresas} placeholder="Seleccione una empresa" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label="Fecha" name="fecha_egreso" rules={[{ required: true }]}>
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col xs={24}>
                <Form.Item label="Descripción" name="descripcion" rules={[{ required: true }]}>
                  <Input.TextArea rows={3} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Monto" name="monto" rules={[{ required: true }]}>
                  <InputNumber min={0} style={{ width: '100%' }} addonBefore="$" />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Moneda" name="moneda" rules={[{ required: true }]}>
                  <Select options={[{ label: 'MXN', value: 'MXN' }, { label: 'USD', value: 'USD' }]} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Categoría" name="categoria" rules={[{ required: true }]}>
                  <Select options={categoriaOptions} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Estatus" name="estatus" rules={[{ required: true }]}>
                  <Select options={estatusOptions} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Proveedor" name="proveedor">
                  <Input />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Método de Pago" name="metodo_pago" rules={[{ required: true }]}>
                  <Select options={metodosPago} placeholder="Seleccione un método de pago" />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label="Documento" name="path_documento">
                  <Upload {...uploadProps}>
                    <Button icon={<UploadOutlined />}>Click to Upload</Button>
                  </Upload>
                </Form.Item>
              </Col>
            </Row>
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/egresos')}>
                Cancelar
              </Button>
              <Button icon={<SaveOutlined />} type="primary" htmlType="submit" loading={saving}>
                {id ? 'Actualizar' : 'Guardar'}
              </Button>
            </Space>
          </Card>
        </Form>
      </div>
    </>
  );
};

export default EgresoFormPage;