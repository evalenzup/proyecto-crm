'use client';
import React from 'react';
import { useRouter } from 'next/router';
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
import { Breadcrumbs } from '@/components/Breadcrumb';
import { formatDate } from '@/utils/formatDate';
import { useProductoServicioForm } from '@/hooks/useProductoServicioForm'; // Importamos el hook
import { TipoProductoServicio } from '@/services/productoServicioService';

const { Text } = Typography;

const FormularioProductoServicio: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  // Usamos el hook personalizado para toda la lógica del formulario
  const {
    form,
    loading,
    metadata,
    empresasOptions, // Opciones para el select de empresas
    onFinish,
    schema, // Obtenemos el schema del hook
    mapaClavesSat, // Obtenemos el mapa de claves SAT del hook
    loadingSatCatalogs,
  } = useProductoServicioForm(id);

  // Observar el campo 'tipo' para renderizado condicional
  const tipo = Form.useWatch('tipo', form);

  if (loading || loadingSatCatalogs) {
    return (
      <Spin spinning tip="Cargando...">
        <div style={{ minHeight: 200 }} />
      </Spin>
    );
  }

  const renderField = (key: string, prop: any) => {
    const isRequired = schema.required?.includes(key);
    const isInventario = [
      'stock_actual',
      'stock_minimo',
      'unidad_inventario',
      'ubicacion',
      'requiere_lote',
      'cantidad',
    ].includes(key);

    // Ocultar campos de inventario si el tipo no es PRODUCTO
    if (isInventario && tipo !== TipoProductoServicio.PRODUCTO) return null;

    const rules = isRequired || (tipo === TipoProductoServicio.PRODUCTO && isInventario)
      ? [{ required: true, message: `Se requiere ${prop.title || key}` }]
      : [];

    // Campo empresa_id (select con opciones de empresas)
    if (key === 'empresa_id') {
      return (
        <Form.Item key={key} label={prop.title} name={key} rules={rules}>
          <Select placeholder="Selecciona una empresa">
            {empresasOptions.map((opt: any) => (
              <Select.Option key={opt.value} value={opt.value}>
                {opt.label}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
      );
    }

    // Claves SAT (producto y unidad)
    if (key === 'clave_producto' || key === 'clave_unidad') {
      return (
        <Form.Item key={key} label={prop.title} name={key} rules={rules}>
          <Select
            showSearch
            filterOption={(input, option) =>
              (String(option?.value || '').toLowerCase().indexOf(input.toLowerCase()) >= 0) ||
              (String(option?.label || '').toLowerCase().indexOf(input.toLowerCase()) >= 0)
            }
            placeholder="Buscar clave o descripción SAT"
            options={prop['x-options']?.map((opt: any) => ({ value: opt.value, label: opt.label })) || []}
          />
        </Form.Item>
      );
    }

    // Selects con opciones fijas o de schema (tipo, requiere_lote)
    if (prop.enum || prop['x-options']) {
      return (
        <Form.Item key={key} label={prop.title} name={key} rules={rules}>
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

    // InputNumber para campos numéricos
    if (prop.type === 'number' || prop.type === 'integer') {
      return (
        <Form.Item key={key} label={prop.title} name={key} rules={rules}>
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
      );
    }

    // Input de texto por defecto
    return (
      <Form.Item key={key} label={prop.title} name={key} rules={rules}>
        <Input maxLength={prop.maxLength || 255} />
      </Form.Item>
    );
  };

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">{id ? 'Editar Producto/Servicio' : 'Nuevo Producto/Servicio'}</h1>
        </div>
      </div>
      <div className="app-content">
        <Card>
          {metadata && (
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: '0.85em' }}>
                Creado: {formatDate(metadata.creado_en)} &nbsp;|&nbsp; Actualizado: {formatDate(metadata.actualizado_en)}
              </Text>
            </div>
          )}
          <Form form={form} layout="vertical" onFinish={onFinish}>
            {Object.entries(schema.properties || {}).map(([key, prop]) =>
              renderField(key, { ...prop, required: schema.required?.includes(key) })
            )}
            <Form.Item style={{ textAlign: 'right', marginTop: 16 }}>
              <Space>
                <Button onClick={() => router.push('/productos-servicios')}>Cancelar</Button>
                <Button type="primary" htmlType="submit">
                  {id ? 'Actualizar' : 'Guardar'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </>
  );
};

export default FormularioProductoServicio;