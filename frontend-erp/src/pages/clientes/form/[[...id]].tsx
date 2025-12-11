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
  Divider,
  Modal,
  Alert,
  Tag,
} from 'antd';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { formatDate } from '@/utils/formatDate';
import { useClienteForm } from '@/hooks/useClienteForm';
// Importar el servicio necesario para obtener los catálogos
import { getRegimenesFiscales } from '@/services/facturaService';

const { Text } = Typography;

// --- INICIO: Sub-componente para Geolocalización ---
const GeolocationFields = () => {
  const form = Form.useFormInstance(); // Obtiene la instancia del formulario actual
  const lat = Form.useWatch('latitud', form);
  const lon = Form.useWatch('longitud', form);

  return (
    <>
      <Form.Item label="Latitud" name="latitud">
        <Input type="number" placeholder="Ej. 19.4326" />
      </Form.Item>
      <Form.Item label="Longitud" name="longitud">
        <Input type="number" placeholder="Ej. -99.1332" />
      </Form.Item>
      {lat && lon && (
        <Form.Item>
          <a
            href={`https://www.google.com/maps?q=${lat},${lon}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Ver Ubicación en Google Maps
          </a>
        </Form.Item>
      )}
    </>
  );
};
// --- FIN: Sub-componente para Geolocalización ---

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
    existingClientCandidate,
    confirmAssignment,
    cancelAssignment,
    lockedEmpresaIds,
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

          <Select
            mode="multiple"
            placeholder="Selecciona una o más empresas"
            tagRender={(props) => {
              const { label, value, closable, onClose } = props;
              const isLocked = lockedEmpresaIds.includes(value);
              const handleClose = (e: React.MouseEvent<HTMLElement>) => {
                if (isLocked) {
                  e.preventDefault();
                  e.stopPropagation();
                  return;
                }
                onClose(e);
              };
              return (
                <Tag
                  color={isLocked ? "default" : undefined}
                  closable={!isLocked} // Ocultar X si está bloqueado, o mostrarla pero inactiva? AntD closable=false oculta la X.
                  onClose={handleClose}
                  style={{ marginRight: 3, cursor: isLocked ? 'not-allowed' : 'default' }}
                >
                  {label} {isLocked && "(Sin acceso)"}
                </Tag>
              );
            }}
          >
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

    // --- INICIO: Lógica para renderizar campos de Geolocalización ---
    if (key === 'latitud') {
      return <GeolocationFields key="geo-fields" />;
    }
    if (key === 'longitud') {
      return null; // Se renderiza dentro de GeolocationFields
    }
    // --- FIN: Lógica para renderizar campos de Geolocalización ---

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
      {/* Modal para confirmación de cliente existente */}
      <Modal
        title="Cliente existente encontrado"
        open={!!existingClientCandidate}
        onOk={confirmAssignment}
        onCancel={cancelAssignment}
        okText="Asignar a esta empresa"
        cancelText="Cancelar y corregir"
        okButtonProps={{ danger: false }}
      >
        {existingClientCandidate && (
          <div>
            <Alert
              message="Coincidencia Exacta"
              description="Se ha encontrado un cliente con el mismo RFC y Nombre Comercial registrado en otra(s) empresa(s)."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <p><strong>Nombre Comercial:</strong> {existingClientCandidate.nombre_comercial}</p>
            <p><strong>RFC:</strong> {existingClientCandidate.rfc}</p>
            <p><strong>Régimen Fiscal:</strong> {existingClientCandidate.regimen_fiscal}</p>
            <p><strong>CP:</strong> {existingClientCandidate.codigo_postal}</p>
            <Divider />
            <p>¿Deseas <b>asignar este cliente existente</b> a tu empresa en lugar de crear uno nuevo?</p>
            <p style={{ fontSize: '0.85em', color: '#666' }}>Esto compartirá la ficha del cliente, pero mantendrá los datos sincronizados.</p>
          </div>
        )}
      </Modal>

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

            {/* --- INICIO: SECCIÓN DE CONTACTOS DINÁMICOS --- */}
            <Divider>Contactos</Divider>
            <Form.List name="contactos">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Card size="small" key={key} style={{ marginBottom: 16 }}>
                      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <MinusCircleOutlined onClick={() => remove(name)} />
                      </div>
                      <Form.Item
                        {...restField}
                        name={[name, 'nombre']}
                        label="Nombre del Contacto"
                        rules={[{ required: true, message: 'El nombre es requerido' }]}
                      >
                        <Input placeholder="Nombre completo" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'puesto']}
                        label="Puesto"
                      >
                        <Input placeholder="Ej. Gerente de Compras" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'email']}
                        label="Email"
                        rules={[{ type: 'email', message: 'Email no válido' }]}
                      >
                        <Input placeholder="contacto@email.com" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'telefono']}
                        label="Teléfono"
                      >
                        <Input placeholder="+52 123 456 7890" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'tipo']}
                        label="Tipo de Contacto"
                        initialValue="PRINCIPAL"
                      >
                        <Select placeholder="Selecciona un tipo">
                          <Select.Option value="PRINCIPAL">PRINCIPAL</Select.Option>
                          <Select.Option value="ADMINISTRATIVO">ADMINISTRATIVO</Select.Option>
                          <Select.Option value="COBRANZA">COBRANZA</Select.Option>
                          <Select.Option value="OPERATIVO">OPERATIVO</Select.Option>
                          <Select.Option value="OTRO">OTRO</Select.Option>
                        </Select>
                      </Form.Item>
                    </Card>
                  ))}
                  <Form.Item>
                    <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                      Añadir Contacto
                    </Button>
                  </Form.Item>
                </>
              )}
            </Form.List>
            {/* --- FIN: SECCIÓN DE CONTACTOS DINÁMICOS --- */}

            <Form.Item style={{ textAlign: 'right', marginTop: 16 }}>
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