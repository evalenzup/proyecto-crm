import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/axios';
import {
  Form,
  Input,
  Select,
  Upload,
  Button,
  Spin,
  Card,
  message,
  Space,
} from 'antd';
import type { UploadFile } from 'antd';
import { UploadOutlined, DownloadOutlined } from '@ant-design/icons';
import { Layout } from '@/components/Layout';
import { PageContainer } from '@ant-design/pro-layout';
import { Breadcrumbs } from '@/components/Breadcrumb';


interface JSONSchema {
  properties: Record<string, any>;
  required?: string[];
}

const EmpresaFormPage: React.FC = () => {
  const router = useRouter();
  const idArray = router.query.id as string[] | undefined;
  const id = Array.isArray(idArray) ? idArray[0] : idArray;
  const [form] = Form.useForm();
  const [schema, setSchema] = useState<JSONSchema>({ properties: {}, required: [] });
  const [loading, setLoading] = useState(true);
  const [loadingRecord, setLoadingRecord] = useState(!!id);

  useEffect(() => {
    api
      .get<JSONSchema>(`/empresas/schema`)
      .then(({ data }) => setSchema(data))
      .catch(() => message.error('Error al cargar esquema'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!id || !schema.properties) return;
    api
      .get(`/empresas/${id}`)
      .then(({ data }) => {
        const initial = { ...data };
        ['archivo_cer', 'archivo_key'].forEach((key) => {
          if (data[key]) {
            initial[`${key}_file`] = [
              { uid: '-1', name: data[key].split('/').pop(), url: data[key] },
            ];
          }
        });
        form.setFieldsValue(initial);
      })
      .catch(() => {
        message.error('Registro no encontrado');
        router.push('/empresas');
      })
      .finally(() => setLoadingRecord(false));
  }, [id, schema]);

  const onFinish = async (values: any) => {
    const payload = new FormData();
    Object.entries(values).forEach(([k, v]) => {
      if (k.endsWith('_file')) return;
      if (v !== undefined && v !== '') payload.append(k, v as any);
    });
    ['archivo_cer_file', 'archivo_key_file'].forEach((key) => {
      const fileList: UploadFile[] = values[key] || [];
      if (fileList[0]?.originFileObj) {
        payload.append(
          key.replace('_file', ''),
          fileList[0].originFileObj as Blob
        );
      }
    });

    try {
      if (id) {
        await api.put(`/empresas/${id}`, payload, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        message.success('Empresa actualizada');
      } else {
        await api.post(`/empresas/`, payload, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        message.success('Empresa creada');
      }
      router.push('/empresas');
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
    
      if (typeof errorDetail === 'string') {
        if (errorDetail.includes('nombre comercial')) {
          form.setFields([{ name: 'nombre_comercial', errors: [errorDetail] }]);
        } else if (errorDetail.includes('RUC')) {
          form.setFields([{ name: 'ruc', errors: [errorDetail] }]);
        } else if (errorDetail.includes('RFC')) {
          form.setFields([{ name: 'rfc', errors: [errorDetail] }]);
        } else {
          message.error(errorDetail);
        }
      } else if (Array.isArray(errorDetail)) {
        // Caso en que FastAPI retorna varios errores
        const fieldErrors: Record<string, string[]> = {};
    
        errorDetail.forEach((e) => {
          const field = e.loc?.[1];
          if (field) {
            if (!fieldErrors[field]) fieldErrors[field] = [];
            fieldErrors[field].push(e.msg);
          }
        });
    
        Object.entries(fieldErrors).forEach(([field, errors]) => {
          form.setFields([{ name: field, errors }]);
        });
      } else {
        message.error('Error inesperado al guardar');
      }
    }    
  };

  if (loading || loadingRecord) {
    return (
      <Layout>
        <PageContainer>
          <Spin spinning tip="Cargando...">
            <div style={{ minHeight: 200 }} />
          </Spin>
        </PageContainer>
      </Layout>
    );
  }

  return (
    <Layout>
      <PageContainer
        title={id ? 'Editar Empresa' : 'Nueva Empresa'}
        extra={
          <Breadcrumbs
            items={[
              { path: '/empresas', label: 'Empresas' },
              { path: `/empresas/form/${id}`, label: id ? 'Editar' : 'Nueva' },
            ]}
          />
        }
      >
        <Card>
          <Form form={form} layout="vertical" onFinish={onFinish}>
            {Object.entries(schema.properties).map(([key, prop]) => {
              const isReq = schema.required?.includes(key);

              if (prop.format === 'binary') {
                const ext = key === 'archivo_cer' ? 'cer' : 'key';
                const fileUrl = `${process.env.NEXT_PUBLIC_API_URL}/empresas/certificados/${id}.${ext}`;
              
                return (
                  <Form.Item
                    key={key}
                    label={prop.title || key}
                    name={`${key}_file`}
                    valuePropName="fileList"
                    getValueFromEvent={(e) => e.fileList}
                    rules={isReq ? [{ required: true }] : []}
                  >
                    <>
                      <Upload
                        beforeUpload={() => false}
                        maxCount={1}
                        accept={ext === 'cer' ? '.cer' : '.key'}
                      >
                        <Button icon={<UploadOutlined />}>Subir {prop.title}</Button>
                      </Upload>
                      {id && (
                        <a
                          href={fileUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ display: 'inline-block', marginTop: 8 }}
                        >
                          <Button icon={<DownloadOutlined />} type="link">
                            Descargar {prop.title}
                          </Button>
                        </a>
                      )}
                    </>
                  </Form.Item>
                );
              
              
              }

              if (prop.enum) {
                return (
                  <Form.Item
                    key={key}
                    label={prop.title || key}
                    name={key}
                    rules={isReq ? [{ required: true }] : []}
                  >
                    <Select>
                      {prop['x-options']?.map((opt: any) => (
                        <Select.Option key={opt.value} value={opt.value}>
                          {opt.label}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                );
              }

              return (
                <Form.Item
                  key={key}
                  label={prop.title || key}
                  name={key}
                  rules={isReq ? [{ required: true }] : []}
                >
                  <Input
                    maxLength={prop.maxLength}
                    type={prop.format === 'password' ? 'password' : 'text'}
                  />
                </Form.Item>
              );
            })}

            <Form.Item>
              <Space>
                <Button htmlType="button" onClick={() => router.push('/empresas')}>
                  Cancelar
                </Button>
                <Button type="primary" htmlType="submit">
                  {id ? 'Actualizar' : 'Guardar'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      </PageContainer>
    </Layout>
  );
};

export default EmpresaFormPage;
