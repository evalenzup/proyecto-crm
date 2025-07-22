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
  Typography,
} from 'antd';
import type { UploadFile } from 'antd';
import { UploadOutlined, DownloadOutlined } from '@ant-design/icons';
import { Layout } from '@/components/Layout';
import { PageContainer } from '@ant-design/pro-layout';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { formatDate } from '@/utils/formatDate';

const { Text } = Typography;

interface JSONSchema {
  properties: Record<string, any>;
  required?: string[];
}

// Formatear fechas asumiendo UTC y mostrando en America/Tijuana
/*
const formatDate = (iso: string) => {
  const utc = iso.endsWith('Z') ? iso : `${iso}Z`;
  return new Date(utc).toLocaleString('es-MX', {
    timeZone: 'America/Tijuana',
    dateStyle: 'short',
    timeStyle: 'medium',
  });
};
*/
const EmpresaFormPage: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const [form] = Form.useForm();
  const [schema, setSchema] = useState<JSONSchema>({ properties: {}, required: [] });
  const [loadingSchema, setLoadingSchema] = useState(true);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);

  // Campos que deben forzar mayúsculas
  const uppercaseFields = ['nombre', 'nombre_comercial', 'rfc', 'ruc', 'direccion'];

  // Cargar esquema
  useEffect(() => {
    api
      .get<JSONSchema>('/empresas/schema')
      .then(({ data }) => setSchema(data))
      .catch(() => message.error('Error al cargar esquema'))
      .finally(() => setLoadingSchema(false));
  }, []);

  // Cargar datos para editar
  useEffect(() => {
    if (!id) return;
    setLoadingRecord(true);
    api
      .get(`/empresas/${id}`)
      .then(({ data }) => {
        const initial: any = { ...data };
        ['archivo_cer', 'archivo_key'].forEach((key) => {
          if (data[key]) {
            initial[`${key}_file`] = [
              { uid: '-1', name: data[key].split('/').pop(), url: data[key] },
            ];
          }
        });
        form.setFieldsValue(initial);
        setMetadata({
          creado_en: data.creado_en,
          actualizado_en: data.actualizado_en,
        });
      })
      .catch(() => {
        message.error('Registro no encontrado');
        router.replace('/empresas');
      })
      .finally(() => setLoadingRecord(false));
  }, [id, schema, form, router]);

  // Envío del formulario
  const onFinish = async (values: any) => {
    const payload = new FormData();
    Object.entries(values).forEach(([k, v]) => {
      if (k.endsWith('_file')) return;
      if (v !== undefined && v !== '') payload.append(k, v as any);
    });
    ['archivo_cer_file', 'archivo_key_file'].forEach((key) => {
      const files: UploadFile[] = values[key] || [];
      if (files[0]?.originFileObj) {
        payload.append(key.replace('_file', ''), files[0].originFileObj as Blob);
      }
    });

    try {
      if (id) {
        await api.put(`/empresas/${id}`, payload, { headers: { 'Content-Type': 'multipart/form-data' } });
        message.success('Empresa actualizada');
      } else {
        await api.post(`/empresas/`, payload, { headers: { 'Content-Type': 'multipart/form-data' } });
        message.success('Empresa creada');
      }
      router.push('/empresas');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      message.error(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((e: any) => e.msg).join(', ')
          : 'Error inesperado'
      );
    }
  };

  if (loadingSchema || loadingRecord) {
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

  const crumbs = [
    { path: '/empresas', label: 'Empresas' },
    id ? { path: `/empresas/form/${id}`, label: 'Editar' } : { path: '/empresas/form', label: 'Nueva' },
  ];

  return (
    <Layout>
      <PageContainer title={id ? 'Editar Empresa' : 'Nueva Empresa'} extra={<Breadcrumbs items={crumbs} />}>  
        <Card>
          {metadata && (
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: '0.85em' }}>
                Creado: {formatDate(metadata.creado_en)} &nbsp;|&nbsp; Actualizado: {formatDate(metadata.actualizado_en)}
              </Text>
            </div>
          )}
          <Form form={form} layout="vertical" onFinish={onFinish}>
            {Object.entries(schema.properties).map(([key, prop]) => {
              const required = schema.required?.includes(key);
              // Archivos (.cer/.key)
              if (prop.format === 'binary') {
                const ext = key === 'archivo_cer' ? 'cer' : 'key';
                return (
                  <Form.Item
                    key={key}
                    label={prop.title}
                    name={`${key}_file`}
                    valuePropName="fileList"
                    getValueFromEvent={(e) => e.fileList}
                    rules={required ? [{ required: true, message: `Se requiere ${prop.title}` }] : []}
                  >
                    <>
                      <Upload beforeUpload={() => false} maxCount={1} accept={ext === 'cer' ? '.cer' : '.key'}>
                        <Button icon={<UploadOutlined />}>Subir {prop.title}</Button>
                      </Upload>
                      {id && (
                        <a href={`${process.env.NEXT_PUBLIC_API_URL}/empresas/certificados/${id}.${ext}`} target="_blank" rel="noopener noreferrer" style={{ display: 'block', marginTop: 8 }}>
                          <Button icon={<DownloadOutlined />} type="link">Descargar {prop.title}</Button>
                        </a>
                      )}
                    </>
                  </Form.Item>
                );
              }
              // Select
              if (prop.enum) {
                return (
                  <Form.Item key={key} label={prop.title} name={key} rules={required ? [{ required: true, message: `Se requiere ${prop.title}` }] : []}>
                    <Select>
                      {prop['x-options']?.map((opt: any) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}
                    </Select>
                  </Form.Item>
                );
              }
              // Input de texto/password
              return (
                <Form.Item
                  key={key}
                  label={prop.title}
                  name={key}
                  rules={required ? [{ required: true, message: `Se requiere ${prop.title}` }] : []}
                  getValueFromEvent={(e) => {
                    const val = e.target.value;
                    return uppercaseFields.includes(key) ? val.toUpperCase() : val;
                  }}
                >
                  <Input
                    maxLength={prop.maxLength}
                    type={prop.format === 'password' ? 'password' : 'text'}
                    style={uppercaseFields.includes(key) ? { textTransform: 'uppercase' } : undefined}
                  />
                </Form.Item>
              );
            })}
            <Form.Item>
              <Space>
                <Button onClick={() => router.push('/empresas')}>Cancelar</Button>
                <Button type="primary" htmlType="submit">{id ? 'Actualizar' : 'Guardar'}</Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      </PageContainer>
    </Layout>
  );
};

export default EmpresaFormPage;
