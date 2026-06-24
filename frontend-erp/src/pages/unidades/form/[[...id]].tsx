'use client';
// pages/unidades/form/[[...id]].tsx

import React, { useState, useEffect, useCallback } from 'react';
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
  Tabs,
  Row,
  Col,
  Divider,
  DatePicker,
  Upload,
  Table,
  Modal,
  Tag,
  Popconfirm,
  Tooltip,
} from 'antd';
import {
  UploadOutlined,
  DeleteOutlined,
  PlusOutlined,
  EditOutlined,
  FilePdfOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import dayjs, { Dayjs } from 'dayjs';
import api from '@/lib/axios';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import {
  unidadService,
  UnidadOut,
  UnidadCreate,
  UnidadUpdate,
  TipoUnidad,
  PolizaSeguroOut,
  PolizaSeguroCreate,
  PolizaSeguroUpdate,
} from '@/services/unidadService';
import { servicioOperativoService } from '@/services/servicioOperativoService';

const { TextArea } = Input;
const { Text, Title } = Typography;
const { Option } = Select;

const TIPOS_UNIDAD: { value: TipoUnidad; label: string }[] = [
  { value: 'SEDAN', label: 'Sedán' },
  { value: 'PICKUP', label: 'Pickup' },
  { value: 'CAMIONETA', label: 'Camioneta' },
  { value: 'VAN', label: 'Van' },
  { value: 'CAMION', label: 'Camión' },
  { value: 'MOTOCICLETA', label: 'Motocicleta' },
  { value: 'OTRO', label: 'Otro' },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/$/, '');

/** Abre un documento de unidad via endpoint autenticado (evita exposición de /data sin auth). */
const abrirDocUnidad = async (filename: string) => {
  try {
    const { data } = await api.get(
      `${API_BASE}/unidades/docs/archivo?ruta=${encodeURIComponent(filename)}`,
      { responseType: 'blob' },
    );
    const url = URL.createObjectURL(data);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  } catch {
    // message import may not exist at module level; use console as fallback
    console.error('No se pudo abrir el documento');
  }
};

function toDateValue(v: string | null | undefined): Dayjs | null {
  return v ? dayjs(v) : null;
}

// ─── Componente FotoUpload ─────────────────────────────────────────────────────

interface FotoUploadProps {
  label: string;
  blobUrl: string | null | undefined;
  onUpload: (file: File) => Promise<void>;
  onDelete: () => Promise<void>;
  uploading: boolean;
}

const FotoUpload: React.FC<FotoUploadProps> = ({ label, blobUrl, onUpload, onDelete, uploading }) => (
  <div style={{ textAlign: 'center' }}>
    <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
      {label}
    </Text>
    {blobUrl ? (
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <Image
          src={blobUrl}
          alt={label}
          width={160}
          height={110}
          style={{ objectFit: 'cover', borderRadius: 6, border: '1px solid #d9d9d9', display: 'block' }}
        />
        <Popconfirm title="¿Eliminar foto?" onConfirm={onDelete} okText="Sí" cancelText="No">
          <Button
            danger
            size="small"
            icon={<DeleteOutlined />}
            style={{ position: 'absolute', top: 4, right: 4, zIndex: 10 }}
            loading={uploading}
          />
        </Popconfirm>
      </div>
    ) : (
      <Upload
        accept="image/*"
        showUploadList={false}
        beforeUpload={(file) => {
          onUpload(file as unknown as File);
          return false;
        }}
      >
        <Button
          icon={<UploadOutlined />}
          loading={uploading}
          style={{ width: 160, height: 110, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}
        >
          <span style={{ marginTop: 4, fontSize: 12 }}>Subir imagen</span>
        </Button>
      </Upload>
    )}
  </div>
);

// ─── Componente DocUpload ─────────────────────────────────────────────────────

interface DocUploadProps {
  label: string;
  filename: string | null | undefined;
  onUpload: (file: File) => Promise<void>;
  onDelete: () => Promise<void>;
  uploading: boolean;
}

const DocUpload: React.FC<DocUploadProps> = ({ label, filename, onUpload, onDelete, uploading }) => {
  return (
    <Space>
      {filename ? (
        <>
          <Button
            icon={<FilePdfOutlined />}
            size="small"
            onClick={() => abrirDocUnidad(filename)}
          >
            {filename?.slice(0, 20)}…
          </Button>
          <Popconfirm title={`¿Eliminar ${label}?`} onConfirm={onDelete} okText="Sí" cancelText="No">
            <Button danger size="small" icon={<DeleteOutlined />} loading={uploading}>
              Eliminar
            </Button>
          </Popconfirm>
        </>
      ) : (
        <Upload
          accept=".pdf,image/*"
          showUploadList={false}
          beforeUpload={(file) => {
            onUpload(file as unknown as File);
            return false;
          }}
        >
          <Button icon={<UploadOutlined />} loading={uploading} size="small">
            Subir {label}
          </Button>
        </Upload>
      )}
    </Space>
  );
};

// ─── Modal Póliza ─────────────────────────────────────────────────────────────

interface PolizaModalProps {
  open: boolean;
  unidadId: string;
  poliza: PolizaSeguroOut | null;
  onClose: () => void;
  onSaved: (p: PolizaSeguroOut) => void;
}

const PolizaModal: React.FC<PolizaModalProps> = ({ open, unidadId, poliza, onClose, onSaved }) => {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      if (poliza) {
        form.setFieldsValue({
          num_poliza: poliza.num_poliza,
          compania: poliza.compania,
          fecha_expedicion: toDateValue(poliza.fecha_expedicion),
          fecha_vencimiento: toDateValue(poliza.fecha_vencimiento),
          activo: poliza.activo,
        });
      } else {
        form.resetFields();
        form.setFieldValue('activo', true);
      }
    }
  }, [open, poliza, form]);

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      const payload = {
        num_poliza: values.num_poliza,
        compania: values.compania,
        fecha_expedicion: values.fecha_expedicion ? values.fecha_expedicion.format('YYYY-MM-DD') : null,
        fecha_vencimiento: values.fecha_vencimiento ? values.fecha_vencimiento.format('YYYY-MM-DD') : null,
        activo: values.activo ?? true,
      };
      let result: PolizaSeguroOut;
      if (poliza) {
        result = await unidadService.actualizarPoliza(unidadId, poliza.id, payload as PolizaSeguroUpdate);
        message.success('Póliza actualizada');
      } else {
        result = await unidadService.crearPoliza(unidadId, payload as PolizaSeguroCreate);
        message.success('Póliza creada');
      }
      onSaved(result);
      onClose();
    } catch (e: any) {
      if (!e?._handled) message.error('Error al guardar la póliza');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title={poliza ? 'Editar Póliza de Seguro' : 'Nueva Póliza de Seguro'}
      onCancel={onClose}
      footer={null}
      width="min(95vw, 480px)"
    >
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Form.Item label="Número de Póliza" name="num_poliza" rules={[{ required: true }]}>
          <Input maxLength={60} />
        </Form.Item>
        <Form.Item label="Compañía" name="compania" rules={[{ required: true }]}>
          <Input maxLength={100} />
        </Form.Item>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Fecha Expedición" name="fecha_expedicion">
              <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Fecha Vencimiento" name="fecha_vencimiento">
              <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item label="Activo" name="activo" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
          <Space>
            <Button onClick={onClose}>Cancelar</Button>
            <Button type="primary" htmlType="submit" loading={saving}>
              {poliza ? 'Actualizar' : 'Guardar'}
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

// ─── Formulario Principal ─────────────────────────────────────────────────────

const UnidadForm: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const { selectedEmpresaId, empresas, isAdmin } = useEmpresaSelector();

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [record, setRecord] = useState<UnidadOut | null>(null);

  // Servicios compatibles
  const [serviciosOptions, setServiciosOptions] = useState<{ value: string; label: string }[]>([]);
  const [fetchingServicios, setFetchingServicios] = useState(false);

  // Fotos
  const [uploadingFoto, setUploadingFoto] = useState<Record<string, boolean>>({});
  const [fotosBlob, setFotosBlob] = useState<Record<string, string | null>>({});

  // Docs
  const [uploadingDoc, setUploadingDoc] = useState<Record<string, boolean>>({});

  // Pólizas
  const [polizas, setPolizas] = useState<PolizaSeguroOut[]>([]);
  const [polizaModalOpen, setPolizaModalOpen] = useState(false);
  const [editingPoliza, setEditingPoliza] = useState<PolizaSeguroOut | null>(null);
  const [uploadingDocPoliza, setUploadingDocPoliza] = useState<Record<string, boolean>>({});

  const watchedEmpresaId = Form.useWatch('empresa_id', form);

  // ── Carga del registro ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        const data = await unidadService.getUnidad(id);
        setRecord(data);
        setPolizas(data.polizas_seguro);
        form.setFieldsValue({
          empresa_id: data.empresa_id,
          nombre: data.nombre,
          placa: data.placa ?? undefined,
          tipo: data.tipo,
          max_servicios_dia: data.max_servicios_dia ?? undefined,
          activo: data.activo,
          notas: data.notas ?? undefined,
          servicios_ids: data.servicios_compatibles.map((s) => s.id),
          // Vehículo
          numero_serie: data.numero_serie ?? undefined,
          marca: data.marca ?? undefined,
          version: data.version ?? undefined,
          modelo_anio: data.modelo_anio ?? undefined,
          capacidad_personas: data.capacidad_personas ?? undefined,
          color: data.color ?? undefined,
          numero_motor: data.numero_motor ?? undefined,
          numero_economico: data.numero_economico ?? undefined,
          propietario: data.propietario ?? undefined,
          // Tarjeta circulación
          tarjeta_circulacion: data.tarjeta_circulacion ?? undefined,
          fecha_expedicion_tc: toDateValue(data.fecha_expedicion_tc),
          fecha_vencimiento_tc: toDateValue(data.fecha_vencimiento_tc),
        });

        // Cargar fotos como blobs autenticados
        const campos = ['foto_frontal', 'foto_lateral', 'foto_placa'] as const;
        const blobs: Record<string, string | null> = {};
        await Promise.all(campos.map(async (campo) => {
          if (data[campo]) {
            try {
              blobs[campo] = await unidadService.getFotoBlob(id, campo);
            } catch {
              blobs[campo] = null;
            }
          } else {
            blobs[campo] = null;
          }
        }));
        setFotosBlob(blobs);
      } catch (e: any) {
        if (!e?._handled) message.error('Error al cargar la unidad');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id, form]);

  // Set empresa default para nuevos registros
  useEffect(() => {
    if (!id && selectedEmpresaId && !form.getFieldValue('empresa_id')) {
      form.setFieldValue('empresa_id', selectedEmpresaId);
    }
  }, [id, selectedEmpresaId, form]);

  // Cargar servicios según empresa
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

  // ── Guardar ─────────────────────────────────────────────────────────────────

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      const basePayload = {
        nombre: values.nombre,
        placa: values.placa ?? null,
        tipo: values.tipo,
        max_servicios_dia: values.max_servicios_dia ?? null,
        activo: values.activo,
        notas: values.notas ?? null,
        servicios_ids: values.servicios_ids ?? [],
        numero_serie: values.numero_serie ?? null,
        marca: values.marca ?? null,
        version: values.version ?? null,
        modelo_anio: values.modelo_anio ?? null,
        capacidad_personas: values.capacidad_personas ?? null,
        color: values.color ?? null,
        numero_motor: values.numero_motor ?? null,
        numero_economico: values.numero_economico ?? null,
        propietario: values.propietario ?? null,
        tarjeta_circulacion: values.tarjeta_circulacion ?? null,
        fecha_expedicion_tc: values.fecha_expedicion_tc
          ? (values.fecha_expedicion_tc as Dayjs).format('YYYY-MM-DD')
          : null,
        fecha_vencimiento_tc: values.fecha_vencimiento_tc
          ? (values.fecha_vencimiento_tc as Dayjs).format('YYYY-MM-DD')
          : null,
      };

      if (id) {
        const updated = await unidadService.updateUnidad(id, basePayload as UnidadUpdate);
        setRecord(updated);
        message.success('Unidad actualizada');
      } else {
        const payload: UnidadCreate = {
          empresa_id: values.empresa_id,
          ...basePayload,
          activo: values.activo ?? true,
          tipo: values.tipo ?? 'OTRO',
        };
        const created = await unidadService.createUnidad(payload);
        message.success('Unidad creada');
        router.push(`/unidades/form/${created.id}`);
        return;
      }
    } catch (e: any) {
      if (!e?._handled) message.error('Error al guardar la unidad');
    } finally {
      setSaving(false);
    }
  };

  // ── Fotos ───────────────────────────────────────────────────────────────────

  const handleFotoUpload = async (campo: 'foto_frontal' | 'foto_lateral' | 'foto_placa', file: File) => {
    if (!id) return;
    setUploadingFoto((p) => ({ ...p, [campo]: true }));
    try {
      const updated = await unidadService.subirFoto(id, campo, file);
      setRecord(updated);
      setFotosBlob((p) => ({ ...p, [campo]: URL.createObjectURL(file) }));
      message.success('Foto subida correctamente');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al subir la foto');
    } finally {
      setUploadingFoto((p) => ({ ...p, [campo]: false }));
    }
  };

  const handleFotoDelete = async (campo: 'foto_frontal' | 'foto_lateral' | 'foto_placa') => {
    if (!id) return;
    setUploadingFoto((p) => ({ ...p, [campo]: true }));
    try {
      await unidadService.eliminarFoto(id, campo);
      setRecord((prev) => prev ? { ...prev, [campo]: null } : prev);
      setFotosBlob((p) => ({ ...p, [campo]: null }));
      message.success('Foto eliminada');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al eliminar la foto');
    } finally {
      setUploadingFoto((p) => ({ ...p, [campo]: false }));
    }
  };

  // ── Doc Tarjeta Circulación ─────────────────────────────────────────────────

  const handleDocTCUpload = async (file: File) => {
    if (!id) return;
    setUploadingDoc((p) => ({ ...p, tc: true }));
    try {
      const updated = await unidadService.subirDocTarjetaCirculacion(id, file);
      setRecord(updated);
      message.success('Documento subido correctamente');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al subir el documento');
    } finally {
      setUploadingDoc((p) => ({ ...p, tc: false }));
    }
  };

  const handleDocTCDelete = async () => {
    if (!id) return;
    setUploadingDoc((p) => ({ ...p, tc: true }));
    try {
      await unidadService.eliminarDocTarjetaCirculacion(id);
      setRecord((prev) => prev ? { ...prev, doc_tarjeta_circulacion: null } : prev);
      message.success('Documento eliminado');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al eliminar el documento');
    } finally {
      setUploadingDoc((p) => ({ ...p, tc: false }));
    }
  };

  // ── Doc Comprobante de Pago de TC ───────────────────────────────────────────

  const handleComprobantePagoTCUpload = async (file: File) => {
    if (!id) return;
    setUploadingDoc((p) => ({ ...p, comprobante_tc: true }));
    try {
      const updated = await unidadService.subirDocComprobantePagoTC(id, file);
      setRecord(updated);
      message.success('Comprobante subido correctamente');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al subir el comprobante');
    } finally {
      setUploadingDoc((p) => ({ ...p, comprobante_tc: false }));
    }
  };

  const handleComprobantePagoTCDelete = async () => {
    if (!id) return;
    setUploadingDoc((p) => ({ ...p, comprobante_tc: true }));
    try {
      await unidadService.eliminarDocComprobantePagoTC(id);
      setRecord((prev) => prev ? { ...prev, doc_comprobante_pago_tc: null } : prev);
      message.success('Comprobante eliminado');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al eliminar el comprobante');
    } finally {
      setUploadingDoc((p) => ({ ...p, comprobante_tc: false }));
    }
  };

  // ── Pólizas ─────────────────────────────────────────────────────────────────

  const handlePolizaDelete = async (polizaId: string) => {
    if (!id) return;
    try {
      await unidadService.eliminarPoliza(id, polizaId);
      setPolizas((prev) => prev.filter((p) => p.id !== polizaId));
      message.success('Póliza eliminada');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al eliminar la póliza');
    }
  };

  const handleDocPolizaUpload = async (polizaId: string, file: File) => {
    if (!id) return;
    setUploadingDocPoliza((p) => ({ ...p, [polizaId]: true }));
    try {
      const updated = await unidadService.subirDocPoliza(id, polizaId, file);
      setPolizas((prev) => prev.map((p) => (p.id === polizaId ? updated : p)));
      message.success('Documento de póliza subido');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al subir el documento');
    } finally {
      setUploadingDocPoliza((p) => ({ ...p, [polizaId]: false }));
    }
  };

  const handleDocPolizaDelete = async (polizaId: string) => {
    if (!id) return;
    setUploadingDocPoliza((p) => ({ ...p, [polizaId]: true }));
    try {
      await unidadService.eliminarDocPoliza(id, polizaId);
      setPolizas((prev) => prev.map((p) => (p.id === polizaId ? { ...p, documento: null } : p)));
      message.success('Documento eliminado');
    } catch (e: any) {
      if (!e?._handled) message.error('Error al eliminar el documento');
    } finally {
      setUploadingDocPoliza((p) => ({ ...p, [polizaId]: false }));
    }
  };

  // ── Tabla Pólizas ────────────────────────────────────────────────────────────

  const polizasColumns = [
    {
      title: 'No. Póliza',
      dataIndex: 'num_poliza',
      key: 'num_poliza',
      width: 140,
    },
    {
      title: 'Compañía',
      dataIndex: 'compania',
      key: 'compania',
    },
    {
      title: 'Vencimiento',
      dataIndex: 'fecha_vencimiento',
      key: 'fecha_vencimiento',
      width: 120,
      render: (v: string | null) =>
        v ? dayjs(v).format('DD/MM/YYYY') : <Text type="secondary">—</Text>,
    },
    {
      title: 'Estado',
      dataIndex: 'activo',
      key: 'activo',
      width: 90,
      render: (v: boolean) =>
        v ? (
          <Tag icon={<CheckCircleOutlined />} color="success">Activa</Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="error">Inactiva</Tag>
        ),
    },
    {
      title: 'Documento',
      key: 'documento',
      width: 160,
      render: (_: any, row: PolizaSeguroOut) => {
        if (!id) return null;
        return (
          <Space size="small">
            {row.documento ? (
              <>
                <Button
                  size="small"
                  icon={<FilePdfOutlined />}
                  onClick={() => abrirDocUnidad(row.documento!)}
                />
                <Popconfirm
                  title="¿Eliminar documento?"
                  onConfirm={() => handleDocPolizaDelete(row.id)}
                  okText="Sí"
                  cancelText="No"
                >
                  <Button
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    loading={uploadingDocPoliza[row.id]}
                  />
                </Popconfirm>
              </>
            ) : (
              <Upload
                accept=".pdf,image/*"
                showUploadList={false}
                beforeUpload={(file) => {
                  handleDocPolizaUpload(row.id, file as unknown as File);
                  return false;
                }}
              >
                <Button
                  size="small"
                  icon={<UploadOutlined />}
                  loading={uploadingDocPoliza[row.id]}
                >
                  Subir
                </Button>
              </Upload>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 90,
      render: (_: any, row: PolizaSeguroOut) => (
        <Space size="small">
          <Tooltip title="Editar">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingPoliza(row);
                setPolizaModalOpen(true);
              }}
            />
          </Tooltip>
          <Popconfirm
            title="¿Eliminar esta póliza?"
            onConfirm={() => handlePolizaDelete(row.id)}
            okText="Sí"
            cancelText="No"
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // ─── Render ─────────────────────────────────────────────────────────────────

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
      <PageHeader title={isEditing ? 'Editar Unidad' : 'Nueva Unidad'} />

      <div className="app-content">
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{ activo: true, tipo: 'OTRO' }}
        >
          <Tabs
            defaultActiveKey="general"
            items={[
              // ──────────────────────────────────────────────────────────────
              // Tab 1: Datos Generales
              // ──────────────────────────────────────────────────────────────
              {
                key: 'general',
                label: 'Datos Generales',
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
                      <Col xs={24} md={12}>
                        <Form.Item
                          label="Nombre / Alias"
                          name="nombre"
                          rules={[{ required: true, message: 'El nombre es obligatorio' }]}
                        >
                          <Input maxLength={100} placeholder="Ej. Unidad 01 / Suburban Blanca" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Placa" name="placa">
                          <Input maxLength={20} placeholder="ABC-123" />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Tipo de Vehículo" name="tipo">
                          <Select placeholder="Selecciona">
                            {TIPOS_UNIDAD.map((t) => (
                              <Option key={t.value} value={t.value}>{t.label}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Número Económico" name="numero_economico">
                          <Input maxLength={30} placeholder="Ej. 01" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Marca" name="marca">
                          <Input maxLength={60} placeholder="Ej. Chevrolet" />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Versión / Submarca" name="version">
                          <Input maxLength={60} placeholder="Ej. Suburban LT" />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Año Modelo" name="modelo_anio">
                          <InputNumber
                            min={1900}
                            max={new Date().getFullYear() + 2}
                            style={{ width: '100%' }}
                            placeholder="Ej. 2022"
                          />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Color" name="color">
                          <Input maxLength={30} placeholder="Ej. Blanco" />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Capacidad (personas)" name="capacidad_personas">
                          <InputNumber min={0} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Máx. Servicios/Día" name="max_servicios_dia">
                          <InputNumber min={1} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Divider orientation="left" style={{ fontSize: 13 }}>Identificación del Vehículo</Divider>

                    <Row gutter={24}>
                      <Col xs={24} sm={8}>
                        <Form.Item label="No. de Serie (VIN)" name="numero_serie">
                          <Input maxLength={50} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Form.Item label="No. de Motor" name="numero_motor">
                          <Input maxLength={50} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Form.Item label="Propietario" name="propietario">
                          <Input maxLength={120} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Divider orientation="left" style={{ fontSize: 13 }}>Servicios y Configuración</Divider>

                    <Row gutter={24}>
                      <Col xs={24} md={16}>
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
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item label="Activo" name="activo" valuePropName="checked">
                          <Switch />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Form.Item label="Notas" name="notas">
                      <TextArea rows={3} maxLength={500} showCount />
                    </Form.Item>
                  </Card>
                ),
              },

              // ──────────────────────────────────────────────────────────────
              // Tab 2: Documentos y Fotos
              // ──────────────────────────────────────────────────────────────
              {
                key: 'documentos',
                label: 'Documentos y Fotos',
                children: (
                  <Card>
                    {!isEditing && (
                      <div style={{ marginBottom: 16, padding: '8px 16px', background: '#fffbe6', borderRadius: 6, border: '1px solid #ffe58f' }}>
                        <Text type="warning">Guarda la unidad primero para poder subir fotos y documentos.</Text>
                      </div>
                    )}

                    <Divider orientation="left" style={{ fontSize: 13 }}>Fotos del Vehículo</Divider>

                    <Row gutter={32} style={{ marginBottom: 24 }}>
                      <Col>
                        <FotoUpload
                          label="Foto Frontal"
                          blobUrl={fotosBlob['foto_frontal']}
                          onUpload={(f) => handleFotoUpload('foto_frontal', f)}
                          onDelete={() => handleFotoDelete('foto_frontal')}
                          uploading={!!uploadingFoto['foto_frontal']}
                        />
                      </Col>
                      <Col>
                        <FotoUpload
                          label="Foto Lateral"
                          blobUrl={fotosBlob['foto_lateral']}
                          onUpload={(f) => handleFotoUpload('foto_lateral', f)}
                          onDelete={() => handleFotoDelete('foto_lateral')}
                          uploading={!!uploadingFoto['foto_lateral']}
                        />
                      </Col>
                      <Col>
                        <FotoUpload
                          label="Foto de Placa"
                          blobUrl={fotosBlob['foto_placa']}
                          onUpload={(f) => handleFotoUpload('foto_placa', f)}
                          onDelete={() => handleFotoDelete('foto_placa')}
                          uploading={!!uploadingFoto['foto_placa']}
                        />
                      </Col>
                    </Row>

                    <Divider orientation="left" style={{ fontSize: 13 }}>Tarjeta de Circulación</Divider>

                    <Row gutter={24} align="middle">
                      <Col xs={24} sm={6}>
                        <Form.Item label="No. Tarjeta de Circulación" name="tarjeta_circulacion">
                          <Input maxLength={50} />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={6}>
                        <Form.Item label="Fecha de Expedición" name="fecha_expedicion_tc">
                          <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={6}>
                        <Form.Item label="Fecha de Vencimiento" name="fecha_vencimiento_tc">
                          <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={6}>
                        <Form.Item label="Documento TC">
                          <DocUpload
                            label="Tarjeta de Circulación"
                            filename={record?.doc_tarjeta_circulacion}
                            onUpload={handleDocTCUpload}
                            onDelete={handleDocTCDelete}
                            uploading={!!uploadingDoc['tc']}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={24} sm={6}>
                        <Form.Item label="Comprobante de Pago TC">
                          <DocUpload
                            label="Comprobante de Pago TC"
                            filename={record?.doc_comprobante_pago_tc}
                            onUpload={handleComprobantePagoTCUpload}
                            onDelete={handleComprobantePagoTCDelete}
                            uploading={!!uploadingDoc['comprobante_tc']}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                ),
              },

              // ──────────────────────────────────────────────────────────────
              // Tab 3: Pólizas de Seguro
              // ──────────────────────────────────────────────────────────────
              {
                key: 'polizas',
                label: `Pólizas de Seguro${polizas.length ? ` (${polizas.length})` : ''}`,
                children: (
                  <Card>
                    {!isEditing ? (
                      <div style={{ padding: '8px 16px', background: '#fffbe6', borderRadius: 6, border: '1px solid #ffe58f' }}>
                        <Text type="warning">Guarda la unidad primero para poder agregar pólizas de seguro.</Text>
                      </div>
                    ) : (
                      <>
                        <div style={{ marginBottom: 16, textAlign: 'right' }}>
                          <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            onClick={() => {
                              setEditingPoliza(null);
                              setPolizaModalOpen(true);
                            }}
                          >
                            Nueva Póliza
                          </Button>
                        </div>
                        <Table
                          dataSource={polizas}
                          columns={polizasColumns}
                          rowKey="id"
                          size="small"
                          pagination={false}
                          locale={{ emptyText: 'Sin pólizas registradas' }}
                        />
                      </>
                    )}
                  </Card>
                ),
              },
            ]}
          />

          {/* Botones de acción globales */}
          <div style={{ textAlign: 'right', marginTop: 16 }}>
            <Space>
              <Button onClick={() => router.push('/unidades')}>Cancelar</Button>
              <Button type="primary" htmlType="submit" loading={saving}>
                {isEditing ? 'Actualizar Datos' : 'Guardar y Continuar'}
              </Button>
            </Space>
          </div>
        </Form>
      </div>

      {/* Modal de Póliza */}
      {id && (
        <PolizaModal
          open={polizaModalOpen}
          unidadId={id}
          poliza={editingPoliza}
          onClose={() => {
            setPolizaModalOpen(false);
            setEditingPoliza(null);
          }}
          onSaved={(p) => {
            setPolizas((prev) => {
              const idx = prev.findIndex((x) => x.id === p.id);
              if (idx >= 0) {
                const next = [...prev];
                next[idx] = p;
                return next;
              }
              return [...prev, p];
            });
          }}
        />
      )}
    </>
  );
};

export default UnidadForm;
