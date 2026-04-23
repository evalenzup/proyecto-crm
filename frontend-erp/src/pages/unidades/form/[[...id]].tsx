'use client';
// pages/unidades/form/[[...id]].tsx

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
import { unidadService, UnidadOut, UnidadCreate, UnidadUpdate, TipoUnidad } from '@/services/unidadService';
import { servicioOperativoService } from '@/services/servicioOperativoService';

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

const TIPOS_UNIDAD: TipoUnidad[] = ['SEDAN', 'PICKUP', 'CAMIONETA', 'MOTOCICLETA', 'OTRO'];

const UnidadForm: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const { selectedEmpresaId, empresas, isAdmin } = useEmpresaSelector();

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [record, setRecord] = useState<UnidadOut | null>(null);

  // Servicios compatibles options
  const [serviciosOptions, setServiciosOptions] = useState<{ value: string; label: string }[]>([]);
  const [fetchingServicios, setFetchingServicios] = useState(false);

  const watchedEmpresaId = Form.useWatch('empresa_id', form);

  // Load existing record when editing
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    unidadService
      .getUnidad(id)
      .then((data) => {
        setRecord(data);
        form.setFieldsValue({
          empresa_id: data.empresa_id,
          nombre: data.nombre,
          placa: data.placa ?? undefined,
          tipo: data.tipo,
          max_servicios_dia: data.max_servicios_dia ?? undefined,
          activo: data.activo,
          notas: data.notas ?? undefined,
          servicios_ids: data.servicios_compatibles.map((s) => s.id),
        });
      })
      .catch(() => message.error('Error al cargar la unidad'))
      .finally(() => setLoading(false));
  }, [id, form]);

  // Set default empresa_id for new records
  useEffect(() => {
    if (!id && selectedEmpresaId && !form.getFieldValue('empresa_id')) {
      form.setFieldValue('empresa_id', selectedEmpresaId);
    }
  }, [id, selectedEmpresaId, form]);

  // Load servicios options when empresa changes
  const loadServicios = async (empresaId: string, search = '') => {
    if (!empresaId) return;
    setFetchingServicios(true);
    try {
      const result = await servicioOperativoService.getServicios({
        empresa_id: empresaId,
        q: search || undefined,
        activo: true,
        limit: 100,
        offset: 0,
      });
      setServiciosOptions(result.items.map((s) => ({ value: s.id, label: s.nombre })));
    } catch {
      // silent
    } finally {
      setFetchingServicios(false);
    }
  };

  useEffect(() => {
    if (watchedEmpresaId) {
      loadServicios(watchedEmpresaId);
    } else {
      setServiciosOptions([]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchedEmpresaId]);

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      if (id) {
        const payload: UnidadUpdate = {
          nombre: values.nombre,
          placa: values.placa ?? null,
          tipo: values.tipo,
          max_servicios_dia: values.max_servicios_dia ?? null,
          activo: values.activo,
          notas: values.notas ?? null,
          servicios_ids: values.servicios_ids ?? [],
        };
        await unidadService.updateUnidad(id, payload);
        message.success('Unidad actualizada');
      } else {
        const payload: UnidadCreate = {
          empresa_id: values.empresa_id,
          nombre: values.nombre,
          placa: values.placa ?? null,
          tipo: values.tipo ?? 'OTRO',
          max_servicios_dia: values.max_servicios_dia ?? null,
          activo: values.activo ?? true,
          notas: values.notas ?? null,
          servicios_ids: values.servicios_ids ?? [],
        };
        await unidadService.createUnidad(payload);
        message.success('Unidad creada');
      }
      router.push('/unidades');
    } catch {
      message.error('Error al guardar la unidad');
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
          <h1 className="app-title">{id ? 'Editar Unidad' : 'Nueva Unidad'}</h1>
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
            initialValues={{ activo: true, tipo: 'OTRO' }}
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

            <Form.Item label="Placa" name="placa">
              <Input maxLength={20} />
            </Form.Item>

            <Form.Item label="Tipo" name="tipo">
              <Select placeholder="Selecciona un tipo">
                {TIPOS_UNIDAD.map((t) => (
                  <Option key={t} value={t}>
                    {t}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item label="Max Servicios/Día" name="max_servicios_dia">
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item label="Servicios Compatibles" name="servicios_ids">
              <Select
                mode="multiple"
                showSearch
                allowClear
                loading={fetchingServicios}
                placeholder="Buscar servicios operativos..."
                filterOption={false}
                onSearch={(val) => {
                  if (watchedEmpresaId) loadServicios(watchedEmpresaId, val);
                }}
                options={serviciosOptions}
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
                <Button onClick={() => router.push('/unidades')}>Cancelar</Button>
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

export default UnidadForm;
