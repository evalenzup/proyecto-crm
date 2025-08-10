// src/pages/clientes/form/[[...id]].tsx

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/axios';
import {
  Form,
  Input,
  Select,
  Button,
  Spin,
  Card,
  message,
  Space,
  Typography,
} from 'antd';
import { Layout } from '@/components/Layout';
import { PageContainer } from '@ant-design/pro-layout';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { formatDate } from '@/utils/formatDate';

const { Text } = Typography;

interface JSONSchema {
  properties: Record<string, any>;
  required?: string[];
}

const ClienteFormPage: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const [form] = Form.useForm();
  const [schema, setSchema] = useState<JSONSchema>({ properties: {}, required: [] });
  const [loadingSchema, setLoadingSchema] = useState(true);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);

  // Campos que deben forzar mayúsculas
  const uppercaseFields = [
    'nombre_comercial',
    'nombre_razon_social',
    'rfc',
    'calle',
    'colonia',
  ];

  // 1) Carga el JSON-Schema
  useEffect(() => {
    api
      .get<JSONSchema>('/clientes/schema')
      .then(({ data }) => setSchema(data))
      .catch(() => message.error('Error al cargar esquema'))
      .finally(() => setLoadingSchema(false));
  }, []);

  // 2) Si hay `id`, carga los datos para editar
  useEffect(() => {
    if (!id) return;
    setLoadingRecord(true);

    api
      .get(`/clientes/${id}`)
      .then(({ data }) => {
        // Prepara el formulario
        const initial: any = { ...data };
        // empresa_id → array de UUIDs
        if (Array.isArray(data.empresas)) {
          initial.empresa_id = data.empresas.map((e: any) => e.id);
        }
        form.setFieldsValue(initial);
        setMetadata({
          creado_en: data.creado_en,
          actualizado_en: data.actualizado_en,
        });
      })
      .catch(() => {
        message.error('Registro no encontrado');
        router.replace('/clientes');
      })
      .finally(() => setLoadingRecord(false));
  }, [id, form, router]);

  // 3) Submit: POST si no hay id, PUT si hay id
  const onFinish = async (values: any) => {
    // Clona y limpia valores vacíos
    const payload: any = { ...values };
    Object.keys(payload).forEach((k) => {
      if (payload[k] === undefined || payload[k] === '') {
        delete payload[k];
      }
    });
    try {
      if (id) {
        await api.put(`/clientes/${id}`, payload);
        message.success('Cliente actualizado');
      } else {
        await api.post('/clientes/', payload);
        message.success('Cliente creado');
      }
      router.push('/clientes');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      message.error(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((e: any) => `${e.loc[1]}: ${e.msg}`).join(', ')
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
    { path: '/clientes', label: 'Clientes' },
    id
      ? { path: `/clientes/form/${id}`, label: 'Editar' }
      : { path: '/clientes/form', label: 'Nuevo' },
  ];

  return (
    <Layout>
      <PageContainer
        title={id ? 'Editar Cliente' : 'Nuevo Cliente'}
        extra={<Breadcrumbs items={crumbs} />}
      >
        <Card>
          {metadata && (
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: '0.85em' }}>
                Creado: {formatDate(metadata.creado_en)} &nbsp;|&nbsp; Actualizado:{' '}
                {formatDate(metadata.actualizado_en)}
              </Text>
            </div>
          )}

          <Form form={form} layout="vertical" onFinish={onFinish}>
            {Object.entries(schema.properties).map(([key, prop]) => {
              const required = schema.required?.includes(key);

              // --- MULTI-SELECT DE EMPRESAS ---
              if (key === 'empresa_id') {
                return (
                  <Form.Item
                    key={key}
                    label={prop.title}
                    name={key}
                    rules={
                      required
                        ? [{ required: true, message: `Se requiere ${prop.title}` }]
                        : []
                    }
                  >
                    <Select mode="multiple" placeholder="Selecciona una o más empresas">
                      {prop['x-options']?.map((opt: any) => (
                        <Select.Option key={opt.value} value={opt.value}>
                          {opt.label}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                );
              }

              // --- EMAIL / TELÉFONO COMO TEXTO LIBRE ---
              if (key === 'email' || key === 'telefono') {
                const placeholder =
                  key === 'email'
                    ? 'correo1@dominio.com, correo2@dominio.com'
                    : '+521234567890, +529876543210';
                return (
                  <Form.Item
                    key={key}
                    label={prop.title}
                    name={key}
                    rules={
                      required
                        ? [{ required: true, message: `Se requiere ${prop.title}` }]
                        : []
                    }
                  >
                    <Input placeholder={placeholder} />
                  </Form.Item>
                );
              }

              // --- SELECT / ENUMERADOS ---
              if (prop.enum || prop['x-options']) {
                return (
                  <Form.Item
                    key={key}
                    label={prop.title}
                    name={key}
                    rules={
                      required
                        ? [{ required: true, message: `Se requiere ${prop.title}` }]
                        : []
                    }
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

              // --- INPUT DE TEXTO / PASSWORD ---
              return (
                <Form.Item
                  key={key}
                  label={prop.title}
                  name={key}
                  rules={
                    required
                      ? [{ required: true, message: `Se requiere ${prop.title}` }]
                      : []
                  }
                  getValueFromEvent={(e) => {
                    const val = e.target.value;
                    return uppercaseFields.includes(key) ? val.toUpperCase() : val;
                  }}
                >
                  <Input
                    maxLength={prop.maxLength}
                    type={prop.format === 'password' ? 'password' : 'text'}
                    style={
                      uppercaseFields.includes(key)
                        ? { textTransform: 'uppercase' }
                        : undefined
                    }
                  />
                </Form.Item>
              );
            })}

            <Form.Item>
              <Space>
                <Button onClick={() => router.push('/clientes')}>Cancelar</Button>
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

export default ClienteFormPage;