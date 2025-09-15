// src/pages/clientes/form/[[...id]].tsx

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import {
  Form,
  Input,
  Select,
  Button,
  Spin,
  Card,
  Space,
  Typography,
  message, // Importar message para notificaciones
} from 'antd';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { formatDate } from '@/utils/formatDate';
import { useClienteForm } from '@/hooks/useClienteForm';
// Importar el servicio necesario para obtener los catálogos
import { getRegimenesFiscales } from '@/services/facturaService';

const { Text } = Typography;

// Campos que deben forzar mayúsculas
const UPPERCASE_FIELDS = [
  'nombre_comercial',
  'nombre_razon_social',
  'rfc',
  'calle',
  'colonia',
];

const ClienteFormPage: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const {
    form,
    loading,
    metadata,
    empresasOptions,
    onFinish,
    schema,
  } = useClienteForm(id);

  // --- NUEVO ESTADO PARA GUARDAR LAS OPCIONES DEL CATÁLOGO ---
  const [regimenesOptions, setRegimenesOptions] = useState<{ label: string; value: string }[]>([]);

  // --- NUEVO EFECTO PARA CARGAR EL CATÁLOGO AL INICIAR ---
  useEffect(() => {
    const fetchRegimenes = async () => {
      try {
        const data = await getRegimenesFiscales();
        const options = (data || []).map((r: any) => ({
          value: r.clave,
          label: `${r.clave} — ${r.descripcion}`,
        }));
        setRegimenesOptions(options);
      } catch (error) {
        message.error('Error al cargar los regímenes fiscales');
      }
    };
    fetchRegimenes();
  }, []);


  // Opciones estáticas para selects
  const tamanoOptions = [
    { value: 'CHICO', label: 'CHICO' },
    { value: 'MEDIANO', label: 'MEDIANO' },
    { value: 'GRANDE', label: 'GRANDE' },
  ];
  const actividadOptions = [
    { value: 'RESIDENCIAL', label: 'RESIDENCIAL' },
    { value: 'COMERCIAL', label: 'COMERCIAL' },
    { value: 'INDUSTRIAL', label: 'INDUSTRIAL' },
  ];

  if (loading && regimenesOptions.length === 0) { // Ajustar condición de carga
    return (
      <Spin spinning tip="Cargando...">
        <div style={{ minHeight: 200 }} />
      </Spin>
    );
  }

  // Función para renderizar campos del formulario
  const renderField = (key: string, prop: any) => {
    const required = schema.required?.includes(key);

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
            {empresasOptions.map((opt: any) => (
              <Select.Option key={opt.value} value={opt.value}>
                {opt.label}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
      );
    }

    // --- REGÍMEN FISCAL (CORREGIDO) ---
    if (key === 'regimen_fiscal') {
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
          <Select
            showSearch
            placeholder="Selecciona un régimen fiscal"
            optionFilterProp="label" // Buscar por el texto de la etiqueta
            options={regimenesOptions} // Usar las opciones cargadas en el estado
            loading={regimenesOptions.length === 0} // Mostrar ícono de carga
          />
        </Form.Item>
      );
    }

    if (key === 'tamano') {
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
          <Select
            placeholder="Selecciona tamaño"
            options={tamanoOptions}
          />
        </Form.Item>
      );
    }

    if (key === 'actividad') {
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
          <Select
            placeholder="Selecciona actividad"
            options={actividadOptions}
          />
        </Form.Item>
      );
    }

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
          return UPPERCASE_FIELDS.includes(key) && val != null ? String(val).toUpperCase() : val;
        }}
      >
        <Input
          maxLength={prop.maxLength}
          type={prop.format === 'password' ? 'password' : 'text'}
          style={
            UPPERCASE_FIELDS.includes(key)
              ? { textTransform: 'uppercase' }
              : undefined
          }
        />
      </Form.Item>
    );
  };

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">{id ? 'Editar Cliente' : 'Nuevo Cliente'}</h1>
        </div>
      </div>
      <div className="app-content">
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
            {Object.entries(schema.properties || {}).map(([key, prop]) =>
              renderField(key, { ...prop, required: schema.required?.includes(key) })
            )}

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
      </div>
    </>
  );
};

export default ClienteFormPage;