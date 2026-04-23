'use client';
// pages/servicios-operativos/form/[[...id]].tsx

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
import {
  servicioOperativoService,
  ServicioOperativoOut,
  ServicioOperativoCreate,
  ServicioOperativoUpdate,
} from '@/services/servicioOperativoService';

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

const ServicioOperativoForm: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const { selectedEmpresaId, empresas, isAdmin } = useEmpresaSelector();

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [record, setRecord] = useState<ServicioOperativoOut | null>(null);

  // For servicio_padre_id select
  const [padreOptions, setPadreOptions] = useState<{ value: string; label: string }[]>([]);
  const [fetchingPadre, setFetchingPadre] = useState(false);

  const watchedEmpresaId = Form.useWatch('empresa_id', form);

  // Load existing record when editing
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    servicioOperativoService
      .getServicio(id)
      .then((data) => {
        setRecord(data);
        form.setFieldsValue({
          empresa_id: data.empresa_id,
          nombre: data.nombre,
          descripcion: data.descripcion ?? undefined,
          duracion_estimada_min: data.duracion_estimada_min ?? undefined,
          duracion_variable: data.duracion_variable,
          personal_requerido: data.personal_requerido,
          requiere_vehiculo: data.requiere_vehiculo,
          servicio_padre_id: data.servicio_padre_id ?? undefined,
          observaciones: data.observaciones ?? undefined,
          activo: data.activo,
        });
      })
      .catch(() => message.error('Error al cargar el servicio'))
      .finally(() => setLoading(false));
  }, [id, form]);

  // Set default empresa_id for new records
  useEffect(() => {
    if (!id && selectedEmpresaId && !form.getFieldValue('empresa_id')) {
      form.setFieldValue('empresa_id', selectedEmpresaId);
    }
  }, [id, selectedEmpresaId, form]);

  // Load parent service options when empresa changes
  const loadPadreOptions = async (empresaId: string, search = '') => {
    if (!empresaId) return;
    setFetchingPadre(true);
    try {
      const result = await servicioOperativoService.getServicios({
        empresa_id: empresaId,
        q: search || undefined,
        activo: true,
        limit: 50,
        offset: 0,
      });
      setPadreOptions(
        result.items
          .filter((s) => s.id !== id)
          .map((s) => ({ value: s.id, label: s.nombre }))
      );
    } catch {
      // silent
    } finally {
      setFetchingPadre(false);
    }
  };

  useEffect(() => {
    if (watchedEmpresaId) {
      loadPadreOptions(watchedEmpresaId);
    } else {
      setPadreOptions([]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchedEmpresaId]);

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      if (id) {
        const payload: ServicioOperativoUpdate = {
          nombre: values.nombre,
          descripcion: values.descripcion ?? null,
          duracion_estimada_min: values.duracion_estimada_min ?? null,
          duracion_variable: values.duracion_variable,
          personal_requerido: values.personal_requerido,
          requiere_vehiculo: values.requiere_vehiculo,
          servicio_padre_id: values.servicio_padre_id ?? null,
          observaciones: values.observaciones ?? null,
          activo: values.activo,
        };
        await servicioOperativoService.updateServicio(id, payload);
        message.success('Servicio actualizado');
      } else {
        const payload: ServicioOperativoCreate = {
          empresa_id: values.empresa_id,
          nombre: values.nombre,
          descripcion: values.descripcion ?? null,
          duracion_estimada_min: values.duracion_estimada_min ?? null,
          duracion_variable: values.duracion_variable ?? false,
          personal_requerido: values.personal_requerido ?? 1,
          requiere_vehiculo: values.requiere_vehiculo ?? false,
          servicio_padre_id: values.servicio_padre_id ?? null,
          observaciones: values.observaciones ?? null,
          activo: values.activo ?? true,
        };
        await servicioOperativoService.createServicio(payload);
        message.success('Servicio creado');
      }
      router.push('/servicios-operativos');
    } catch {
      message.error('Error al guardar el servicio');
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
          <h1 className="app-title">
            {id ? 'Editar Servicio Operativo' : 'Nuevo Servicio Operativo'}
          </h1>
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
            initialValues={{
              duracion_variable: false,
              personal_requerido: 1,
              requiere_vehiculo: false,
              activo: true,
            }}
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
              label="Nombre"
              name="nombre"
              rules={[{ required: true, message: 'El nombre es obligatorio' }]}
            >
              <Input maxLength={200} />
            </Form.Item>

            <Form.Item label="Descripción" name="descripcion">
              <TextArea rows={3} maxLength={500} showCount />
            </Form.Item>

            <Form.Item label="Duración Estimada (min)" name="duracion_estimada_min">
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item label="Duración Variable" name="duracion_variable" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item label="Personal Requerido" name="personal_requerido">
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item label="Requiere Vehículo" name="requiere_vehiculo" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item label="Servicio Padre" name="servicio_padre_id">
              <Select
                showSearch
                allowClear
                loading={fetchingPadre}
                placeholder="Buscar servicio padre..."
                filterOption={false}
                onSearch={(val) => {
                  if (watchedEmpresaId) loadPadreOptions(watchedEmpresaId, val);
                }}
                options={padreOptions}
                disabled={!watchedEmpresaId}
              />
            </Form.Item>

            <Form.Item label="Observaciones" name="observaciones">
              <TextArea rows={3} maxLength={500} showCount />
            </Form.Item>

            <Form.Item label="Activo" name="activo" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item style={{ textAlign: 'right', marginTop: 16 }}>
              <Space>
                <Button onClick={() => router.push('/servicios-operativos')}>Cancelar</Button>
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

export default ServicioOperativoForm;
