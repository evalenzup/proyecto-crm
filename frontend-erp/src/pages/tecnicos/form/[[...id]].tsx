'use client';
// pages/tecnicos/form/[[...id]].tsx

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { PageHeader } from '@/components/PageHeader';
import {
  Form,
  Image,
  Input,
  Select,
  InputNumber,
  Switch,
  Button,
  Spin,
  Card,
  message,
  Space,
  Typography,
  Row,
  Col,
  Divider,
  DatePicker,
  Upload,
  Popconfirm,
  Tabs,
  Modal,
} from 'antd';
import {
  UploadOutlined,
  DeleteOutlined,
  UserOutlined,
  IdcardOutlined,
  FilePdfOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import {
  tecnicoService,
  TecnicoOut,
  TecnicoCreate,
  TecnicoUpdate,
  TipoPersonal,
  Sexo,
  TipoSangre,
  NivelEstudios,
  LicenciaTipo,
} from '@/services/tecnicoService';
import { servicioOperativoService } from '@/services/servicioOperativoService';

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;


const TIPOS_PERSONAL: { value: TipoPersonal; label: string }[] = [
  { value: 'TECNICO', label: 'Técnico' },
  { value: 'ADMINISTRATIVO', label: 'Administrativo' },
  { value: 'OPERATIVO', label: 'Operativo' },
  { value: 'SUPERVISOR', label: 'Supervisor' },
  { value: 'OTRO', label: 'Otro' },
];

const TIPOS_SANGRE: TipoSangre[] = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

const NIVELES_ESTUDIOS: { value: NivelEstudios; label: string }[] = [
  { value: 'PRIMARIA', label: 'Primaria' },
  { value: 'SECUNDARIA', label: 'Secundaria' },
  { value: 'PREPARATORIA', label: 'Preparatoria / Bachillerato' },
  { value: 'TECNICO_MEDIO', label: 'Técnico Medio Superior' },
  { value: 'LICENCIATURA', label: 'Licenciatura' },
  { value: 'INGENIERIA', label: 'Ingeniería' },
  { value: 'POSGRADO', label: 'Posgrado / Maestría / Doctorado' },
  { value: 'OTRO', label: 'Otro' },
];

const PersonalForm: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const { selectedEmpresaId, empresas } = useEmpresaSelector();

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [record, setRecord] = useState<TecnicoOut | null>(null);
  const [uploadingFoto, setUploadingFoto] = useState(false);
  const [fotoBlob, setFotoBlob] = useState<string | null>(null);
  const [generandoCredencial, setGenerandoCredencial] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [especialidadesOptions, setEspecialidadesOptions] = useState<{ value: string; label: string }[]>([]);
  const [fetchingEspecialidades, setFetchingEspecialidades] = useState(false);

  const watchedEmpresaId = Form.useWatch('empresa_id', form);

  // ── Carga del registro ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    tecnicoService
      .getTecnico(id)
      .then(async (data) => {
        setRecord(data);
        if (data.foto) {
          try {
            const blobUrl = await tecnicoService.getFotoBlob(id);
            setFotoBlob(blobUrl);
          } catch {
            setFotoBlob(null);
          }
        } else {
          setFotoBlob(null);
        }
        form.setFieldsValue({
          empresa_id: data.empresa_id,
          nombre: data.nombre ?? undefined,
          primer_apellido: data.primer_apellido ?? undefined,
          segundo_apellido: data.segundo_apellido ?? undefined,
          curp: data.curp ?? undefined,
          rfc: data.rfc ?? undefined,
          nss: data.nss ?? undefined,
          sexo: data.sexo ?? undefined,
          tipo_sangre: data.tipo_sangre ?? undefined,
          numero_trabajador: data.numero_trabajador ?? undefined,
          tipo_personal: data.tipo_personal,
          area: data.area ?? undefined,
          puesto: data.puesto ?? undefined,
          nivel_estudios: data.nivel_estudios ?? undefined,
          salario_base_cotizable: data.salario_base_cotizable ?? undefined,
          telefono: data.telefono ?? undefined,
          celular: data.celular ?? undefined,
          email: data.email ?? undefined,
          direccion: data.direccion ?? undefined,
          licencia_numero: data.licencia_numero ?? undefined,
          licencia_tipo: data.licencia_tipo ?? undefined,
          licencia_vencimiento: data.licencia_vencimiento ? dayjs(data.licencia_vencimiento) : undefined,
          max_servicios_dia: data.max_servicios_dia ?? undefined,
          activo: data.activo,
          notas: data.notas ?? undefined,
          especialidades_ids: data.especialidades.map((e) => e.id),
        });
      })
      .catch((e: any) => { if (!e?._handled) message.error('Error al cargar el registro'); })
      .finally(() => setLoading(false));
  }, [id, form]);

  useEffect(() => {
    if (!id && selectedEmpresaId && !form.getFieldValue('empresa_id')) {
      form.setFieldValue('empresa_id', selectedEmpresaId);
    }
  }, [id, selectedEmpresaId, form]);

  const loadEspecialidades = async (empresaId: string, search = '') => {
    if (!empresaId) return;
    setFetchingEspecialidades(true);
    try {
      const result = await servicioOperativoService.getServicios({
        empresa_id: empresaId,
        q: search || undefined,
        activo: true,
        limit: 100,
        offset: 0,
      });
      setEspecialidadesOptions(result.items.map((s) => ({ value: s.id, label: s.nombre })));
    } catch {
      // silent
    } finally {
      setFetchingEspecialidades(false);
    }
  };

  useEffect(() => {
    if (watchedEmpresaId) loadEspecialidades(watchedEmpresaId);
    else setEspecialidadesOptions([]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchedEmpresaId]);

  // ── Guardar ─────────────────────────────────────────────────────────────────

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      const base = {
        nombre: values.nombre,
        primer_apellido: values.primer_apellido,
        segundo_apellido: values.segundo_apellido ?? null,
        curp: values.curp ?? null,
        rfc: values.rfc ?? null,
        nss: values.nss ?? null,
        sexo: values.sexo ?? null,
        tipo_sangre: values.tipo_sangre ?? null,
        numero_trabajador: values.numero_trabajador ?? null,
        tipo_personal: values.tipo_personal ?? 'TECNICO',
        area: values.area ?? null,
        puesto: values.puesto ?? null,
        nivel_estudios: values.nivel_estudios ?? null,
        salario_base_cotizable: values.salario_base_cotizable ?? null,
        telefono: values.telefono ?? null,
        celular: values.celular ?? null,
        email: values.email ?? null,
        direccion: values.direccion ?? null,
        licencia_numero: values.licencia_numero ?? null,
        licencia_tipo: values.licencia_tipo ?? null,
        licencia_vencimiento: values.licencia_vencimiento
          ? (values.licencia_vencimiento as Dayjs).format('YYYY-MM-DD')
          : null,
        max_servicios_dia: values.max_servicios_dia ?? null,
        activo: values.activo,
        notas: values.notas ?? null,
        especialidades_ids: values.especialidades_ids ?? [],
      };

      if (id) {
        const updated = await tecnicoService.updateTecnico(id, base as TecnicoUpdate);
        setRecord(updated);
        message.success('Registro actualizado');
      } else {
        const payload: TecnicoCreate = { empresa_id: values.empresa_id, ...base, activo: values.activo ?? true };
        const created = await tecnicoService.createTecnico(payload);
        message.success('Registro creado');
        router.push(`/tecnicos/form/${created.id}`);
        return;
      }
    } catch (e: any) {
      if (!e?._handled) message.error('Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  // ── Foto ────────────────────────────────────────────────────────────────────

  const handleFotoUpload = async (file: File) => {
    if (!id) return;
    setUploadingFoto(true);
    try {
      const updated = await tecnicoService.subirFoto(id, file);
      setRecord(updated);
      setFotoBlob(URL.createObjectURL(file));
      message.success('Foto actualizada');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al subir la foto');
    } finally {
      setUploadingFoto(false);
    }
  };

  const handleFotoDelete = async () => {
    if (!id) return;
    setUploadingFoto(true);
    try {
      await tecnicoService.eliminarFoto(id);
      setRecord((prev) => prev ? { ...prev, foto: null } : prev);
      setFotoBlob(null);
      message.success('Foto eliminada');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al eliminar la foto');
    } finally {
      setUploadingFoto(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <Spin spinning tip="Cargando...">
        <div style={{ minHeight: 200 }} />
      </Spin>
    );
  }

  const isEditing = !!id;

  return (
    <>
      <PageHeader title={isEditing ? 'Modificar personal' : 'Nuevo personal'} />

      <div className="app-content">
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{ activo: true, tipo_personal: 'TECNICO' }}
        >
          <Tabs
            defaultActiveKey="datos"
            items={[
              // ────────────────────────────────────────────────────────────
              // Tab 1: Datos Personales
              // ────────────────────────────────────────────────────────────
              {
                key: 'datos',
                label: 'Datos Personales',
                children: (
                  <Card>
                    {record && (
                      <div style={{ marginBottom: 16 }}>
                        <Text type="secondary" style={{ fontSize: '0.85em' }}>
                          Creado: {new Date(record.creado_en).toLocaleString()} &nbsp;|&nbsp;
                          Actualizado: {new Date(record.actualizado_en).toLocaleString()}
                        </Text>
                      </div>
                    )}

                    <Row gutter={24}>
                      <Col xs={24} md={8}>
                        <Form.Item label="CURP" name="curp">
                          <Input maxLength={18} style={{ textTransform: 'uppercase' }} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item label="RFC" name="rfc">
                          <Input maxLength={13} style={{ textTransform: 'uppercase' }} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item label="NSS" name="nss">
                          <Input maxLength={11} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={24} md={8}>
                        <Form.Item
                          label="Nombre"
                          name="nombre"
                          rules={[{ required: true, message: 'El nombre es obligatorio' }]}
                        >
                          <Input maxLength={100} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item
                          label="Primer Apellido"
                          name="primer_apellido"
                          rules={[{ required: true, message: 'El primer apellido es obligatorio' }]}
                        >
                          <Input maxLength={100} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item label="Segundo Apellido" name="segundo_apellido">
                          <Input maxLength={100} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={12} md={6}>
                        <Form.Item label="Sexo" name="sexo">
                          <Select allowClear placeholder="Selecciona">
                            <Option value="HOMBRE">Hombre</Option>
                            <Option value="MUJER">Mujer</Option>
                            <Option value="OTRO">Otro</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col xs={12} md={6}>
                        <Form.Item label="Tipo Sanguíneo" name="tipo_sangre">
                          <Select allowClear placeholder="—">
                            {TIPOS_SANGRE.map((t) => (
                              <Option key={t} value={t}>{t}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col xs={12} md={6}>
                        <Form.Item label="Núm. de Trabajador" name="numero_trabajador">
                          <Input maxLength={30} />
                        </Form.Item>
                      </Col>
                      <Col xs={12} md={6}>
                        <Form.Item label="Nivel de Estudios" name="nivel_estudios">
                          <Select allowClear placeholder="—">
                            {NIVELES_ESTUDIOS.map((n) => (
                              <Option key={n.value} value={n.value}>{n.label}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={24} md={8}>
                        <Form.Item label="Correo Electrónico" name="email"
                          rules={[{ type: 'email', message: 'Ingresa un email válido' }]}>
                          <Input maxLength={150} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item label="Número de Teléfono" name="telefono">
                          <Input maxLength={50} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item label="Número de Celular" name="celular">
                          <Input maxLength={50} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={24}>
                        <Form.Item label="Domicilio" name="direccion">
                          <Input.TextArea rows={2} maxLength={500} />
                        </Form.Item>
                      </Col>
                    </Row>

                    {/* Foto */}
                    <Divider orientation="left" style={{ fontSize: 13 }}>Fotografía</Divider>
                    <Row gutter={32} align="top">
                      <Col>
                        <div style={{ textAlign: 'center' }}>
                          {fotoBlob ? (
                            <div style={{ position: 'relative', display: 'inline-block' }}>
                              <Image
                                src={fotoBlob}
                                alt="Foto personal"
                                width={140}
                                height={180}
                                style={{ objectFit: 'cover', borderRadius: 4, border: '1px solid #d9d9d9', display: 'block' }}
                              />
                              {isEditing && (
                                <Popconfirm
                                  title="¿Eliminar foto?"
                                  onConfirm={handleFotoDelete}
                                  okText="Sí"
                                  cancelText="No"
                                >
                                  <Button
                                    danger
                                    size="small"
                                    icon={<DeleteOutlined />}
                                    style={{ position: 'absolute', top: 4, right: 4, zIndex: 10 }}
                                    loading={uploadingFoto}
                                  />
                                </Popconfirm>
                              )}
                            </div>
                          ) : (
                            <div style={{
                              width: 140, height: 180, border: '1px dashed #d9d9d9',
                              borderRadius: 4, display: 'flex', alignItems: 'center',
                              justifyContent: 'center', color: '#bfbfbf', flexDirection: 'column',
                            }}>
                              <UserOutlined style={{ fontSize: 40 }} />
                              <span style={{ fontSize: 11, marginTop: 4 }}>Sin foto</span>
                            </div>
                          )}
                          {isEditing && (
                            <div style={{ marginTop: 8 }}>
                              <Upload
                                accept="image/*"
                                showUploadList={false}
                                beforeUpload={(file) => {
                                  handleFotoUpload(file as unknown as File);
                                  return false;
                                }}
                              >
                                <Button size="small" icon={<UploadOutlined />} loading={uploadingFoto}>
                                  {fotoBlob ? 'Cambiar Foto' : 'Subir Foto'}
                                </Button>
                              </Upload>
                            </div>
                          )}
                        </div>
                      </Col>
                      <Col flex={1}>
                        <div style={{ padding: '8px 16px', background: '#f9f9f9', borderRadius: 6, fontSize: 13 }}>
                          <Text strong>La fotografía debe:</Text>
                          <ul style={{ marginTop: 8, paddingLeft: 18 }}>
                            <li>Tener fondo blanco.</li>
                            <li>La persona debe estar centrada, desde hombros hasta cabeza.</li>
                            <li>No debe haber más de una persona en la imagen.</li>
                            <li>La fotografía no debe contener ninguna edición.</li>
                          </ul>
                        </div>
                        {!isEditing && (
                          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
                            Guarda el registro primero para poder subir la foto.
                          </Text>
                        )}
                      </Col>
                    </Row>
                  </Card>
                ),
              },

              // ────────────────────────────────────────────────────────────
              // Tab 2: Datos Laborales
              // ────────────────────────────────────────────────────────────
              {
                key: 'laboral',
                label: 'Datos Laborales',
                children: (
                  <Card>
                    <Row gutter={24}>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label="Empresa"
                          name="empresa_id"
                          rules={[{ required: true, message: 'Selecciona una empresa' }]}
                        >
                          <Select placeholder="Selecciona una empresa" disabled={isEditing}>
                            {empresas.map((e) => (
                              <Option key={e.id} value={e.id}>
                                {e.nombre_comercial || e.nombre}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={6}>
                        <Form.Item label="Tipo de Personal" name="tipo_personal">
                          <Select>
                            {TIPOS_PERSONAL.map((t) => (
                              <Option key={t.value} value={t.value}>{t.label}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={6}>
                        <Form.Item label="Activo" name="activo" valuePropName="checked">
                          <Switch />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={24} md={12}>
                        <Form.Item label="Área" name="area">
                          <Input maxLength={100} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={12}>
                        <Form.Item label="Puesto" name="puesto">
                          <Input maxLength={100} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label="Salario Base Cotizable"
                          name="salario_base_cotizable"
                          tooltip="Se usa en la tabla de personal asignado del contrato"
                        >
                          <InputNumber
                            min={0}
                            style={{ width: '100%' }}
                            prefix="$"
                            precision={2}
                            placeholder="0.00"
                          />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={24} md={12}>
                        <Form.Item label="Especialidades / Servicios" name="especialidades_ids">
                          <Select
                            mode="multiple"
                            showSearch
                            allowClear
                            loading={fetchingEspecialidades}
                            placeholder="Buscar servicios operativos..."
                            filterOption={false}
                            onSearch={(val) => {
                              if (watchedEmpresaId) loadEspecialidades(watchedEmpresaId, val);
                            }}
                            options={especialidadesOptions}
                            disabled={!watchedEmpresaId}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={6}>
                        <Form.Item label="Máx. Servicios/Día" name="max_servicios_dia">
                          <InputNumber min={1} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Form.Item label="Notas" name="notas">
                      <TextArea rows={3} maxLength={500} showCount />
                    </Form.Item>
                  </Card>
                ),
              },

              // ────────────────────────────────────────────────────────────
              // Tab 3: Licencia de Conducir
              // ────────────────────────────────────────────────────────────
              {
                key: 'licencia',
                label: 'Licencia',
                children: (
                  <Card>
                    <Row gutter={24}>
                      <Col xs={24} md={8}>
                        <Form.Item label="Número de Licencia" name="licencia_numero">
                          <Input maxLength={50} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item label="Tipo de Licencia" name="licencia_tipo">
                          <Select allowClear placeholder="—">
                            {(['A', 'B', 'C', 'D', 'E'] as LicenciaTipo[]).map((t) => (
                              <Option key={t} value={t}>Tipo {t}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item label="Fecha de Vencimiento" name="licencia_vencimiento">
                          <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                ),
              },
            ]}
          />

          <div style={{ textAlign: 'right', marginTop: 16 }}>
            <Space>
              <Button onClick={() => router.push('/tecnicos')}>Cancelar</Button>
              {isEditing && record && (
                <Button
                  icon={<IdcardOutlined />}
                  loading={generandoCredencial}
                  onClick={async () => {
                    setGenerandoCredencial(true);
                    try {
                      const response = await import('@/lib/axios').then(m =>
                        m.default.get(`/tecnicos/${record.id}/credencial`, { responseType: 'blob' })
                      );
                      if (previewUrl) URL.revokeObjectURL(previewUrl);
                      const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
                      setPreviewUrl(url);
                      setPreviewOpen(true);
                    } catch (e: any) {
                      if (!e?._handled) message.error('Error al generar la credencial');
                    } finally {
                      setGenerandoCredencial(false);
                    }
                  }}
                >
                  Credencial PDF
                </Button>
              )}
              <Button type="primary" htmlType="submit" loading={saving}>
                {isEditing ? 'Actualizar' : 'Guardar y continuar'}
              </Button>
            </Space>
          </div>
        </Form>
      </div>

      {/* ── Modal Vista Previa Credencial ── */}
      <Modal
        title="Vista Previa — Credencial"
        open={previewOpen}
        onCancel={() => {
          setPreviewOpen(false);
        }}
        footer={[
          <Button key="close" onClick={() => setPreviewOpen(false)}>
            Cerrar
          </Button>,
          <Button
            key="download"
            type="primary"
            icon={<FilePdfOutlined />}
            onClick={() => {
              if (!previewUrl || !record) return;
              const a = document.createElement('a');
              a.href = previewUrl;
              a.download = `credencial_${record.nombre_completo.replace(/\s+/g, '_').toLowerCase()}.pdf`;
              a.click();
            }}
          >
            Descargar
          </Button>,
        ]}
        width="50%"
        style={{ top: 20 }}
        styles={{ body: { height: '80vh', padding: 0 } }}
        destroyOnHidden
      >
        {previewUrl && (
          <iframe
            src={previewUrl}
            style={{ width: '100%', height: '100%', border: 'none' }}
            title="Vista Previa Credencial"
          />
        )}
      </Modal>
    </>
  );
};

export default PersonalForm;
