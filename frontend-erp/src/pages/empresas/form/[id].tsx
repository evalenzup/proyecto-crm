// src/pages/empresas/form/[[...id]].tsx
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
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
import { UploadOutlined } from '@ant-design/icons';
import { Layout } from '@/components/Layout';
import { PageContainer } from '@ant-design/pro-layout';
import { EmpresaBreadcrumb } from '@/components/EmpresaBreadcrumb';

// Interfaz para el esquema JSON que define el formulario dinámico
interface JSONSchema {
  properties: Record<string, any>;
  required?: string[];
}

const EmpresaFormPage: React.FC = () => {
  const router = useRouter();

  // Obtenemos el parámetro dinámico de la URL (puede ser undefined, string o array)
  const idArray = router.query.id as string[] | undefined;
  const id = Array.isArray(idArray) ? idArray[0] : idArray;

  // Instancia del formulario de Ant Design
  const [form] = Form.useForm();

  // Estado para almacenar el JSON-Schema y los indicadores de carga
  const [schema, setSchema] = useState<JSONSchema>({ properties: {}, required: [] });
  const [loading, setLoading] = useState(true);              // carga del esquema
  const [loadingRecord, setLoadingRecord] = useState(!!id);  // carga del registro si es edición

  // Cargar el JSON-Schema al montar el componente
  useEffect(() => {
    axios
      .get<JSONSchema>(`${process.env.NEXT_PUBLIC_API_URL}/empresas/schema`)
      .then(({ data }) => setSchema(data))
      .catch(() => message.error('Error al cargar esquema'))
      .finally(() => setLoading(false));
  }, []);

  // Si se está editando una empresa (hay `id`), se cargan los datos del registro
  useEffect(() => {
    if (!id || !schema.properties) return;

    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}`)
      .then(({ data }) => {
        const initial = { ...data };

        // Precarga visual de archivos existentes para los campos cer/key
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
  }, [id, schema, form, router]);

  // Envía los datos del formulario como FormData para manejar archivos
  const onFinish = async (values: any) => {
    const payload = new FormData();

    // Agrega los campos normales (excluyendo los _file)
    Object.entries(values).forEach(([k, v]) => {
      if (k.endsWith('_file')) return;
      if (v !== undefined && v !== '') payload.append(k, v as any);
    });

    // Agrega los archivos .cer y .key reales (si fueron cargados)
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
        // Si hay ID, se actualiza
        await axios.put(
          `${process.env.NEXT_PUBLIC_API_URL}/empresas/${id}`,
          payload,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        );
        message.success('Empresa actualizada');
      } else {
        // Si no hay ID, se crea nuevo registro
        await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/empresas/`,
          payload,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        );
        message.success('Empresa creada');
      }

      // Redirección al listado
      router.push('/empresas');
    } catch {
      message.error('Error al guardar');
    }
  };

  // Mientras se carga el esquema o los datos, se muestra un spinner
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

  // Render del formulario dinámico
  return (
    <Layout>
      <PageContainer title={id ? 'Editar Empresa' : 'Nueva Empresa'} extra={<EmpresaBreadcrumb id={id} />}>
        <Card>
          <Form form={form} layout="vertical" onFinish={onFinish}>
            {/* Generación dinámica de campos a partir del JSON-Schema */}
            {Object.entries(schema.properties).map(([key, prop]) => {
              const isReq = schema.required?.includes(key);

              // Campo tipo archivo (subida de .cer o .key)
              if (prop.format === 'binary') {
                return (
                  <Form.Item
                    key={key}
                    label={prop.title || key}
                    name={`${key}_file`}
                    valuePropName="fileList"
                    getValueFromEvent={(e) => e.fileList}
                    rules={isReq ? [{ required: true }] : []}
                  >
                    <Upload
                      beforeUpload={() => false}
                      maxCount={1}
                      accept={key === 'archivo_cer' ? '.cer' : '.key'}
                    >
                      <Button icon={<UploadOutlined />}>Subir {prop.title}</Button>
                    </Upload>
                  </Form.Item>
                );
              }

              // Campo tipo select (enums con opciones)
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

              // Campo texto o password (input genérico)
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

            {/* Botones de acción */}
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
