'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  Table, Card, Row, Col, Statistic, DatePicker, Select, Button, Tag, Space,
  Modal, Form, message, Result, Typography, Popconfirm,
} from 'antd';
import { CheckCircleOutlined, DollarOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { PageHeader } from '@/components/PageHeader';
import { useAuth } from '@/context/AuthContext';
import { useEmpresaContext } from '@/context/EmpresaContext';
import {
  IngresoRow, IngresosResumen, obtenerIngresos, marcarCobro, canVerIngresos,
} from '@/services/ingresosNoFacturadosService';
import { normalizeHttpError } from '@/utils/httpError';

const { Text } = Typography;

const money = (v?: number | null) =>
  v != null ? `$${Number(v).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '$0.00';

const ESTADO_TAG: Record<string, string> = {
  COMPLETADO: 'green',
  EN_PROGRESO: 'blue',
};

const IngresosNoFacturadosPage: React.FC = () => {
  const { user } = useAuth();
  const { selectedEmpresaId } = useEmpresaContext();

  const [mes, setMes] = useState<Dayjs | null>(dayjs());
  const [cobradoFilter, setCobradoFilter] = useState<boolean | undefined>(undefined);
  const [rows, setRows] = useState<IngresoRow[]>([]);
  const [resumen, setResumen] = useState<IngresosResumen | null>(null);
  const [loading, setLoading] = useState(false);
  const [cobro, setCobro] = useState<IngresoRow | null>(null);

  const permitido = canVerIngresos(user);

  const cargar = useCallback(() => {
    if (!selectedEmpresaId || !permitido) return;
    setLoading(true);
    obtenerIngresos({
      empresa_id: selectedEmpresaId,
      anio: mes ? mes.year() : undefined,
      mes: mes ? mes.month() + 1 : undefined,
      cobrado: cobradoFilter,
    })
      .then((r) => { setRows(r.items); setResumen(r.resumen); })
      .catch((e) => message.error(normalizeHttpError(e)))
      .finally(() => setLoading(false));
  }, [selectedEmpresaId, permitido, mes, cobradoFilter]);

  useEffect(() => { cargar(); }, [cargar]);

  if (!permitido) {
    return (
      <>
        <PageHeader title="Ingresos no facturados" />
        <div className="app-content">
          <Result status="403" title="Sin acceso"
            subTitle="No tienes permiso para ver este módulo. Solicítalo al administrador." />
        </div>
      </>
    );
  }

  const columns = [
    { title: 'Orden', dataIndex: 'folio_os', key: 'folio', width: 110 },
    {
      title: 'Fecha', dataIndex: 'fecha_programada', key: 'fecha', width: 110,
      render: (v: string) => dayjs(v).format('DD/MM/YYYY'),
    },
    { title: 'Cliente', dataIndex: 'cliente_nombre', key: 'cliente' },
    {
      title: 'Estado orden', dataIndex: 'estado', key: 'estado', width: 130,
      render: (v: string) => <Tag color={ESTADO_TAG[v] || 'default'}>{v}</Tag>,
    },
    {
      title: 'Importe', dataIndex: 'precio_acordado', key: 'precio', width: 120, align: 'right' as const,
      render: (v: number | null) => money(v),
    },
    {
      title: 'Cobro', key: 'cobro', width: 160,
      render: (_: unknown, r: IngresoRow) =>
        r.cobrado ? (
          <Space direction="vertical" size={0}>
            <Tag icon={<CheckCircleOutlined />} color="success">Cobrado</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {r.fecha_cobro ? dayjs(r.fecha_cobro).format('DD/MM/YY') : ''}{r.forma_cobro ? ` · ${r.forma_cobro}` : ''}
            </Text>
          </Space>
        ) : (
          <Tag color="warning">Pendiente</Tag>
        ),
    },
    {
      title: '', key: 'acc', width: 130,
      render: (_: unknown, r: IngresoRow) =>
        r.cobrado ? (
          <Popconfirm
            title="Regresar a no pagado"
            description="¿Seguro que quieres quitar el cobro de esta orden? Quedará registrado en la auditoría."
            okText="Sí, quitar" cancelText="Cancelar"
            onConfirm={() => quitarCobro(r)}
          >
            <Button size="small">Quitar cobro</Button>
          </Popconfirm>
        ) : (
          <Button size="small" type="primary" onClick={() => setCobro(r)}>Marcar cobrado</Button>
        ),
    },
  ];

  const quitarCobro = async (r: IngresoRow) => {
    try {
      await marcarCobro(r.orden_id, { cobrado: false });
      message.success('Cobro retirado');
      cargar();
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e));
    }
  };

  return (
    <>
      <PageHeader title="Ingresos no facturados" />
      <div className="app-content">
        {!selectedEmpresaId ? (
          <Text type="secondary">Selecciona una empresa para ver sus ingresos no facturados.</Text>
        ) : (
          <>
            <Row gutter={12} style={{ marginBottom: 12 }}>
              <Col xs={24} sm={8}>
                <Card size="small">
                  <Statistic title="No facturado" value={Number(resumen?.total_no_facturado || 0)}
                    prefix={<DollarOutlined />} precision={2}
                    valueStyle={{ color: '#1677ff' }} />
                  <Text type="secondary">{resumen?.num_ordenes || 0} órdenes</Text>
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card size="small">
                  <Statistic title="Cobrado" value={Number(resumen?.total_cobrado || 0)}
                    precision={2} valueStyle={{ color: '#3f8600' }} />
                  <Text type="secondary">{resumen?.num_cobradas || 0} cobradas</Text>
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card size="small">
                  <Statistic title="Pendiente por cobrar" value={Number(resumen?.total_pendiente || 0)}
                    precision={2} valueStyle={{ color: '#cf1322' }} />
                </Card>
              </Col>
            </Row>

            <Space style={{ marginBottom: 12 }} wrap>
              <DatePicker picker="month" value={mes} onChange={setMes} placeholder="Todos los meses" />
              <Select
                style={{ width: 180 }} value={cobradoFilter} onChange={setCobradoFilter}
                allowClear placeholder="Cobro (todos)"
                options={[{ value: false, label: 'Solo pendientes' }, { value: true, label: 'Solo cobrados' }]}
              />
              <Button onClick={cargar}>Actualizar</Button>
            </Space>

            <Table
              rowKey="orden_id" size="small" loading={loading} columns={columns} dataSource={rows}
              pagination={{ pageSize: 25 }}
              locale={{ emptyText: 'No hay órdenes sin factura en este periodo.' }}
            />
          </>
        )}
      </div>

      <CobroModal
        row={cobro}
        onClose={() => setCobro(null)}
        onDone={() => { setCobro(null); cargar(); }}
      />
    </>
  );
};

const CobroModal: React.FC<{
  row: IngresoRow | null;
  onClose: () => void;
  onDone: () => void;
}> = ({ row, onClose, onDone }) => {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (row) form.setFieldsValue({ fecha_cobro: dayjs(), forma_cobro: undefined });
  }, [row, form]);

  const submit = async () => {
    const v = await form.validateFields();
    if (!row) return;
    setSaving(true);
    try {
      await marcarCobro(row.orden_id, {
        cobrado: true,
        fecha_cobro: (v.fecha_cobro as Dayjs).format('YYYY-MM-DD'),
        forma_cobro: v.forma_cobro || null,
      });
      message.success('Orden marcada como cobrada');
      onDone();
    } catch (e: any) {
      if (!e?._handled) message.error(normalizeHttpError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={!!row} onCancel={onClose} onOk={submit} confirmLoading={saving}
      title={row ? `Marcar cobrado — ${row.folio_os}` : 'Marcar cobrado'} okText="Confirmar cobro">
      <Form form={form} layout="vertical">
        <Form.Item name="fecha_cobro" label="Fecha de cobro" rules={[{ required: true }]}>
          <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
        </Form.Item>
        <Form.Item name="forma_cobro" label="Forma de cobro (opcional)">
          <Select allowClear placeholder="Selecciona"
            options={['Efectivo', 'Transferencia', 'Cheque', 'Depósito', 'Tarjeta', 'Otro']
              .map((x) => ({ value: x, label: x }))} />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default IngresosNoFacturadosPage;
