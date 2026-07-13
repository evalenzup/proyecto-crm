// pages/certificados/index.tsx
// Certificados de Aplicación de Plaguicidas — exclusivo NORTON FUMIGACIONES.
// Réplica del formato oficial (folio consecutivo, PDF idéntico al machote).
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert, Button, Card, Col, DatePicker, Divider, Form, Input, InputNumber,
  Modal, Popconfirm, Row, Select, Space, Table, Tooltip, message,
} from 'antd';
import {
  DeleteOutlined, EditOutlined, FilePdfOutlined, PlusOutlined, ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import debounce from 'lodash/debounce';

import { PageHeader } from '@/components/PageHeader';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';
import { useTableHeight } from '@/hooks/useTableHeight';
import certificadoService, { CertificadoServicio } from '@/services/certificadoService';
import { clienteService, ClienteOut } from '@/services/clienteService';

const EMPRESA_PERMITIDA = 'NORTON FUMIGACIONES';
// Gerente que firma los certificados (editable en el formulario)
const GERENTE_DEFAULT = 'Lic. Rodolfo Muñoz Barba';

const AREAS: [string, string][] = [
  ['habitaciones', 'No. Habitaciones'], ['closets', 'No. Closets'], ['banos', 'Baños'],
  ['cocinas', 'Cocinas'], ['comedores', 'Comedores'], ['barras', 'Barras'],
  ['almacenes', 'Almacenes'], ['oficinas', 'Oficinas'], ['exteriores', 'Exteriores'],
  ['estacionamientos', 'Estacionamientos'], ['otros', 'Otros'],
];

const PLAGAS: [string, string][] = [
  ['cucaracha', 'Cucaracha'], ['roedores', 'Roedores'], ['hormiga', 'Hormiga'],
  ['aracnidos', 'Arácnidos'], ['alacran', 'Alacrán'], ['grillo', 'Grillo'],
  ['ectoparasitos', 'Ectoparásitos'], ['termita', 'Termita'], ['plagas_jardin', 'Plagas de Jardín'],
  ['desinfecciones', 'Desinfecciones'], ['otros', 'Otros'],
];

const limpiar = (obj: Record<string, any>): Record<string, string> =>
  Object.fromEntries(
    Object.entries(obj || {}).filter(([, v]) => v != null && String(v).trim() !== '')
      .map(([k, v]) => [k, String(v).trim()])
  );

const CertificadosPage: React.FC = () => {
  const { containerRef, tableY } = useTableHeight();
  const { selectedEmpresaId, empresas } = useEmpresaSelector();

  const empresaActual = empresas?.find((e: any) => e.id === selectedEmpresaId);
  const habilitado = (empresaActual?.nombre_comercial || '').trim().toUpperCase() === EMPRESA_PERMITIDA;

  const [rows, setRows] = useState<CertificadoServicio[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sort, setSort] = useState<{ order_by?: string; order_dir?: 'asc' | 'desc' }>({});

  // Modal form
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<CertificadoServicio | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  // Cliente autocomplete (prellenado)
  const [clienteOpts, setClienteOpts] = useState<ClienteOut[]>([]);
  const buscarClientes = useMemo(() => debounce(async (v: string) => {
    if (!v || v.length < 3 || !selectedEmpresaId) { setClienteOpts([]); return; }
    try {
      setClienteOpts(await clienteService.buscarClientes(v, selectedEmpresaId, 'comercial'));
    } catch { /* interceptor notifica */ }
  }, 500), [selectedEmpresaId]);

  // PDF preview
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfTitulo, setPdfTitulo] = useState('');

  const fetchData = useCallback(async () => {
    if (!selectedEmpresaId || !habilitado) { setRows([]); setTotal(0); return; }
    setLoading(true);
    try {
      const data = await certificadoService.list({
        empresa_id: selectedEmpresaId,
        tipo: 'PLAGUICIDAS',
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
        order_by: sort.order_by,
        order_dir: sort.order_dir,
      });
      setRows(data.items);
      setTotal(data.total);
    } catch (e: any) {
      if (!e?._handled) message.error('Error al cargar los certificados');
    } finally {
      setLoading(false);
    }
  }, [selectedEmpresaId, habilitado, currentPage, pageSize, sort]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { setCurrentPage(1); }, [selectedEmpresaId]);

  const so = (key: string): 'ascend' | 'descend' | undefined =>
    sort.order_by === key ? (sort.order_dir === 'asc' ? 'ascend' : 'descend') : undefined;
  const handleTableChange = (_p: any, _f: any, sorter: any) => {
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    const next = s && s.order
      ? { order_by: String(s.columnKey ?? s.field), order_dir: (s.order === 'ascend' ? 'asc' : 'desc') as 'asc' | 'desc' }
      : {};
    if (next.order_by !== sort.order_by || next.order_dir !== sort.order_dir) {
      setSort(next); setCurrentPage(1);
    }
  };

  // ── Form helpers ────────────────────────────────────────────────────────────
  const abrir = (cert?: CertificadoServicio) => {
    setEditando(cert ?? null);
    form.resetFields();
    if (cert) {
      form.setFieldsValue({
        fecha: dayjs(cert.fecha),
        nombre_razon_social: cert.nombre_razon_social,
        domicilio: cert.domicilio,
        telefono: cert.telefono,
        actividad: cert.actividad,
        observaciones: cert.observaciones,
        gerente_nombre: cert.gerente_nombre,
        areas: cert.areas || {},
        plagas: cert.plagas || {},
        aplicaciones: cert.aplicaciones || {},
      });
    } else {
      form.setFieldsValue({ fecha: dayjs(), gerente_nombre: GERENTE_DEFAULT });
    }
    setModalOpen(true);
  };

  const prellenarCliente = (clienteId: string) => {
    const c = clienteOpts.find((x) => x.id === clienteId);
    if (!c) return;
    const dir = [
      c.serv_calle || c.calle,
      c.serv_numero_exterior || c.numero_exterior,
      c.serv_colonia || c.colonia,
      c.serv_codigo_postal || c.codigo_postal,
      c.serv_ciudad || c.ciudad,
    ].filter(Boolean).join(' ');
    form.setFieldsValue({
      cliente_id: c.id,
      nombre_razon_social: c.nombre_comercial,
      domicilio: dir || undefined,
      telefono: Array.isArray(c.telefono) ? c.telefono[0] : c.telefono,
      actividad: c.actividad || undefined,
    });
  };

  const guardar = async () => {
    try {
      const v = await form.validateFields();
      setSaving(true);
      const payload: any = {
        fecha: v.fecha.format('YYYY-MM-DD'),
        cliente_id: v.cliente_id || null,
        nombre_razon_social: v.nombre_razon_social,
        domicilio: v.domicilio || null,
        telefono: v.telefono || null,
        actividad: v.actividad || null,
        areas: limpiar(v.areas),
        plagas: limpiar(v.plagas),
        aplicaciones: limpiar(v.aplicaciones),
        observaciones: v.observaciones || null,
        gerente_nombre: v.gerente_nombre || null,
      };
      let cert: CertificadoServicio;
      if (editando) {
        cert = await certificadoService.update(editando.id, payload);
        message.success('Certificado actualizado');
      } else {
        cert = await certificadoService.create({
          ...payload,
          empresa_id: selectedEmpresaId!,
          tipo: 'PLAGUICIDAS',
          folio: v.folio || null,
        });
        message.success(`Certificado No. ${cert.folio} creado`);
      }
      setModalOpen(false);
      fetchData();
      verPdf(cert);
    } catch (e: any) {
      if (e?.errorFields) return; // validación del form
      if (!e?._handled) message.error('No se pudo guardar el certificado');
    } finally {
      setSaving(false);
    }
  };

  const eliminar = async (cert: CertificadoServicio) => {
    try {
      await certificadoService.remove(cert.id);
      message.success('Certificado eliminado');
      fetchData();
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo eliminar');
    }
  };

  const verPdf = async (cert: CertificadoServicio) => {
    try {
      const blob = await certificadoService.pdf(cert.id);
      setPdfUrl(window.URL.createObjectURL(blob));
      setPdfTitulo(`Certificado No. ${cert.folio}`);
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudo generar el PDF');
    }
  };

  const cerrarPdf = () => {
    if (pdfUrl) window.URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
  };

  // ── Columnas ────────────────────────────────────────────────────────────────
  const columns: ColumnsType<CertificadoServicio> = [
    { title: 'Folio', dataIndex: 'folio', key: 'folio', width: 90, sorter: true, sortOrder: so('folio'), render: (v) => <strong>No. {v}</strong> },
    { title: 'Fecha', dataIndex: 'fecha', key: 'fecha', width: 110, sorter: true, sortOrder: so('fecha'), render: (v) => dayjs(v).format('DD/MM/YYYY') },
    { title: 'Establecimiento', dataIndex: 'nombre_razon_social', key: 'nombre_razon_social', sorter: true, sortOrder: so('nombre_razon_social') },
    { title: 'Producto', key: 'producto', width: 160, render: (_, r) => r.aplicaciones?.producto || '—' },
    {
      title: 'Acciones', key: 'acc', width: 140,
      render: (_, r) => (
        <Space>
          <Tooltip title="Ver PDF"><Button type="link" icon={<FilePdfOutlined />} onClick={() => verPdf(r)} /></Tooltip>
          <Tooltip title="Editar"><Button type="link" icon={<EditOutlined />} onClick={() => abrir(r)} /></Tooltip>
          <Popconfirm title="¿Eliminar este certificado?" onConfirm={() => eliminar(r)} okText="Sí" cancelText="No">
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const gridCampos = (name: string, defs: [string, string][]) => (
    <Row gutter={[12, 0]}>
      {defs.map(([key, label]) => (
        <Col xs={12} sm={8} md={6} key={key}>
          <Form.Item label={label} name={[name, key]} style={{ marginBottom: 8 }}>
            <Input placeholder="X / valor" maxLength={30} />
          </Form.Item>
        </Col>
      ))}
    </Row>
  );

  return (
    <>
      <PageHeader
        title="Certificados de Aplicación de Plaguicidas"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchData}>Actualizar</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => abrir()} disabled={!habilitado}>
              Nuevo certificado
            </Button>
          </Space>
        }
      />
      <div className="app-content" ref={containerRef}>
        {!selectedEmpresaId ? (
          <Card><Alert type="info" showIcon message="Selecciona una empresa" /></Card>
        ) : !habilitado ? (
          <Card>
            <Alert
              type="warning" showIcon
              message="Certificados no disponibles para esta empresa"
              description={`El certificado de Aplicación de Plaguicidas solo está disponible para ${EMPRESA_PERMITIDA}.`}
            />
          </Card>
        ) : (
          <Table<CertificadoServicio>
            rowKey="id"
            size="small"
            columns={columns}
            dataSource={rows}
            loading={loading}
            scroll={{ x: 800, y: tableY }}
            onChange={handleTableChange}
            pagination={{
              current: currentPage,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (t) => `${t} certificados`,
              onChange: (p, s) => { setCurrentPage(p); if (s) setPageSize(s); },
            }}
            locale={{ emptyText: 'Sin certificados' }}
          />
        )}
      </div>

      {/* ── Modal de captura ── */}
      <Modal
        title={editando ? `Editar certificado No. ${editando.folio}` : 'Nuevo certificado'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={guardar}
        okText={editando ? 'Guardar' : 'Crear y ver PDF'}
        confirmLoading={saving}
        width={900}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Row gutter={12}>
            <Col xs={24} sm={8}>
              <Form.Item label="Fecha" name="fecha" rules={[{ required: true, message: 'Requerida' }]}>
                <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
              </Form.Item>
            </Col>
            {!editando && (
              <Col xs={24} sm={8}>
                <Form.Item label="Folio" name="folio" tooltip="Déjalo vacío para asignar el consecutivo automático">
                  <InputNumber style={{ width: '100%' }} min={1} placeholder="Automático" />
                </Form.Item>
              </Col>
            )}
            <Col xs={24} sm={8}>
              <Form.Item label="Prellenar desde cliente" name="cliente_id">
                <Select
                  showSearch allowClear
                  placeholder="Buscar cliente (3+ letras)…"
                  filterOption={false}
                  onSearch={buscarClientes}
                  onSelect={(v: string) => prellenarCliente(v)}
                  options={clienteOpts.map((c) => ({ value: c.id, label: c.nombre_comercial }))}
                  notFoundContent={null}
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" style={{ fontSize: 13, margin: '4px 0 12px' }}>Establecimiento</Divider>
          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item label="Nombre o Razón Social" name="nombre_razon_social" rules={[{ required: true, message: 'Requerido' }]}>
                <Input maxLength={255} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Actividad del Establecimiento" name="actividad">
                <Input maxLength={255} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={16}>
              <Form.Item label="Domicilio" name="domicilio">
                <Input maxLength={255} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item label="Teléfono" name="telefono">
                <Input maxLength={50} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" style={{ fontSize: 13, margin: '4px 0 12px' }}>Áreas tratadas</Divider>
          {gridCampos('areas', AREAS)}

          <Divider orientation="left" style={{ fontSize: 13, margin: '4px 0 12px' }}>Plagas sujetas a control</Divider>
          {gridCampos('plagas', PLAGAS)}

          <Divider orientation="left" style={{ fontSize: 13, margin: '4px 0 12px' }}>Aplicaciones</Divider>
          <Row gutter={12}>
            <Col xs={12} sm={6}><Form.Item label="Tiempo de Entrada" name={['aplicaciones', 'tiempo_entrada']} style={{ marginBottom: 8 }}><Input placeholder="2 HRS" /></Form.Item></Col>
            <Col xs={12} sm={6}><Form.Item label="Tiempo de Ventilación" name={['aplicaciones', 'tiempo_ventilacion']} style={{ marginBottom: 8 }}><Input placeholder="30 MIN" /></Form.Item></Col>
            <Col xs={12} sm={6}><Form.Item label="Aplicación Diurna" name={['aplicaciones', 'diurna']} style={{ marginBottom: 8 }}><Input placeholder="X" /></Form.Item></Col>
            <Col xs={12} sm={6}><Form.Item label="Aplicación Nocturna" name={['aplicaciones', 'nocturna']} style={{ marginBottom: 8 }}><Input placeholder="X" /></Form.Item></Col>
            <Col xs={12} sm={8}><Form.Item label="Producto Utilizado" name={['aplicaciones', 'producto']} style={{ marginBottom: 8 }}><Input placeholder="CIPERMETRINA" /></Form.Item></Col>
            <Col xs={12} sm={4}><Form.Item label="%" name={['aplicaciones', 'porcentaje']} style={{ marginBottom: 8 }}><Input placeholder="40" /></Form.Item></Col>
            <Col xs={24} sm={12}><Form.Item label="Antídoto" name={['aplicaciones', 'antidoto']} style={{ marginBottom: 8 }}><Input placeholder="SINTOMATICO" /></Form.Item></Col>
          </Row>

          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item label="Observaciones (una por línea)" name="observaciones">
                <Input.TextArea rows={3} placeholder={'VENCE: 31/07/2026\nSERVICIO MENSUAL\nNOM-256-SSA1-2012'} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Nombre del Gerente (firma)" name="gerente_nombre">
                <Input maxLength={255} placeholder="Lic. Nombre Apellido" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* ── Modal de PDF ── */}
      <Modal
        title={pdfTitulo}
        open={!!pdfUrl}
        onCancel={cerrarPdf}
        width="90%"
        style={{ top: 20, maxWidth: 1000 }}
        styles={{ body: { height: '80vh', padding: 0 } }}
        footer={[
          <Button key="close" onClick={cerrarPdf}>Cerrar</Button>,
          <Button key="dl" type="primary" icon={<FilePdfOutlined />} onClick={() => {
            if (!pdfUrl) return;
            const a = document.createElement('a');
            a.href = pdfUrl;
            a.download = `${pdfTitulo.replace(/\s+/g, '_').toLowerCase()}.pdf`;
            a.click();
          }}>Descargar</Button>,
        ]}
        destroyOnHidden
      >
        {pdfUrl && <iframe src={pdfUrl} title="Certificado" style={{ width: '100%', height: '100%', border: 'none' }} />}
      </Modal>
    </>
  );
};

export default CertificadosPage;
