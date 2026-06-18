// src/pages/clientes/form/[[...id]].tsx
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { PageHeader } from '@/components/PageHeader';
import {
  Form, Input, Select, Button, Spin, Card, Space, Typography,
  message, Divider, Modal, Alert, Tag, Upload, Popconfirm,
  Row, Col, InputNumber,
} from 'antd';
import {
  MinusCircleOutlined, PlusOutlined, FilePdfOutlined,
  DeleteOutlined, EnvironmentOutlined,
} from '@ant-design/icons';
import { formatDate } from '@/utils/formatDate';
import { useClienteForm } from '@/hooks/useClienteForm';
import { getRegimenesFiscales } from '@/services/facturaService';
import { ClienteDocumentos } from '@/components/ClienteDocumentos';

const { Text } = Typography;

// ─── helpers ──────────────────────────────────────────────────────────────────
const toUpper = (e: React.ChangeEvent<HTMLInputElement>) =>
  String(e.target.value).toUpperCase();

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
    existingClientCandidate,
    confirmAssignment,
    cancelAssignment,
    lockedEmpresaIds,
  } = useClienteForm(id);

  const [regimenesOptions, setRegimenesOptions] = useState<{ label: string; value: string }[]>([]);
  const lat = Form.useWatch('latitud', form);
  const lon = Form.useWatch('longitud', form);

  useEffect(() => {
    getRegimenesFiscales()
      .then((data: any[]) =>
        setRegimenesOptions(
          (data || []).map((r) => ({ value: r.clave, label: `${r.clave} — ${r.descripcion}` }))
        )
      )
      .catch(() => message.error('Error al cargar los regímenes fiscales'));
  }, []);

  // ─── Importar CSF ────────────────────────────────────────────────────────────
  const handleImportCSF = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      message.loading({ content: 'Analizando Constancia...', key: 'csf' });
      const { default: api } = await import('@/lib/axios');
      const { data } = await api.post('/utils/parse-csf', formData);
      const updates: Record<string, any> = {};
      if (data.rfc)          updates.rfc = data.rfc;
      if (data.razon_social) {
        updates.nombre_razon_social = data.razon_social;
        if (!form.getFieldValue('nombre_comercial')) updates.nombre_comercial = data.razon_social;
      }
      if (data.codigo_postal)   updates.codigo_postal = data.codigo_postal;
      if (data.calle)            updates.calle = data.calle;
      else if (data.direccion)   updates.calle = data.direccion;
      if (data.numero_exterior)  updates.numero_exterior = data.numero_exterior;
      if (data.numero_interior)  updates.numero_interior = data.numero_interior;
      if (data.colonia)          updates.colonia = data.colonia;
      if (data.regimen_fiscal)   updates.regimen_fiscal = data.regimen_fiscal;
      form.setFieldsValue(updates);
      message.success({ content: 'Datos extraídos de la CSF', key: 'csf' });
    } catch {
      message.error({ content: 'Error al analizar la CSF', key: 'csf' });
    }
    return false;
  };

  if (loading && regimenesOptions.length === 0) {
    return <Spin spinning tip="Cargando..."><div style={{ minHeight: 200 }} /></Spin>;
  }

  return (
    <>
      {/* ── Modal: cliente existente ── */}
      <Modal
        title="Cliente existente encontrado"
        open={!!existingClientCandidate}
        onOk={confirmAssignment}
        onCancel={cancelAssignment}
        okText="Asignar a esta empresa"
        cancelText="Cancelar y corregir"
      >
        {existingClientCandidate && (
          <div>
            <Alert
              message="Coincidencia Exacta"
              description="Se encontró un cliente con el mismo RFC y Nombre Comercial en otra(s) empresa(s)."
              type="info" showIcon style={{ marginBottom: 16 }}
            />
            <p><strong>Nombre Comercial:</strong> {existingClientCandidate.nombre_comercial}</p>
            <p><strong>RFC:</strong> {existingClientCandidate.rfc}</p>
            <p><strong>Régimen Fiscal:</strong> {existingClientCandidate.regimen_fiscal}</p>
            <p><strong>CP:</strong> {existingClientCandidate.codigo_postal}</p>
            <Divider />
            <p>¿Deseas <b>asignar este cliente existente</b> a tu empresa en lugar de crear uno nuevo?</p>
            <p style={{ fontSize: '0.85em', color: '#888' }}>
              Esto compartirá la ficha del cliente y mantendrá los datos sincronizados.
            </p>
          </div>
        )}
      </Modal>

      {/* ── Header ── */}
      <PageHeader title={id ? 'Editar Cliente' : 'Nuevo Cliente'} />

      <div className="app-content">
        <Form form={form} layout="vertical" onFinish={onFinish}>

          {/* ── Metadata ── */}
          {metadata && (
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ fontSize: '0.82em' }}>
                Creado: {formatDate(metadata.creado_en)} &nbsp;|&nbsp;
                Actualizado: {formatDate(metadata.actualizado_en)}
              </Text>
            </div>
          )}

          {/* ── Importar CSF ── */}
          <Card
            size="small"
            style={{ marginBottom: 16 }}
            styles={{ body: { padding: '10px 16px' } }}
          >
            <Space align="center" wrap>
              <Text strong>Autocompletar con Constancia de Situación Fiscal:</Text>
              <Upload accept=".pdf" showUploadList={false} beforeUpload={handleImportCSF}>
                <Button
                  icon={<FilePdfOutlined />}
                  type="dashed"
                  style={{ borderColor: '#d32f2f', color: '#d32f2f' }}
                >
                  Subir PDF Constancia (CSF)
                </Button>
              </Upload>
            </Space>
          </Card>

          {/* ══════════════════════════════════════════════════════════════════
              SECCIÓN 1 — Identificación
          ══════════════════════════════════════════════════════════════════ */}
          <Card title="Identificación" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  label="Nombre Comercial"
                  name="nombre_comercial"
                  rules={[{ required: true, message: 'Requerido' }]}
                  getValueFromEvent={toUpper}
                >
                  <Input style={{ textTransform: 'uppercase' }} placeholder="Como lo conoces (ej. FARMACIAS DEL SUR)" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  label="Nombre Fiscal / Razón Social"
                  name="nombre_razon_social"
                  rules={[{ required: true, message: 'Requerido' }]}
                  getValueFromEvent={toUpper}
                >
                  <Input style={{ textTransform: 'uppercase' }} placeholder="Exactamente como aparece en la CSF" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item
                  label="RFC"
                  name="rfc"
                  rules={[{ required: true, message: 'Requerido' }]}
                  getValueFromEvent={toUpper}
                >
                  <Input style={{ textTransform: 'uppercase' }} maxLength={13} placeholder="XAXX010101000" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={16}>
                <Form.Item
                  label="Régimen Fiscal"
                  name="regimen_fiscal"
                  rules={[{ required: true, message: 'Requerido' }]}
                >
                  <Select
                    showSearch
                    placeholder="Selecciona un régimen fiscal"
                    optionFilterProp="label"
                    options={regimenesOptions}
                    loading={regimenesOptions.length === 0}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item label="Empresa(s)" name="empresa_id">
              <Select
                mode="multiple"
                placeholder="Selecciona una o más empresas"
                tagRender={(props) => {
                  const { label, value, closable, onClose } = props;
                  const isLocked = lockedEmpresaIds.includes(value);
                  return (
                    <Tag
                      color={isLocked ? 'default' : undefined}
                      closable={!isLocked}
                      onClose={(e) => {
                        if (isLocked) { e.preventDefault(); return; }
                        onClose(e);
                      }}
                      style={{ marginRight: 3, cursor: isLocked ? 'not-allowed' : 'default' }}
                    >
                      {label}{isLocked && ' (Sin acceso)'}
                    </Tag>
                  );
                }}
              >
                {empresasOptions.map((opt: any) => (
                  <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                ))}
              </Select>
            </Form.Item>
          </Card>

          {/* ══════════════════════════════════════════════════════════════════
              SECCIÓN 2 — Datos de Contacto
          ══════════════════════════════════════════════════════════════════ */}
          <Card title="Datos de Contacto" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  label="Teléfono(s)"
                  name="telefono"
                  extra="Separa varios números con coma"
                >
                  <Input placeholder="+52 55 1234 5678, +52 33 9876 5432" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  label="Correo(s) Electrónico(s)"
                  name="email"
                  extra="Separa varios correos con coma"
                >
                  <Input placeholder="ventas@empresa.com, admin@empresa.com" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* ══════════════════════════════════════════════════════════════════
              SECCIÓN 3 — Dirección Fiscal
          ══════════════════════════════════════════════════════════════════ */}
          <Card title="Dirección Fiscal" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} sm={14}>
                <Form.Item label="Calle" name="calle" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={100} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={5}>
                <Form.Item label="No. Exterior" name="numero_exterior" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={50} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={5}>
                <Form.Item label="No. Interior" name="numero_interior" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={50} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item label="Colonia" name="colonia" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={100} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item label="Ciudad" name="ciudad" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={100} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={4}>
                <Form.Item
                  label="C.P."
                  name="codigo_postal"
                  rules={[{ required: true, message: 'Requerido' }]}
                >
                  <Input maxLength={10} placeholder="00000" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item label="Estado" name="estado" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={100} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* ══════════════════════════════════════════════════════════════════
              SECCIÓN 4 — Dirección de Servicio
          ══════════════════════════════════════════════════════════════════ */}
          <Card title="Dirección de Servicio" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} sm={14}>
                <Form.Item label="Calle" name="serv_calle" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={100} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={5}>
                <Form.Item label="No. Exterior" name="serv_numero_exterior" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={50} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={5}>
                <Form.Item label="No. Interior" name="serv_numero_interior" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={50} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item label="Colonia" name="serv_colonia" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={100} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item label="Ciudad" name="serv_ciudad" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={100} />
                </Form.Item>
              </Col>
              <Col xs={12} sm={4}>
                <Form.Item label="C.P." name="serv_codigo_postal">
                  <Input maxLength={10} placeholder="00000" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item label="Estado" name="serv_estado" getValueFromEvent={toUpper}>
                  <Input style={{ textTransform: 'uppercase' }} maxLength={100} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={16}>
                <Form.Item label="Referencias / Indicaciones" name="serv_referencia">
                  <Input maxLength={255} placeholder="Ej. Portón azul, preguntar por recepción" />
                </Form.Item>
              </Col>
            </Row>

            {/* Geolocalización */}
            <Divider orientation="left" plain style={{ marginTop: 4 }}>
              <EnvironmentOutlined /> Geolocalización
            </Divider>
            <Row gutter={16}>
              <Col xs={12} sm={6}>
                <Form.Item label="Latitud" name="latitud">
                  <Input type="number" placeholder="19.4326" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item label="Longitud" name="longitud">
                  <Input type="number" placeholder="-99.1332" />
                </Form.Item>
              </Col>
              {lat && lon && (
                <Col xs={24} sm={12} style={{ display: 'flex', alignItems: 'center', paddingTop: 8 }}>
                  <a
                    href={`https://www.google.com/maps?q=${lat},${lon}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <EnvironmentOutlined /> Ver en Google Maps
                  </a>
                </Col>
              )}
            </Row>
          </Card>

          {/* ══════════════════════════════════════════════════════════════════
              SECCIÓN 5 — Clasificación y Crédito
          ══════════════════════════════════════════════════════════════════ */}
          <Card title="Clasificación y Crédito" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={12} sm={8}>
                <Form.Item label="Tamaño" name="tamano">
                  <Select placeholder="Selecciona" allowClear>
                    <Select.Option value="CHICO">Chico</Select.Option>
                    <Select.Option value="MEDIANO">Mediano</Select.Option>
                    <Select.Option value="GRANDE">Grande</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={12} sm={8}>
                <Form.Item label="Actividad" name="actividad">
                  <Select placeholder="Selecciona" allowClear>
                    <Select.Option value="RESIDENCIAL">Residencial</Select.Option>
                    <Select.Option value="COMERCIAL">Comercial</Select.Option>
                    <Select.Option value="INDUSTRIAL">Industrial</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={8} sm={6}>
                <Form.Item label="Días de Crédito" name="dias_credito">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={8} sm={6}>
                <Form.Item label="Días de Recepción" name="dias_recepcion">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={8} sm={6}>
                <Form.Item label="Días de Pago" name="dias_pago">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* ══════════════════════════════════════════════════════════════════
              SECCIÓN — Datos para Contrato
          ══════════════════════════════════════════════════════════════════ */}
          <Card title="Datos para Contrato" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item label="Representante Legal" name="representante_legal" getValueFromEvent={toUpper}>
                  <Input placeholder="Nombre del representante legal del cliente" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item
                  label="Escritura Pública"
                  name="escritura_publica"
                  tooltip="No. de escritura constitutiva y fecha (para el contrato)"
                >
                  <Input placeholder="Ej. No. 1,468 de fecha 09/01/2020" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* ══════════════════════════════════════════════════════════════════
              SECCIÓN 6 — Contactos Adicionales
          ══════════════════════════════════════════════════════════════════ */}
          <Card title="Contactos Adicionales" size="small" style={{ marginBottom: 16 }}>
            <Form.List name="contactos">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Card
                      key={key}
                      size="small"
                      style={{ marginBottom: 12, background: 'var(--color-bg-layout, #f5f5f5)' }}
                      extra={
                        <Button
                          type="text"
                          danger
                          size="small"
                          icon={<MinusCircleOutlined />}
                          onClick={() => remove(name)}
                        >
                          Eliminar
                        </Button>
                      }
                    >
                      <Row gutter={16}>
                        <Col xs={24} sm={12}>
                          <Form.Item
                            {...restField}
                            name={[name, 'nombre']}
                            label="Nombre"
                            rules={[{ required: true, message: 'Requerido' }]}
                          >
                            <Input placeholder="Nombre completo" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} sm={12}>
                          <Form.Item {...restField} name={[name, 'puesto']} label="Puesto">
                            <Input placeholder="Ej. Gerente de Compras" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} sm={10}>
                          <Form.Item
                            {...restField}
                            name={[name, 'email']}
                            label="Email"
                            rules={[{ type: 'email', message: 'Email no válido' }]}
                          >
                            <Input placeholder="contacto@empresa.com" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} sm={8}>
                          <Form.Item {...restField} name={[name, 'telefono']} label="Teléfono">
                            <Input placeholder="+52 55 1234 5678" />
                          </Form.Item>
                        </Col>
                        <Col xs={24} sm={6}>
                          <Form.Item
                            {...restField}
                            name={[name, 'tipo']}
                            label="Tipo"
                            initialValue="PRINCIPAL"
                          >
                            <Select>
                              <Select.Option value="PRINCIPAL">Principal</Select.Option>
                              <Select.Option value="ADMINISTRATIVO">Administrativo</Select.Option>
                              <Select.Option value="COBRANZA">Cobranza</Select.Option>
                              <Select.Option value="OPERATIVO">Operativo</Select.Option>
                              <Select.Option value="OTRO">Otro</Select.Option>
                            </Select>
                          </Form.Item>
                        </Col>
                      </Row>
                    </Card>
                  ))}
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                    Agregar Contacto
                  </Button>
                </>
              )}
            </Form.List>
          </Card>

          {/* ══════════════════════════════════════════════════════════════════
              SECCIÓN — Documentos / Contrato (solo en edición)
          ══════════════════════════════════════════════════════════════════ */}
          {id && <ClienteDocumentos clienteId={String(id)} />}

          {/* ── Botones ── */}
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Space>
              {id && (
                <Popconfirm
                  title="¿Eliminar este cliente?"
                  onConfirm={async () => {
                    try {
                      const { clienteService } = await import('@/services/clienteService');
                      await clienteService.deleteCliente(String(id));
                      message.success('Cliente eliminado');
                      router.push('/clientes');
                    } catch {
                      message.error('Error al eliminar cliente');
                    }
                  }}
                  okText="Sí, eliminar"
                  cancelText="Cancelar"
                >
                  <Button danger icon={<DeleteOutlined />}>Eliminar</Button>
                </Popconfirm>
              )}
              <Button onClick={() => router.push('/clientes')}>Cancelar</Button>
              <Button type="primary" htmlType="submit">
                {id ? 'Actualizar' : 'Guardar'}
              </Button>
            </Space>
          </div>

        </Form>
      </div>
    </>
  );
};

export default ClienteFormPage;
