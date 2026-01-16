'use client';

import React, { useState } from 'react';
import dayjs from 'dayjs';
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
  Popconfirm,
} from 'antd';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEgresoForm } from '@/hooks/useEgresoForm';
import { SaveOutlined, ArrowLeftOutlined, UploadOutlined, DeleteOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';
import api from '@/lib/axios';
import { deleteEgreso } from '@/services/egresoService';

const EgresoFormPage: React.FC = () => {
  const router = useRouter();
  const { id, form, loading, saving, empresas, categorias, estatus, metodosPago,
    onFinish,
    egreso,
  } = useEgresoForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  // Helper para obtener la URL base (sin /api)
  const getBaseUrl = () => {
    const apiUrl = api.defaults.baseURL || '';
    return apiUrl.endsWith('/api') ? apiUrl.slice(0, -4) : apiUrl;
  };

  const handleDelete = async () => {
    if (!id) return;
    try {
      await deleteEgreso(id);
      message.success('Egreso eliminado correctamente');
      router.push('/egresos');
    } catch (error) {
      message.error('Error al eliminar el egreso');
    }
  };

  React.useEffect(() => {
    if (egreso && egreso.path_documento) {
      setFileList([
        {
          uid: '-1',
          name: egreso.path_documento.split('/').pop() || 'documento',
          status: 'done',
          url: `${getBaseUrl()}/data/${egreso.path_documento}`,
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
    action: `${api.defaults.baseURL}/egresos/upload-documento/`,
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
                <Form.Item label="Archivo XML" name="archivo_xml">
                  <Upload
                    name="file"
                    action={`${api.defaults.baseURL}/egresos/upload-documento/`}
                    maxCount={1}
                    defaultFileList={egreso?.archivo_xml ? [{ uid: '-1', name: egreso.archivo_xml.split('/').pop() || 'xml', status: 'done', url: `${getBaseUrl()}/data/${egreso.archivo_xml}` }] : []}
                    onChange={async (info) => {
                      if (info.file.status === 'done') {
                        message.success(`${info.file.name} subido correctamente`);
                        form.setFieldsValue({ archivo_xml: info.file.response.path_documento });

                        // Auto-llenado
                        if (info.file.originFileObj) {
                          try {
                            const formData = new FormData();
                            formData.append('file', info.file.originFileObj);
                            const { data } = await api.post('/egresos/parse-xml', formData);
                            if (data) {
                              const updates: any = {};
                              if (data.fecha_egreso) updates.fecha_egreso = dayjs(data.fecha_egreso);
                              if (data.monto) updates.monto = data.monto;
                              if (data.moneda) updates.moneda = data.moneda;
                              if (data.proveedor) updates.proveedor = data.proveedor;
                              if (data.metodo_pago) updates.metodo_pago = data.metodo_pago; // Asumiendo que el método venga como clave compatible

                              form.setFieldsValue(updates);
                              message.info('Datos auto-completados desde XML');
                            }
                          } catch (e) {
                            console.error('Error auto-llenado XML', e);
                          }
                        }
                      } else if (info.file.status === 'error') {
                        message.error(`${info.file.name} error al subir.`);
                      } else if (info.file.status === 'removed') {
                        form.setFieldsValue({ archivo_xml: null });
                      }
                    }}
                  >
                    <Button icon={<UploadOutlined />}>Subir XML</Button>
                  </Upload>
                </Form.Item>
              </Col>

              <Col xs={24} md={8}>
                <Form.Item label="Archivo PDF" name="archivo_pdf">
                  <Upload
                    name="file"
                    action={`${api.defaults.baseURL}/egresos/upload-documento/`}
                    maxCount={1}
                    defaultFileList={egreso?.archivo_pdf ? [{ uid: '-2', name: egreso.archivo_pdf.split('/').pop() || 'pdf', status: 'done', url: `${getBaseUrl()}/data/${egreso.archivo_pdf}` }] : []}
                    onChange={(info) => {
                      if (info.file.status === 'done') {
                        message.success(`${info.file.name} subido correctamente`);
                        form.setFieldsValue({ archivo_pdf: info.file.response.path_documento });
                      } else if (info.file.status === 'error') {
                        message.error(`${info.file.name} error al subir.`);
                      } else if (info.file.status === 'removed') {
                        form.setFieldsValue({ archivo_pdf: null });
                      }
                    }}
                  >
                    <Button icon={<UploadOutlined />}>Subir PDF</Button>
                  </Upload>
                </Form.Item>
              </Col>

              <Col xs={24} md={8}>
                <Form.Item label="Otro Documento" name="path_documento">
                  <Upload {...uploadProps}>
                    <Button icon={<UploadOutlined />}>Subir Otro</Button>
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
              {id && (
                <Popconfirm
                  title="Eliminar Egreso"
                  description="¿Estás seguro de eliminar este egreso?"
                  onConfirm={handleDelete}
                  okText="Sí"
                  cancelText="No"
                  okButtonProps={{ danger: true }}
                >
                  <Button icon={<DeleteOutlined />} danger>
                    Eliminar
                  </Button>
                </Popconfirm>
              )}
            </Space>
          </Card>
        </Form>
      </div>
    </>
  );
};

export default EgresoFormPage;