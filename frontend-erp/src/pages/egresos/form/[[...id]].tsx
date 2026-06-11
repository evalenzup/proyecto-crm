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

  /** Descarga un archivo de egreso via endpoint autenticado y lo abre en nueva pestaña. */
  const onPreviewArchivoEgreso = async (file: UploadFile) => {
    const ruta = file.url; // guardamos la ruta relativa en `url` solo como identificador
    if (!ruta) return;
    try {
      const { data } = await api.get(`/egresos/archivo?ruta=${encodeURIComponent(ruta)}`, {
        responseType: 'blob',
      });
      const blobUrl = URL.createObjectURL(data);
      window.open(blobUrl, '_blank');
      setTimeout(() => URL.revokeObjectURL(blobUrl), 30_000);
    } catch {
      message.error('No se pudo abrir el archivo');
    }
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
          url: egreso.path_documento, // ruta relativa — usada por onPreviewArchivoEgreso
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

  // customRequest usa api (axios) que inyecta el Authorization header automáticamente.
  // Ant Design's `action` usa XHR nativo que no tiene acceso al access token en memoria.
  const makeCustomRequest = (
    onSuccess: (path: string) => void,
    onError?: () => void,
  ) => async (options: any) => {
    const { file, onSuccess: done, onError: fail } = options;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const { data } = await api.post('/egresos/upload-documento/', formData);
      onSuccess(data.path_documento);
      done(data);
    } catch (e) {
      fail?.(e);
      onError?.();
    }
  };

  const uploadProps: UploadProps = {
    name: 'file',
    fileList,
    maxCount: 1,
    customRequest: makeCustomRequest(
      (path) => form.setFieldsValue({ path_documento: path }),
      () => message.error('Error al subir el documento'),
    ),
    onChange(info) {
      setFileList(info.fileList);
      if (info.file.status === 'done') {
        message.success(`${info.file.name} subido correctamente`);
      } else if (info.file.status === 'error') {
        message.error(`${info.file.name} error al subir`);
      }
    },
    onRemove: () => {
      form.setFieldsValue({ path_documento: null });
      return true;
    },
    onPreview: onPreviewArchivoEgreso,
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
                    maxCount={1}
                    accept=".xml"
                    defaultFileList={egreso?.archivo_xml ? [{ uid: '-1', name: egreso.archivo_xml.split('/').pop() || 'xml', status: 'done', url: egreso.archivo_xml }] : []}
                    onPreview={onPreviewArchivoEgreso}
                    customRequest={makeCustomRequest(
                      (path) => form.setFieldsValue({ archivo_xml: path }),
                    )}
                    onChange={(info) => {
                      if (info.file.status === 'done') {
                        message.success(`${info.file.name} subido correctamente`);
                        // Auto-llenado de campos desde el contenido del XML
                        const orig = info.file.originFileObj;
                        if (orig) {
                          const fd = new FormData();
                          fd.append('file', orig);
                          api.post('/egresos/parse-xml', fd)
                            .then(({ data }) => {
                              if (!data) return;
                              const updates: any = {};
                              if (data.fecha_egreso) updates.fecha_egreso = dayjs(data.fecha_egreso);
                              if (data.monto)        updates.monto = data.monto;
                              if (data.moneda)       updates.moneda = data.moneda;
                              if (data.proveedor)    updates.proveedor = data.proveedor;
                              if (data.metodo_pago)  updates.metodo_pago = data.metodo_pago;
                              form.setFieldsValue(updates);
                              message.info('Datos auto-completados desde XML');
                            })
                            .catch(() => { /* parse fallido — no bloquea */ });
                        }
                      } else if (info.file.status === 'error') {
                        message.error(`${info.file.name} error al subir`);
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
                    maxCount={1}
                    accept=".pdf"
                    defaultFileList={egreso?.archivo_pdf ? [{ uid: '-2', name: egreso.archivo_pdf.split('/').pop() || 'pdf', status: 'done', url: egreso.archivo_pdf }] : []}
                    onPreview={onPreviewArchivoEgreso}
                    customRequest={makeCustomRequest(
                      (path) => form.setFieldsValue({ archivo_pdf: path }),
                    )}
                    onChange={(info) => {
                      if (info.file.status === 'done') {
                        message.success(`${info.file.name} subido correctamente`);
                      } else if (info.file.status === 'error') {
                        message.error(`${info.file.name} error al subir`);
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