// pages/programacion-facturas/form/[[...id]].tsx
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import {
  Alert, Button, Card, Checkbox, Col, DatePicker, Divider, Form,
  Input, InputNumber, message, Modal, Row, Select, Space, Switch,
  Table, Tag, Tooltip, Typography,
} from 'antd';
import {
  DeleteOutlined, EditOutlined, PlusOutlined, SaveOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { debounce } from 'lodash';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import {
  programacionFacturaService,
  ConceptoPlantilla,
  PERIODICIDAD_LABELS,
  Periodicidad,
} from '@/services/programacionFacturaService';
import {
  searchClientes,
  searchProductosServicios,
  getFormasPago,
  getMetodosPago,
} from '@/services/facturaService';

const { Text } = Typography;
const { Option } = Select;

const USO_CFDI_OPTS = [
  { value: 'G01', label: 'G01 - Adquisición de mercancias' },
  { value: 'G02', label: 'G02 - Devoluciones, descuentos o bonificaciones' },
  { value: 'G03', label: 'G03 - Gastos en general' },
  { value: 'S01', label: 'S01 - Sin efectos fiscales' },
  { value: 'CP01', label: 'CP01 - Pagos' },
  { value: 'D01', label: 'D01 - Honorarios médicos, dentales y gastos hospitalarios' },
  { value: 'D10', label: 'D10 - Pagos por servicios educativos' },
];

const IVA_OPTS = [
  { value: '0', label: '0%' },
  { value: '0.08', label: '8%' },
  { value: '0.16', label: '16%' },
];

const RET_IVA_OPTS = [
  { value: '0', label: '0%' },
  { value: '0.106667', label: '10.6667% (2/3 IVA 16%)' },
  { value: '0.053333', label: '5.3333% (2/3 IVA 8%)' },
  { value: '0.04', label: '4% (Fletes)' },
  { value: '0.16', label: '16%' },
  { value: '0.08', label: '8%' },
];

const RET_ISR_OPTS = [
  { value: '0', label: '0%' },
  { value: '0.1', label: '10% (honorarios)' },
  { value: '0.0125', label: '1.25% (RESICO)' },
];

// ─────────────────────────────────────────────────────────────────────────────

type ConceptoRow = ConceptoPlantilla & { _key: string };

const ProgramacionFacturaForm: React.FC = () => {
  const router = useRouter();
  const { id: idParam } = router.query;
  const id = Array.isArray(idParam) ? idParam[0] : idParam;
  const isEdit = Boolean(id);

  const { selectedEmpresaId, empresas } = useEmpresaSelector();

  const [form] = Form.useForm();
  const [conceptoForm] = Form.useForm();

  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [conceptos, setConceptos] = useState<ConceptoRow[]>([]);
  const [conceptoModalOpen, setConceptoModalOpen] = useState(false);
  const [editingConcepto, setEditingConcepto] = useState<ConceptoRow | null>(null);

  const [clienteOpts, setClienteOpts] = useState<{ label: string; value: string }[]>([]);
  const [psOpts, setPsOpts] = useState<{ label: string; value: string; data?: any }[]>([]);
  const [formasPago, setFormasPago] = useState<{ value: string; label: string }[]>([]);
  const [metodosPago, setMetodosPago] = useState<{ value: string; label: string }[]>([]);

  const empresaId: string | undefined = Form.useWatch('empresa_id', form) || selectedEmpresaId || undefined;

  // ── Cargar catálogos ───────────────────────────────────────────────────────
  useEffect(() => {
    getFormasPago().then((data: any[]) =>
      setFormasPago(data.map((d: any) => ({ value: d.id ?? d.clave, label: `${d.id ?? d.clave} - ${d.descripcion ?? d.nombre}` })))
    ).catch(() => {});
    getMetodosPago().then((data: any[]) =>
      setMetodosPago(data.map((d: any) => ({ value: d.id ?? d.clave, label: `${d.id ?? d.clave} - ${d.descripcion ?? d.nombre}` })))
    ).catch(() => {});
  }, []);

  // ── Cargar registro existente (modo edición) ───────────────────────────────
  useEffect(() => {
    if (!id) {
      form.setFieldsValue({ empresa_id: selectedEmpresaId, moneda: 'MXN', serie: 'A', periodicidad: 'mensual', auto_timbrar: false, auto_enviar: false });
      return;
    }
    setLoading(true);
    programacionFacturaService.get(id).then(prog => {
      form.setFieldsValue({
        ...prog,
        proxima_ejecucion: prog.proxima_ejecucion ? dayjs(prog.proxima_ejecucion) : null,
        fecha_fin: prog.fecha_fin ? dayjs(prog.fecha_fin) : null,
        emails_destino: (prog.emails_destino || []).join('\n'),
      });
      setConceptos((prog.conceptos || []).map((c, i) => ({ ...c, _key: `loaded-${i}` })));
      // Pre-cargar cliente en opts
      if (prog.cliente_nombre) {
        setClienteOpts([{ value: prog.cliente_id, label: prog.cliente_nombre }]);
      }
    }).catch(() => message.error('No se pudo cargar la programación'))
      .finally(() => setLoading(false));
  }, [id]);

  // ── Búsqueda de clientes ───────────────────────────────────────────────────
  const buscarClientes = useMemo(() =>
    debounce(async (q: string) => {
      if (!empresaId || q.length < 3) { setClienteOpts([]); return; }
      try {
        const data = await searchClientes(q, empresaId);
        setClienteOpts((data || []).map((c: any) => ({
          value: c.id,
          label: c.nombre_comercial ?? c.razon_social ?? c.nombre ?? 'Cliente',
        })));
      } catch { setClienteOpts([]); }
    }, 350), [empresaId]);

  // ── Búsqueda de productos/servicios (para conceptos) ──────────────────────
  const buscarPS = useMemo(() =>
    debounce(async (q: string) => {
      if (!empresaId || q.length < 2) { setPsOpts([]); return; }
      try {
        const data = await searchProductosServicios(empresaId, q);
        setPsOpts((data?.items ?? data ?? []).map((p: any) => ({
          value: p.id,
          label: p.nombre ?? p.descripcion,
          data: p,
        })));
      } catch { setPsOpts([]); }
    }, 350), [empresaId]);

  const onSelectPS = useCallback((val: string, opt: any) => {
    const p = opt?.data;
    if (!p) return;
    conceptoForm.setFieldsValue({
      clave_producto:  p.clave_producto ?? p.clave_prod_serv ?? '',
      clave_unidad:    p.clave_unidad ?? '',
      descripcion:     p.nombre ?? p.descripcion ?? '',
      valor_unitario:  p.precio_unitario ?? p.precio ?? 0,
      iva_tasa:        p.iva_tasa != null ? String(p.iva_tasa) : '0.16',
      ret_iva_tasa:    p.ret_iva_tasa != null ? String(p.ret_iva_tasa) : '0',
      ret_isr_tasa:    p.ret_isr_tasa != null ? String(p.ret_isr_tasa) : '0',
    });
  }, [conceptoForm]);

  // ── Abrir modal concepto ───────────────────────────────────────────────────
  const abrirConcepto = (row?: ConceptoRow) => {
    setEditingConcepto(row ?? null);
    setConceptoModalOpen(true);
    if (row) {
      conceptoForm.setFieldsValue({
        ...row,
        iva_tasa:     row.iva_tasa     ?? '0.16',
        ret_iva_tasa: row.ret_iva_tasa ?? '0',
        ret_isr_tasa: row.ret_isr_tasa ?? '0',
        cantidad:     parseFloat(row.cantidad ?? '1'),
        valor_unitario: parseFloat(row.valor_unitario ?? '0'),
        descuento:    parseFloat(row.descuento ?? '0'),
      });
    } else {
      conceptoForm.resetFields();
      conceptoForm.setFieldsValue({ cantidad: 1, descuento: 0, iva_tasa: '0.16', ret_iva_tasa: '0', ret_isr_tasa: '0' });
    }
  };

  const guardarConcepto = async () => {
    try {
      const vals = await conceptoForm.validateFields();
      const nuevo: ConceptoRow = {
        _key:            editingConcepto?._key ?? `c-${Date.now()}`,
        tipo:            null,
        producto_servicio_id: null,
        clave_producto:  vals.clave_producto,
        clave_unidad:    vals.clave_unidad,
        descripcion:     vals.descripcion,
        cantidad:        String(vals.cantidad ?? 1),
        valor_unitario:  String(vals.valor_unitario ?? 0),
        descuento:       String(vals.descuento ?? 0),
        iva_tasa:        vals.iva_tasa ?? '0',
        ret_iva_tasa:    vals.ret_iva_tasa ?? '0',
        ret_isr_tasa:    vals.ret_isr_tasa ?? '0',
      };
      if (editingConcepto) {
        setConceptos(prev => prev.map(c => c._key === editingConcepto._key ? nuevo : c));
      } else {
        setConceptos(prev => [...prev, nuevo]);
      }
      setConceptoModalOpen(false);
    } catch { }
  };

  // ── Columnas tabla conceptos ───────────────────────────────────────────────
  const conceptosCols: ColumnsType<ConceptoRow> = [
    { title: 'Descripción', dataIndex: 'descripcion', key: 'desc', ellipsis: true },
    { title: 'Cantidad', dataIndex: 'cantidad', key: 'cant', width: 90, align: 'right' },
    { title: 'P.Unit.', dataIndex: 'valor_unitario', key: 'pu', width: 110, align: 'right',
      render: (v: string) => `$${parseFloat(v).toFixed(2)}` },
    { title: 'IVA', dataIndex: 'iva_tasa', key: 'iva', width: 70, align: 'center',
      render: (v: string) => v ? `${(parseFloat(v) * 100).toFixed(0)}%` : '—' },
    {
      title: '', key: 'acc', width: 80,
      render: (_, row) => (
        <Space size={0}>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => abrirConcepto(row)} />
          <Button type="link" size="small" danger icon={<DeleteOutlined />}
            onClick={() => setConceptos(prev => prev.filter(c => c._key !== row._key))} />
        </Space>
      ),
    },
  ];

  // ── Guardar formulario ────────────────────────────────────────────────────
  const onFinish = async (vals: any) => {
    if (conceptos.length === 0) {
      message.error('Agrega al menos un concepto');
      return;
    }
    setSaving(true);
    try {
      const emailsRaw: string = vals.emails_destino ?? '';
      const emails = emailsRaw.split(/[\n,;]+/).map((e: string) => e.trim()).filter(Boolean);

      const payload = {
        empresa_id:          vals.empresa_id ?? selectedEmpresaId,
        cliente_id:          vals.cliente_id,
        nombre:              vals.nombre ?? null,
        serie:               vals.serie ?? 'A',
        tipo_comprobante:    vals.tipo_comprobante ?? 'I',
        forma_pago:          vals.forma_pago ?? null,
        metodo_pago:         vals.metodo_pago ?? null,
        uso_cfdi:            vals.uso_cfdi ?? null,
        moneda:              vals.moneda ?? 'MXN',
        lugar_expedicion:    vals.lugar_expedicion ?? null,
        condiciones_pago:    vals.condiciones_pago ?? null,
        observaciones:       vals.observaciones ?? null,
        conceptos:           conceptos.map(({ _key, ...rest }) => rest),
        periodicidad:        vals.periodicidad,
        proxima_ejecucion:   vals.proxima_ejecucion?.format('YYYY-MM-DD'),
        fecha_fin:           vals.fecha_fin?.format('YYYY-MM-DD') ?? null,
        auto_timbrar:        vals.auto_timbrar ?? false,
        auto_enviar:         vals.auto_enviar ?? false,
        emails_destino:      emails,
      };

      if (isEdit) {
        await programacionFacturaService.update(id!, payload);
        message.success('Programación actualizada');
      } else {
        await programacionFacturaService.create(payload as any);
        message.success('Programación creada');
      }
      router.push('/programacion-facturas');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(typeof detail === 'string' ? detail : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const autoEnviar = Form.useWatch('auto_enviar', form);

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">
            {isEdit ? 'Editar Programación' : 'Nueva Programación de Factura'}
          </h1>
        </div>
        <div className="app-page-header__right">
          <Button onClick={() => router.back()}>Cancelar</Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={() => form.submit()}
          >
            {isEdit ? 'Guardar cambios' : 'Crear programación'}
          </Button>
        </div>
      </div>

      <div className="app-content">
        <Form form={form} layout="vertical" onFinish={onFinish} disabled={loading}>
          <Row gutter={16}>
            {/* ── Columna izquierda ── */}
            <Col xs={24} lg={16}>

              {/* Datos fiscales */}
              <Card title="Datos fiscales" size="small" style={{ marginBottom: 12 }}>
                <Row gutter={12}>
                  <Col xs={24} sm={12}>
                    <Form.Item label="Empresa" name="empresa_id" initialValue={selectedEmpresaId}>
                      <Select disabled placeholder="Empresa">
                        {empresas.map(e => (
                          <Option key={e.id} value={e.id}>
                            {e.nombre_comercial || e.nombre}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item label="Cliente" name="cliente_id"
                      rules={[{ required: true, message: 'Selecciona un cliente' }]}>
                      <Select
                        showSearch filterOption={false} placeholder="Buscar cliente (min 3 caracteres)"
                        onSearch={buscarClientes}
                        options={clienteOpts}
                        notFoundContent={null}
                      />
                    </Form.Item>
                  </Col>
                </Row>
                <Row gutter={12}>
                  <Col xs={12} sm={6}>
                    <Form.Item label="Serie" name="serie" initialValue="A">
                      <Input maxLength={10} />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={6}>
                    <Form.Item label="Moneda" name="moneda" initialValue="MXN">
                      <Select>
                        <Option value="MXN">MXN</Option>
                        <Option value="USD">USD</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={6}>
                    <Form.Item label="Método de pago" name="metodo_pago">
                      <Select allowClear options={metodosPago} placeholder="PUE / PPD" />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={6}>
                    <Form.Item label="Forma de pago" name="forma_pago">
                      <Select showSearch allowClear options={formasPago} placeholder="Forma de pago" />
                    </Form.Item>
                  </Col>
                </Row>
                <Row gutter={12}>
                  <Col xs={12} sm={8}>
                    <Form.Item label="Uso CFDI" name="uso_cfdi">
                      <Select showSearch allowClear options={USO_CFDI_OPTS} placeholder="Uso CFDI" />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={8}>
                    <Form.Item label="Lugar expedición (CP)" name="lugar_expedicion">
                      <Input maxLength={5} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Form.Item label="Condiciones de pago" name="condiciones_pago">
                      <Input placeholder="ej. Neto 30 días" />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item label="Observaciones" name="observaciones">
                  <Input.TextArea rows={2} />
                </Form.Item>
              </Card>

              {/* Conceptos */}
              <Card
                title="Conceptos"
                size="small"
                style={{ marginBottom: 12 }}
                extra={
                  <Button
                    size="small" type="primary" ghost
                    icon={<PlusOutlined />}
                    onClick={() => abrirConcepto()}
                    disabled={!empresaId}
                  >
                    Agregar
                  </Button>
                }
              >
                {conceptos.length === 0 ? (
                  <Text type="secondary" style={{ display: 'block', padding: '16px 0', textAlign: 'center' }}>
                    Sin conceptos — agrega al menos uno
                  </Text>
                ) : (
                  <Table<ConceptoRow>
                    rowKey="_key"
                    columns={conceptosCols}
                    dataSource={conceptos}
                    pagination={false}
                    size="small"
                    scroll={{ x: 500 }}
                  />
                )}
              </Card>
            </Col>

            {/* ── Columna derecha ── */}
            <Col xs={24} lg={8}>

              {/* Identificación */}
              <Card title="Identificación" size="small" style={{ marginBottom: 12 }}>
                <Form.Item label="Nombre / etiqueta" name="nombre"
                  tooltip="Descripción corta para identificar esta programación en la lista">
                  <Input placeholder="ej. Servicio mensual - Empresa ABC" maxLength={120} />
                </Form.Item>
              </Card>

              {/* Programación */}
              <Card title="Programación" size="small" style={{ marginBottom: 12 }}>
                <Form.Item label="Periodicidad" name="periodicidad" initialValue="mensual"
                  rules={[{ required: true }]}>
                  <Select>
                    {(Object.keys(PERIODICIDAD_LABELS) as Periodicidad[]).map(k => (
                      <Option key={k} value={k}>{PERIODICIDAD_LABELS[k]}</Option>
                    ))}
                  </Select>
                </Form.Item>
                <Form.Item label="Primera ejecución" name="proxima_ejecucion"
                  rules={[{ required: true, message: 'Selecciona la fecha de inicio' }]}>
                  <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
                </Form.Item>
                <Form.Item label="Fecha fin (opcional)" name="fecha_fin"
                  tooltip="Deja vacío para repetir indefinidamente">
                  <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
                </Form.Item>
              </Card>

              {/* Automatización */}
              <Card title="Automatización" size="small" style={{ marginBottom: 12 }}>
                <Form.Item name="auto_timbrar" valuePropName="checked" initialValue={false}>
                  <Switch checkedChildren="Timbrar automático" unCheckedChildren="No timbrar" />
                </Form.Item>
                <Form.Item name="auto_enviar" valuePropName="checked" initialValue={false}>
                  <Switch checkedChildren="Enviar por email" unCheckedChildren="No enviar" />
                </Form.Item>

                {autoEnviar && (
                  <Form.Item
                    label="Destinatarios"
                    name="emails_destino"
                    rules={[{
                      validator: (_, v) => {
                        if (!v || !v.trim()) return Promise.reject('Agrega al menos un email');
                        return Promise.resolve();
                      },
                    }]}
                    tooltip="Un email por línea, o separados por coma"
                  >
                    <Input.TextArea
                      rows={3}
                      placeholder={"cliente@empresa.com\npagos@empresa.com"}
                    />
                  </Form.Item>
                )}

                <Alert
                  type="info"
                  showIcon
                  style={{ marginTop: 8 }}
                  message={
                    <Text style={{ fontSize: 12 }}>
                      El cron corre diariamente a las 3:05 AM. También puedes ejecutar
                      cualquier programación manualmente desde la lista.
                    </Text>
                  }
                />
              </Card>
            </Col>
          </Row>
        </Form>

        {/* Modal de concepto */}
        <Modal
          title={editingConcepto ? 'Editar Concepto' : 'Agregar Concepto'}
          open={conceptoModalOpen}
          onOk={guardarConcepto}
          onCancel={() => setConceptoModalOpen(false)}
          width="min(95vw, 760px)"
          okText="Guardar"
          cancelText="Cancelar"
          destroyOnHidden
        >
          <Form form={conceptoForm} layout="vertical">
            <Form.Item label="Producto/Servicio del catálogo" name="ps_lookup">
              <Select
                showSearch filterOption={false} placeholder="Buscar en catálogo…"
                onSearch={buscarPS}
                options={psOpts}
                onSelect={onSelectPS}
                notFoundContent={null}
                disabled={!empresaId}
              />
            </Form.Item>
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item label="Clave SAT" name="clave_producto"
                  rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Clave Unidad SAT" name="clave_unidad"
                  rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="Descripción" name="descripcion" rules={[{ required: true }]}>
              <Input.TextArea rows={2} />
            </Form.Item>
            <Row gutter={12}>
              <Col span={8}>
                <Form.Item label="Cantidad" name="cantidad" rules={[{ required: true }]}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Valor Unitario" name="valor_unitario" rules={[{ required: true }]}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Descuento" name="descuento" initialValue={0}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={12}>
              <Col span={8}>
                <Form.Item label="IVA" name="iva_tasa" initialValue="0.16">
                  <Select options={IVA_OPTS} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Ret. IVA" name="ret_iva_tasa" initialValue="0">
                  <Select options={RET_IVA_OPTS} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="Ret. ISR" name="ret_isr_tasa" initialValue="0">
                  <Select options={RET_ISR_OPTS} />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </Modal>
      </div>
    </>
  );
};

export default ProgramacionFacturaForm;
