'use client';
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/axios';
import {
  Form,
  Input,
  Select,
  InputNumber,
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
import { useDebouncedOptions } from '@/hooks/useDebouncedOptions';
import { formatDate } from '@/utils/formatDate';

const { Text } = Typography;

interface JSONSchema {
  properties: Record<string, any>;
  required?: string[];
}

const FormularioProductoServicio: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const [form] = Form.useForm();
  const [schema, setSchema] = useState<JSONSchema>({ properties: {}, required: [] });
  const [loadingSchema, setLoadingSchema] = useState(true);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [tipo, setTipo] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);

  const {
    options: opcionesProducto,
    fetch: buscarClaveProducto,
  } = useDebouncedOptions('/catalogos/busqueda/productos');

  const {
    options: opcionesUnidad,
    fetch: buscarClaveUnidad,
  } = useDebouncedOptions('/catalogos/busqueda/unidades');

  useEffect(() => {
    api
      .get<JSONSchema>('/productos-servicios/schema')
      .then(({ data }) => setSchema(data))
      .catch(() => message.error('Error al cargar esquema'))
      .finally(() => setLoadingSchema(false));
  }, []);

  useEffect(() => {
    if (!id) return;
    setLoadingRecord(true);
    api
      .get(`/productos-servicios/${id}`)
      .then(async ({ data }) => {
        setTipo(data.tipo);
        setMetadata({
          creado_en: data.creado_en,
          actualizado_en: data.actualizado_en,
        });
  
        try {
          const [prod, unidad] = await Promise.all([
            api.get(`/catalogos/descripcion/producto/${data.clave_producto}`),
            api.get(`/catalogos/descripcion/unidad/${data.clave_unidad}`),
          ]);
          form.setFieldsValue({
            ...data,
            clave_producto: {
              value: prod.data.clave,
              label: `${prod.data.clave} - ${prod.data.descripcion}`,
            },
            clave_unidad: {
              value: unidad.data.clave,
              label: `${unidad.data.clave} - ${unidad.data.descripcion}`,
            },
          });
        } catch {
          form.setFieldsValue(data); // fallback
          message.warning('No se pudo precargar descripción de claves SAT');
        }
      })
      .catch(() => {
        message.error('Registro no encontrado');
        router.replace('/productos-servicios');
      })
      .finally(() => setLoadingRecord(false));
  }, [id, form, router]);

  const onFinish = async (values: any) => {
    values.valor_unitario = Number(values.valor_unitario);
    values.cantidad = values.cantidad !== undefined ? Number(values.cantidad) : undefined;  
    try {
      if (id) {
        await api.put(`/productos-servicios/${id}`, values);
        message.success('Actualizado correctamente');
      } else {
        console.log("📦 Valores recibidos:", values);
        await api.post(`/productos-servicios/`, values);
        message.success('Creado correctamente');
      }
      router.push('/productos-servicios');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Error tipo 422: lista de validaciones
        const mensajes = detail.map((e: any) => {
          const campo = e?.loc?.[1];  // ej: "cantidad"
          return `${campo ? campo + ": " : ""}${e.msg}`;
        });
        message.error(mensajes.join("\n"));
      } else if (typeof detail === "string") {
        // Error manual del backend
        message.error(detail);
      } else {
        message.error("Error inesperado al guardar");
      }
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
    { path: '/productos-servicios', label: 'Productos y Servicios' },
    id
      ? { path: `/productos-servicios/form/${id}`, label: 'Editar' }
      : { path: '/productos-servicios/form', label: 'Nuevo' },
  ];

  return (
    <Layout>
      <PageContainer
        title={id ? 'Editar Producto/Servicio' : 'Nuevo Producto/Servicio'}
        extra={<Breadcrumbs items={crumbs} />}
      >
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
              const isRequired = schema.required?.includes(key);
              const isInventario = [
                'stock_actual',
                'stock_minimo',
                'unidad_inventario',
                'ubicacion',
                'requiere_lote',
                'cantidad',
              ].includes(key);

              if (isInventario && tipo !== 'PRODUCTO') return null;

              const rules =
                isRequired || (tipo === 'PRODUCTO' && isInventario)
                  ? [{ required: true, message: `Se requiere ${prop.title || key}` }]
                  : [];

              if (key === 'clave_producto') {
                return (
                  <Form.Item key={key} label={prop.title} name={key} rules={rules}>
                    <Select
                      showSearch
                      onSearch={buscarClaveProducto}
                      options={opcionesProducto}
                      filterOption={false}
                      placeholder="Buscar clave o descripción SAT"
                    />
                  </Form.Item>
                );
              }

              if (key === 'clave_unidad') {
                return (
                  <Form.Item key={key} label={prop.title} name={key} rules={rules}>
                    <Select
                      showSearch
                      onSearch={buscarClaveUnidad}
                      options={opcionesUnidad}
                      filterOption={false}
                      placeholder="Buscar clave o descripción SAT"
                    />
                  </Form.Item>
                );
              }

              if (prop.enum || prop['x-options']) {
                return (
                  <Form.Item key={key} label={prop.title} name={key} rules={rules}>
                    <Select onChange={key === 'tipo' ? setTipo : undefined}>
                      {prop['x-options']?.map((opt: any) => (
                        <Select.Option key={opt.value} value={opt.value}>
                          {opt.label}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                );
              }

              if (prop.type === 'number' || prop.type === 'integer') {
                return (
                  <Form.Item key={key} label={prop.title} name={key} rules={rules}>
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                );
              }

              if (prop.type === 'boolean') {
                return (
                  <Form.Item key={key} label={prop.title} name={key} valuePropName="checked">
                    <Select>
                      <Select.Option value={true}>Sí</Select.Option>
                      <Select.Option value={false}>No</Select.Option>
                    </Select>
                  </Form.Item>
                );
              }

              return (
                <Form.Item key={key} label={prop.title} name={key} rules={rules}>
                  <Input maxLength={prop.maxLength || 255} />
                </Form.Item>
              );
            })}
            <Form.Item>
              <Space>
                <Button onClick={() => router.push('/productos-servicios')}>Cancelar</Button>
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

export default FormularioProductoServicio;