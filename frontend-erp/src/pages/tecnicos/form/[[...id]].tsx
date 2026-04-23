'use client';
// pages/tecnicos/form/[[...id]].tsx

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import {
  Form,
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
} from 'antd';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import { tecnicoService, TecnicoOut, TecnicoCreate, TecnicoUpdate } from '@/services/tecnicoService';
import { servicioOperativoService } from '@/services/servicioOperativoService';

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

const TecnicoForm: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const { selectedEmpresaId, empresas, isAdmin } = useEmpresaSelector();

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [record, setRecord] = useState<TecnicoOut | null>(null);

  // Especialidades options (servicios operativos of selected empresa)
  const [especialidadesOptions, setEspecialidadesOptions] = useState<
    { value: string; label: string }[]
  >([]);
  const [fetchingEspecialidades, setFetchingEspecialidades] = useState(false);

  const watchedEmpresaId = Form.useWatch('empresa_id', form);

  // Load existing record when editing
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    tecnicoService
      .getTecnico(id)
      .then((data) => {
        setRecord(data);
        form.setFieldsValue({
          empresa_id: data.empresa_id,
          nombre_completo: data.nombre_completo,
          telefono: data.telefono ?? undefined,
          email: data.email ?? undefined,
          max_servicios_dia: data.max_servicios_dia ?? undefined,
          activo: data.activo,
          notas: data.notas ?? undefined,
          especialidades_ids: data.especialidades.map((e) => e.id),
        });
      })
      .catch(() => message.error('Error al cargar el técnico'))
      .finally(() => setLoading(false));
  }, [id, form]);

  // Set default empresa_id for new records
  useEffect(() => {
    if (!id && selectedEmpresaId && !form.getFieldValue('empresa_id')) {
      form.setFieldValue('empresa_id', selectedEmpresaId);
    }
  }, [id, selectedEmpresaId, form]);

  // Load especialidades options when empresa changes
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
    if (watchedEmpresaId) {
      loadEspecialidades(watchedEmpresaId);
    } else {
      setEspecialidadesOptions([]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchedEmpresaId]);

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      if (id) {
        const payload: TecnicoUpdate = {
          nombre_completo: values.nombre_completo,
          telefono: values.telefono ?? null,
          email: values.email ?? null,
          max_servicios_dia: values.max_servicios_dia ?? null,
          activo: values.activo,
          notas: values.notas ?? null,
          especialidades_ids: values.especialidades_ids ?? [],
        };
        await tecnicoService.updateTecnico(id, payload);
        message.success('Técnico actualizado');
      } else {
        const payload: TecnicoCreate = {
          empresa_id: values.empresa_id,
          nombre_completo: values.nombre_completo,
          telefono: values.telefono ?? null,
          email: values.email ?? null,
          max_servicios_dia: values.max_servicios_dia ?? null,
          activo: values.activo ?? true,
          notas: values.notas ?? null,
          especialidades_ids: values.especialidades_ids ?? [],
        };
        await tecnicoService.createTecnico(payload);
        message.success('Técnico creado');
      }
      router.push('/tecnicos');
    } catch {
      message.error('Error al guardar el técnico');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Spin spinning tip="Cargando...">
        <div style={{ minHeight: 200 }} />
      </Spin>
    );
  }

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">{id ? 'Editar Técnico' : 'Nuevo Técnico'}</h1>
        </div>
      </div>
      <div className="app-content">
        <Card>
          {record && (
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: '0.85em' }}>
                Creado: {new Date(record.creado_en).toLocaleString()} &nbsp;|&nbsp;
                Actualizado: {new Date(record.actualizado_en).toLocaleString()}
              </Text>
            </div>
          )}
          <Form
            form={form}
            layout="vertical"
            onFinish={onFinish}
            initialValues={{ activo: true }}
          >
            <Form.Item
              label="Empresa"
              name="empresa_id"
              rules={[{ required: true, message: 'Selecciona una empresa' }]}
            >
              <Select placeholder="Selecciona una empresa" disabled={!!id}>
                {empresas.map((e) => (
                  <Option key={e.id} value={e.id}>
                    {e.nombre_comercial || e.nombre}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="Nombre Completo"
              name="nombre_completo"
              rules={[{ required: true, message: 'El nombre es obligatorio' }]}
            >
              <Input maxLength={200} />
            </Form.Item>

            <Form.Item label="Teléfono" name="telefono">
              <Input maxLength={20} />
            </Form.Item>

            <Form.Item
              label="Email"
              name="email"
              rules={[{ type: 'email', message: 'Ingresa un email válido' }]}
            >
              <Input maxLength={200} />
            </Form.Item>

            <Form.Item label="Max Servicios/Día" name="max_servicios_dia">
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item label="Especialidades" name="especialidades_ids">
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

            <Form.Item label="Notas" name="notas">
              <TextArea rows={3} maxLength={500} showCount />
            </Form.Item>

            <Form.Item label="Activo" name="activo" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item style={{ textAlign: 'right', marginTop: 16 }}>
              <Space>
                <Button onClick={() => router.push('/tecnicos')}>Cancelar</Button>
                <Button type="primary" htmlType="submit" loading={saving}>
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

export default TecnicoForm;
