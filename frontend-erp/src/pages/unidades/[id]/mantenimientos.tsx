'use client';
import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  DatePicker,
  Popconfirm,
  Space,
  Tooltip,
  Tag,
  message,
  Card,
  Descriptions,
  Spin,
  Typography,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';
import {
  unidadService,
  MantenimientoOut,
  MantenimientoCreate,
  TipoMantenimiento,
  UnidadOut,
} from '@/services/unidadService';
import { useTableHeight } from '@/hooks/useTableHeight';

const { TextArea } = Input;
const { Text } = Typography;

const TIPO_COLOR: Record<TipoMantenimiento, string> = {
  PREVENTIVO: 'blue',
  CORRECTIVO: 'volcano',
};

const MantenimientosPage: React.FC = () => {
  const router = useRouter();
  const { id: unidadId } = router.query as { id?: string };
  const { containerRef, tableY } = useTableHeight();

  const [unidad, setUnidad] = useState<UnidadOut | null>(null);
  const [mantenimientos, setMantenimientos] = useState<MantenimientoOut[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const fetchUnidad = useCallback(async () => {
    if (!unidadId) return;
    try {
      const data = await unidadService.getUnidad(unidadId);
      setUnidad(data);
    } catch {
      message.error('No se pudo cargar la unidad.');
    }
  }, [unidadId]);

  const fetchMantenimientos = useCallback(async () => {
    if (!unidadId) return;
    setLoading(true);
    try {
      const data = await unidadService.getMantenimientos(unidadId, {
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      });
      setMantenimientos(data.items);
      setTotal(data.total);
    } catch {
      message.error('Error al cargar mantenimientos.');
    } finally {
      setLoading(false);
    }
  }, [unidadId, page]);

  useEffect(() => {
    fetchUnidad();
  }, [fetchUnidad]);

  useEffect(() => {
    fetchMantenimientos();
  }, [fetchMantenimientos]);

  const openNew = () => {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ tipo: 'PREVENTIVO' });
    setModalOpen(true);
  };

  const openEdit = (record: MantenimientoOut) => {
    setEditingId(record.id);
    form.setFieldsValue({
      tipo: record.tipo,
      fecha_realizado: record.fecha_realizado ? dayjs(record.fecha_realizado) : null,
      kilometraje_actual: record.kilometraje_actual,
      descripcion: record.descripcion,
      costo: record.costo,
      proveedor: record.proveedor,
      proxima_fecha: record.proxima_fecha ? dayjs(record.proxima_fecha) : null,
      proximo_kilometraje: record.proximo_kilometraje,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!unidadId) return;
    try {
      const values = await form.validateFields();
      const payload: MantenimientoCreate = {
        tipo: values.tipo,
        fecha_realizado: values.fecha_realizado?.format('YYYY-MM-DD'),
        kilometraje_actual: values.kilometraje_actual ?? null,
        descripcion: values.descripcion ?? null,
        costo: values.costo ?? null,
        proveedor: values.proveedor ?? null,
        proxima_fecha: values.proxima_fecha?.format('YYYY-MM-DD') ?? null,
        proximo_kilometraje: values.proximo_kilometraje ?? null,
      };
      setSaving(true);
      if (editingId) {
        await unidadService.updateMantenimiento(unidadId, editingId, payload);
        message.success('Mantenimiento actualizado.');
      } else {
        await unidadService.createMantenimiento(unidadId, payload);
        message.success('Mantenimiento registrado.');
      }
      setModalOpen(false);
      fetchMantenimientos();
    } catch (err: any) {
      if (err?.errorFields) return;
      const detail = err?.response?.data?.detail || 'Error al guardar.';
      message.error(detail);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (record: MantenimientoOut) => {
    if (!unidadId) return;
    try {
      await unidadService.deleteMantenimiento(unidadId, record.id);
      message.success('Registro eliminado.');
      fetchMantenimientos();
    } catch {
      message.error('No se pudo eliminar.');
    }
  };

  const columns: ColumnsType<MantenimientoOut> = [
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      width: 120,
      render: (v: TipoMantenimiento) => <Tag color={TIPO_COLOR[v]}>{v}</Tag>,
    },
    {
      title: 'Fecha Realizado',
      dataIndex: 'fecha_realizado',
      width: 140,
      render: (v) => v || '—',
    },
    {
      title: 'Kilometraje',
      dataIndex: 'kilometraje_actual',
      width: 120,
      render: (v) => (v != null ? v.toLocaleString() + ' km' : '—'),
    },
    {
      title: 'Descripción',
      dataIndex: 'descripcion',
      ellipsis: true,
      render: (v) => v || '—',
    },
    {
      title: 'Costo',
      dataIndex: 'costo',
      width: 110,
      render: (v) => (v != null ? `$${Number(v).toFixed(2)}` : '—'),
    },
    {
      title: 'Proveedor',
      dataIndex: 'proveedor',
      width: 150,
      render: (v) => v || '—',
    },
    {
      title: 'Próxima Fecha',
      dataIndex: 'proxima_fecha',
      width: 140,
      render: (v) => v || '—',
    },
    {
      title: 'Próx. Km',
      dataIndex: 'proximo_kilometraje',
      width: 110,
      render: (v) => (v != null ? v.toLocaleString() + ' km' : '—'),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      width: 90,
      fixed: 'right' as const,
      render: (_, record) => (
        <Space>
          <Tooltip title="Editar">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => openEdit(record)}
            />
          </Tooltip>
          <Tooltip title="Eliminar">
            <Popconfirm
              title="¿Eliminar este registro?"
              onConfirm={() => handleDelete(record)}
              okText="Sí"
              cancelText="No"
            >
              <Button type="link" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">
            Mantenimientos
            {unidad && (
              <Text type="secondary" style={{ fontSize: '0.65em', marginLeft: 8 }}>
                {unidad.nombre}
                {unidad.placa ? ` — ${unidad.placa}` : ''}
              </Text>
            )}
          </h1>
        </div>
        <div className="app-page-header__right">
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => router.push('/unidades')}
            >
              Volver
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={openNew}
            >
              Registrar Mantenimiento
            </Button>
          </Space>
        </div>
      </div>

      <div className="app-content" ref={containerRef}>
        {unidad && (
          <Card size="small" variant="borderless" style={{ marginBottom: 8 }}>
            <Descriptions size="small" column={{ xs: 1, sm: 2, md: 4 }}>
              <Descriptions.Item label="Unidad">{unidad.nombre}</Descriptions.Item>
              <Descriptions.Item label="Placa">{unidad.placa || '—'}</Descriptions.Item>
              <Descriptions.Item label="Tipo">{unidad.tipo}</Descriptions.Item>
              <Descriptions.Item label="Estado">
                <Tag color={unidad.activo ? 'success' : 'default'}>
                  {unidad.activo ? 'Activo' : 'Inactivo'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        )}

        <Table<MantenimientoOut>
          rowKey="id"
          columns={columns}
          dataSource={mantenimientos}
          loading={loading}
          scroll={{ x: 1100, y: tableY }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            onChange: (p) => setPage(p),
            showSizeChanger: false,
          }}
          locale={{ emptyText: 'Sin registros de mantenimiento' }}
        />
      </div>

      <Modal
        title={editingId ? 'Editar Mantenimiento' : 'Registrar Mantenimiento'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        okText="Guardar"
        cancelText="Cancelar"
        confirmLoading={saving}
        destroyOnClose
        width={580}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="tipo" label="Tipo" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="PREVENTIVO">PREVENTIVO</Select.Option>
              <Select.Option value="CORRECTIVO">CORRECTIVO</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="fecha_realizado"
            label="Fecha Realizado"
            rules={[{ required: true, message: 'Se requiere la fecha' }]}
          >
            <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
          </Form.Item>

          <Form.Item name="kilometraje_actual" label="Kilometraje Actual (km)">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>

          <Form.Item name="descripcion" label="Descripción">
            <TextArea rows={3} />
          </Form.Item>

          <Form.Item name="costo" label="Costo ($)">
            <InputNumber style={{ width: '100%' }} min={0} precision={2} />
          </Form.Item>

          <Form.Item name="proveedor" label="Proveedor">
            <Input maxLength={150} />
          </Form.Item>

          <Form.Item name="proxima_fecha" label="Próxima Fecha">
            <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
          </Form.Item>

          <Form.Item name="proximo_kilometraje" label="Próximo Kilometraje (km)">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default MantenimientosPage;
