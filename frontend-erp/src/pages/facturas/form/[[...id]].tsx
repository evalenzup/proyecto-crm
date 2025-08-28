// src/pages/facturas/form/[[...id]].tsx
'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/axios';
import {
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Spin,
  Card,
  message,
  Space,
  Typography,
  Divider,
  DatePicker,
  Checkbox,
  Row,
  Col,
  Popconfirm,
  Modal,
  Table,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  StopOutlined,
  PlusCircleOutlined,
  EditOutlined,
  FilePdfOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import debounce from 'lodash/debounce';
import { Breadcrumbs } from '@/components/Breadcrumb';

const { Text } = Typography;

/* ──────────────────────────────────────────────────────────────
 * Tipos
 * ──────────────────────────────────────────────────────────── */
type EstatusCFDI = 'BORRADOR' | 'TIMBRADA' | 'CANCELADA';
type StatusPago = 'PAGADA' | 'NO_PAGADA';

interface ConceptoForm {
  ps_lookup?: any;
  clave_producto?: string;
  clave_unidad?: string;
  descripcion?: string;
  cantidad?: number;
  valor_unitario?: number;
  descuento?: number | null;
  iva_tasa?: number | null;
  ret_iva_tasa?: number | null;
  ret_isr_tasa?: number | null;
}

interface FacturaOut {
  id: string;
  empresa_id: string;
  cliente_id: string | null;
  serie: string | null;
  folio: number;
  estatus: EstatusCFDI;
  status_pago: StatusPago;
  motivo_cancelacion?: string | null;
  folio_fiscal_sustituto?: string | null;
  moneda: 'MXN' | 'USD';
  tipo_cambio?: number | null;
  metodo_pago?: string | null;
  forma_pago?: string | null;
  uso_cfdi?: string | null;
  lugar_expedicion?: string | null;
  condiciones_pago?: string | null;
  cfdi_relacionados_tipo?: string | null;
  cfdi_relacionados?: string | null;
  folio_fiscal?: string | null; // UUID
  subtotal?: number;
  impuestos_trasladados?: number;
  impuestos_retenidos?: number;
  total?: number;
  creado_en: string;
  actualizado_en: string;
  conceptos: (Required<ConceptoForm> & { id: string; descripcion: string })[];
  fecha_emision?: string | null;
  fecha_timbrado?: string | null;
  fecha_pago?: string | null;
  fecha_cobro?: string | null;

  cliente?: {
    id: string;
    nombre_comercial?: string;
    razon_social?: string;
    nombre?: string;
    rfc?: string;
    regimen_fiscal?: string;
    codigo_postal?: string;
    dias_credito?: number;
    tipo_persona?: 'FISICA' | 'MORAL';
    extranjero?: boolean;
  } | null;
}

/* ──────────────────────────────────────────────────────────────
 * Utils
 * ──────────────────────────────────────────────────────────── */
const formatDateTj = (iso?: string) => {
  if (!iso) return '';
  const utc = iso.endsWith('Z') ? iso : `${iso}Z`;
  return new Date(utc).toLocaleString('es-MX', {
    timeZone: 'America/Tijuana',
    dateStyle: 'short',
    timeStyle: 'medium',
  });
};

const lv = (v: any) => (typeof v === 'object' && v !== null ? v.value : v);

/* Retenciones — opciones más comunes y permitidas en práctica */
const RET_IVA_OPTS = [
  { value: 0, label: '0%' },
  { value: 0.106667, label: '10.6667% (2/3 del IVA)' },
];
const RET_ISR_OPTS = [
  { value: 0, label: '0%' },
  { value: 0.10, label: '10% (honorarios/arrendamiento)' },
  { value: 0.0125, label: '1.25% (RESICO PF retenido por PM)' },
];

/* ──────────────────────────────────────────────────────────────
 * Página
 * ──────────────────────────────────────────────────────────── */
const FacturaFormPage: React.FC = () => {
  const router = useRouter();
  const raw = router.query.id;
  const id = Array.isArray(raw) ? raw[0] : raw;

  const [form] = Form.useForm();
  const [conceptoForm] = Form.useForm();
  const [psForm] = Form.useForm();

  // Modal Cancelación
  const [cancelForm] = Form.useForm();
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelSubmitting, setCancelSubmitting] = useState(false);

  // Emisor
  const [rfcEmisor, setRfcEmisor] = useState<string>('');

  // Estado conceptos (tabla)
  const [conceptos, setConceptos] = useState<ConceptoForm[]>([]);
  const [isConceptoModalOpen, setIsConceptoModalOpen] = useState(false);
  const [editingConcepto, setEditingConcepto] = useState<ConceptoForm | null>(null);
  const [editingConceptoIndex, setEditingConceptoIndex] = useState<number | null>(null);

  // Loading / estado UI
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [accionLoading, setAccionLoading] = useState({ timbrar: false, cancelar: false });

  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);
  const [estatusCFDI, setEstatusCFDI] = useState<EstatusCFDI>('BORRADOR');
  const [statusPago, setStatusPago] = useState<StatusPago>('NO_PAGADA');

  // Catálogos CFDI / regimen
  const [metodosPago, setMetodosPago] = useState<{ value: string; label: string }[]>([]);
  const [formasPago, setFormasPago] = useState<{ value: string; label: string }[]>([]);
  const [usosCfdi, setUsosCfdi] = useState<{ value: string; label: string }[]>([]);
  const [regimenes, setRegimenes] = useState<{ value: string; label: string }[]>([]);
  const [tiposRelacion, setTiposRelacion] = useState<{ value: string; label: string }[]>([]);
  const [motivosCancel, setMotivosCancel] = useState<{ value: string; label: string }[]>([]); // NEW

  // Empresa/cliente
  const [empresas, setEmpresas] = useState<{ label: string; value: string }[]>([]);
  const [clienteOpts, setClienteOpts] = useState<{ label: string; value: string }[]>([]);
  const [diasCreditoCliente, setDiasCreditoCliente] = useState<number>(0);

  // Productos/Servicios existentes (autocomplete por empresa)
  const [psOpts, setPsOpts] = useState<{ value: string; label: string; meta: any }[]>([]);
  const [unidadOpts, setUnidadOpts] = useState<{ value: string; label: string }[]>([]);

  // Catálogo SAT de claves producto (para el modal de ALTA)
  const [claveSatOpts, setClaveSatOpts] = useState<{ value: string; label: string }[]>([]);

  // Modal crear PS
  const [psModalOpen, setPsModalOpen] = useState(false);
  const [psSaving, setPsSaving] = useState(false);

  // Watchers
  const empresaId = Form.useWatch('empresa_id', form);
  const moneda = Form.useWatch('moneda', form);
  const metodoPago = Form.useWatch('metodo_pago', form);
  const formaPago = Form.useWatch('forma_pago', form);

  const tipoCambioDisabled = moneda !== 'USD';
  const receptorDisabled = !empresaId;
  const cfdiDisabled = !empresaId;
  const conceptosDisabled = !empresaId;

  // Reglas de bloqueo por estatus CFDI
  const isFormDisabled = estatusCFDI === 'TIMBRADA' || estatusCFDI === 'CANCELADA';
  const fieldDisabled = (defaultDisabled: boolean) => (isFormDisabled ? true : defaultDisabled);
  const fieldAlwaysEditable = (name: string) => {
    return ['status_pago', 'fecha_cobro', 'observaciones'].includes(name) ? false : isFormDisabled;
  };

  const puedeTimbrar = Boolean(id) && estatusCFDI === 'BORRADOR';
  const puedeCancelar = Boolean(id) && estatusCFDI === 'TIMBRADA';

  /* Totales */
  const resumen = useMemo(() => {
    let subtotal = 0;
    let traslados = 0;
    let retenciones = 0;

    conceptos.forEach(c => {
      const cantidad = Number(c.cantidad || 0);
      const valor_unitario = Number(c.valor_unitario || 0);
      const descuento = Number(c.descuento || 0);
      const iva_tasa = Number(c.iva_tasa || 0);
      const ret_iva_tasa = Number(c.ret_iva_tasa || 0);
      const ret_isr_tasa = Number(c.ret_isr_tasa || 0);

      const base = Math.max(cantidad * valor_unitario - descuento, 0);
      const iva = base * iva_tasa;
      const ret_iva = base * ret_iva_tasa;
      const ret_isr = base * ret_isr_tasa;

      subtotal += base;
      traslados += iva;
      retenciones += ret_iva + ret_isr;
    });

    const total = subtotal + traslados - retenciones;
    return { subtotal, traslados, retenciones, total };
  }, [conceptos]);

  /* Catálogos / empresas */
  const cargarCatalogos = async () => {
    const [mp, fp, uc, rf, tr, mc] = await Promise.all([
      api.get('/catalogos/cfdi/metodos-pago'),
      api.get('/catalogos/cfdi/formas-pago'),
      api.get('/catalogos/cfdi/usos-cfdi'),
      api.get('/catalogos/regimen-fiscal'),
      api.get('/catalogos/cfdi/tipos-relacion'),
      api.get('/catalogos/cfdi/motivos-cancelacion'), // NEW
    ]);
    setMetodosPago(mp.data.map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
    setFormasPago(fp.data.map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
    setUsosCfdi(uc.data.map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
    setRegimenes(rf.data.map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
    setTiposRelacion(tr.data.map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })));
    setMotivosCancel(mc.data.map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` }))); // NEW
  };

  const cargarEmpresas = async () => {
    const res = await api.get('/empresas/');
    setEmpresas((res.data || []).map((e: any) => ({ value: e.id, label: e.nombre_comercial ?? e.nombre })));
  };

  /* Empresa / Cliente */
  const onEmpresaChange = async (empId?: string) => {
    form.setFieldsValue({
      cliente_id: undefined,
      nombre_fiscal_receptor: undefined,
      rfc_receptor: undefined,
      regimen_fiscal_receptor: undefined,
      cp_receptor: undefined,
    });
    setClienteOpts([]);
    setDiasCreditoCliente(0);

    if (!empId) {
      form.setFieldsValue({
        nombre_fiscal_emisor: undefined,
        regimen_fiscal_emisor: undefined,
        lugar_expedicion: undefined,
      });
      setRfcEmisor('');
      return;
    }

    const { data } = await api.get(`/empresas/${empId}`);
    form.setFieldsValue({
      nombre_fiscal_emisor: data.nombre ?? data.nombre_comercial,
      regimen_fiscal_emisor: data.regimen_fiscal,
      lugar_expedicion: data.codigo_postal,
    });
    setRfcEmisor((data?.rfc || '').toUpperCase());

    try {
      const { data: factResp } = await api.get('/facturas/', {
        params: { empresa_id: empId, limit: 1, offset: 0, order_by: 'serie_folio', order_dir: 'desc' },
      });
      const last = factResp?.items?.[0];
      const nextFolio = last?.folio ? Number(last.folio) + 1 : 1;
      form.setFieldValue('folio', nextFolio);
    } catch {
      form.setFieldValue('folio', 1);
    }
  };

  const buscarClientes = debounce(async (q: string) => {
    const empId = form.getFieldValue('empresa_id');
    if (!empId) return;
    if (!q || q.trim().length < 3) {
      setClienteOpts([]);
      return;
    }
    try {
      const { data } = await api.get(`/clientes/busqueda?q=${encodeURIComponent(q)}&limit=10`);
      setClienteOpts(
        (data || []).map((c: any) => ({
          value: c.id,
          label: c.nombre_comercial ?? c.razon_social ?? c.nombre ?? 'Cliente',
        })),
      );
    } catch {
      setClienteOpts([]);
    }
  }, 350);

  const onClienteChange = async (cid?: string) => {
    if (!cid) {
      form.setFieldsValue({
        nombre_fiscal_receptor: undefined,
        rfc_receptor: undefined,
        regimen_fiscal_receptor: undefined,
        cp_receptor: undefined,
        fecha_pago: null,
      });
      setDiasCreditoCliente(0);
      return;
    }
    const { data } = await api.get(`/clientes/${cid}`);
    form.setFieldsValue({
      nombre_fiscal_receptor: data.nombre_razon_social ?? data.nombre_comercial,
      rfc_receptor: data.rfc,
      regimen_fiscal_receptor: data.regimen_fiscal,
      cp_receptor: data.codigo_postal,
    });
    const dias = Number(data.dias_credito ?? 0);
    setDiasCreditoCliente(dias);

    const fe = form.getFieldValue('fecha_emision') as Dayjs | undefined;
    if (fe && dayjs.isDayjs(fe)) {
      form.setFieldValue('fecha_pago', fe.add(dias, 'day'));
    }
  };

  const onFechaEmisionChange = (d: Dayjs | null) => {
    if (!d) {
      form.setFieldsValue({ fecha_pago: null, fecha_cobro: null });
      return;
    }
    const dias = diasCreditoCliente || 0;
    form.setFieldsValue({
      fecha_pago: d.add(dias, 'day'),
      ...(form.getFieldValue('status_pago') === 'PAGADA' ? { fecha_cobro: d.add(dias, 'day') } : {}),
    });
  };

  // Productos/Servicios (existentes por empresa)
  const buscarPS = debounce(async (q: string) => {
    const empId = form.getFieldValue('empresa_id');
    if (!empId) return;
    if (!q || q.trim().length < 2) {
      setPsOpts([]);
      return;
    }
    try {
      const { data } = await api.get(
        `/productos-servicios/busqueda?empresa_id=${encodeURIComponent(empId)}&q=${encodeURIComponent(q)}`
      );
      const opts = (data || []).map((it: any) => ({
        value: it.id,
        label: `${it.clave_producto} — ${it.descripcion}`,
        meta: {
          id: it.id,
          clave_producto: it.clave_producto,
          clave_unidad: it.clave_unidad,
          descripcion: it.descripcion,
          valor_unitario: Number(it.valor_unitario ?? 0),
        },
      }));
      setPsOpts(opts);
    } catch {
      setPsOpts([]);
    }
  }, 300);

  /* Catálogo SAT: claves producto (para modal ALTA PS) */
  const buscarClavesProductoSAT = debounce(async (q: string) => {
    if (!q || q.trim().length < 3) {
      setClaveSatOpts([]);
      return;
    }
    try {
      const { data } = await api.get(`/catalogos/busqueda/productos?q=${encodeURIComponent(q)}&limit=20`);
      setClaveSatOpts(
        (data || []).map((x: any) => ({ value: x.clave, label: `${x.clave} — ${x.descripcion}` })),
      );
    } catch {
      setClaveSatOpts([]);
    }
  }, 350);

  const buscarUnidadesSAT = debounce(async (q: string) => {
    if (!q || q.trim().length < 2) {
      setUnidadOpts([]);
      return;
    }
    try {
      const { data } = await api.get(`/catalogos/busqueda/unidades?q=${encodeURIComponent(q)}&limit=20`);
      setUnidadOpts((data || []).map((u: any) => ({ value: u.clave, label: `${u.clave} — ${u.descripcion}` })));
    } catch {
      setUnidadOpts([]);
    }
  }, 250);

  // Modal conceptos
  useEffect(() => {
    if (isConceptoModalOpen) {
      if (editingConcepto) {
        conceptoForm.setFieldsValue({
          ...editingConcepto,
          iva_tasa: editingConcepto.iva_tasa ?? 0.16,
        });
      } else {
        conceptoForm.resetFields();
        conceptoForm.setFieldsValue({ cantidad: 1, descuento: 0, iva_tasa: 0.16, ret_iva_tasa: 0, ret_isr_tasa: 0 });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConceptoModalOpen, editingConcepto]);

  const sugerirRetencionesSiAplica = async () => {
    try {
      const reg = form.getFieldValue('regimen_fiscal_emisor') as string | undefined;
      if (!reg) return;

      let receptorMoral = false;
      const cid = form.getFieldValue('cliente_id');
      if (cid) {
        const { data } = await api.get(`/clientes/${cid}`);
        receptorMoral = (data?.tipo_persona ?? '').toUpperCase() === 'MORAL';
      }

      const esRIFoRESICO =
        /Régimen Simplificado de Confianza/i.test(reg) ||
        /Incorporación Fiscal/i.test(reg) ||
        /RESICO/i.test(reg) ||
        /RIF/i.test(reg);

      if (esRIFoRESICO && receptorMoral) {
        if (conceptoForm.getFieldValue('ret_iva_tasa') == null) conceptoForm.setFieldValue('ret_iva_tasa', 0.106667);
        if (conceptoForm.getFieldValue('ret_isr_tasa') == null) conceptoForm.setFieldValue('ret_isr_tasa', 0.0125);
        message.info('Sugeridas retenciones para RESICO/RIF a persona moral (ajústalas si es necesario).');
      }
    } catch { /* no-op */ }
  };

  const onSelectPSInModal = (_: any, option: any) => {
    const meta = option?.meta || {};
    conceptoForm.setFieldsValue({
      clave_producto: meta.clave_producto,
      clave_unidad: meta.clave_unidad,
      descripcion: meta.descripcion,
      valor_unitario: meta.valor_unitario,
    });
    sugerirRetencionesSiAplica();
  };

  const handleSaveConcepto = async () => {
    const values = await conceptoForm.validateFields();
    const newConcepto: ConceptoForm = {
      ...values,
      cantidad: Number(values.cantidad ?? 0),
      valor_unitario: Number(values.valor_unitario ?? 0),
      descuento: values.descuento != null ? Number(values.descuento) : null,
      iva_tasa: values.iva_tasa != null ? Number(values.iva_tasa) : 0,
      ret_iva_tasa: values.ret_iva_tasa != null ? Number(values.ret_iva_tasa) : 0,
      ret_isr_tasa: values.ret_isr_tasa != null ? Number(values.ret_isr_tasa) : 0,
    };

    if (editingConceptoIndex !== null) {
      const newConceptos = [...conceptos];
      newConceptos[editingConceptoIndex] = newConcepto;
      setConceptos(newConceptos);
    } else {
      setConceptos([...conceptos, newConcepto]);
    }
    setIsConceptoModalOpen(false);
  };

  /* Método/forma de pago: reglas PUE/PPD */
  useEffect(() => {
    if (!metodoPago) return;
    const POR_DEFINIR = '99';
    if (metodoPago === 'PUE') {
      if (formaPago === POR_DEFINIR) {
        form.setFieldValue('forma_pago', undefined);
      }
    } else if (metodoPago === 'PPD') {
      if (formaPago !== POR_DEFINIR) {
        form.setFieldValue('forma_pago', POR_DEFINIR);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metodoPago]);

  // Filtra opciones de forma de pago según método
  const formaPagoOptions = useMemo(() => {
    const POR_DEFINIR = '99';
    if (!metodoPago) return formasPago;
    if (metodoPago === 'PUE') {
      return (formasPago || []).filter((f) => f.value !== POR_DEFINIR);
    }
    if (metodoPago === 'PPD') {
      return (formasPago || []).filter((f) => f.value === POR_DEFINIR);
    }
    return formasPago;
  }, [formasPago, metodoPago]);

  /* Cargar factura (edición) / Init */
  const cargarFactura = async (fid: string) => {
    const { data } = await api.get<FacturaOut>(`/facturas/${fid}`);

    setEstatusCFDI(data.estatus);
    setStatusPago(data.status_pago);

    await onEmpresaChange(data.empresa_id);

    if (data.cliente_id) {
      try {
        const cli = data.cliente ?? (await api.get(`/clientes/${data.cliente_id}`)).data;
        const label = cli?.nombre_comercial ?? cli?.razon_social ?? cli?.nombre ?? 'Cliente';
        setClienteOpts([{ value: data.cliente_id, label }]);
        form.setFieldValue('cliente_id', data.cliente_id);
        await onClienteChange(data.cliente_id);
      } catch {
        form.setFieldValue('cliente_id', data.cliente_id);
      }
    }

    const conceptosCargados = (data.conceptos || []).map(c => ({
      ...c,
      cantidad: Number(c.cantidad ?? 0),
      valor_unitario: Number(c.valor_unitario ?? 0),
      descuento: c.descuento != null ? Number(c.descuento) : null,
      iva_tasa: c.iva_tasa != null ? Number(c.iva_tasa) : 0,
      ret_iva_tasa: c.ret_iva_tasa != null ? Number(c.ret_iva_tasa) : 0,
      ret_isr_tasa: c.ret_isr_tasa != null ? Number(c.ret_isr_tasa) : 0,
    }));
    setConceptos(conceptosCargados);

    form.setFieldsValue({
      empresa_id: data.empresa_id,
      serie: data.serie ?? undefined,
      folio: data.folio,
      moneda: data.moneda,
      tipo_cambio: data.tipo_cambio ?? undefined,
      metodo_pago: data.metodo_pago ?? undefined,
      forma_pago: data.forma_pago ?? undefined,
      uso_cfdi: data.uso_cfdi ?? undefined,
      lugar_expedicion: data.lugar_expedicion ?? undefined,
      condiciones_pago: data.condiciones_pago ?? undefined,
      cfdi_relacionados_tipo: data.cfdi_relacionados_tipo ?? undefined,
      cfdi_relacionados: data.cfdi_relacionados ?? undefined,
      tiene_relacion: !!(data.cfdi_relacionados_tipo || data.cfdi_relacionados),
      status_pago: data.status_pago,
      folio_fiscal: data.folio_fiscal ?? (data as any).cfdi_uuid ?? undefined,
      fecha_emision: data.fecha_emision ? dayjs(data.fecha_emision) : dayjs(),
      fecha_timbrado: data.fecha_timbrado ? dayjs(data.fecha_timbrado) : null,
      fecha_pago: data.fecha_pago ? dayjs(data.fecha_pago) : null,
      fecha_cobro: data.fecha_cobro ? dayjs(data.fecha_cobro) : null,
      observaciones: data.observaciones ?? undefined,
    });

    setMetadata({ creado_en: data.creado_en, actualizado_en: data.actualizado_en });
  };

  // Cargar catálogos/empresas una vez
  useEffect(() => {
    (async () => {
      try {
        await Promise.all([cargarCatalogos(), cargarEmpresas()]);
      } catch {
        message.error('Error al cargar catálogos/empresas');
      }
    })();
  }, []);

  // Init/Edición
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        if (id) {
          await cargarFactura(id);
        } else {
          setConceptos([]);
          setEstatusCFDI('BORRADOR');
          setStatusPago('NO_PAGADA');
          form.setFieldsValue({
            moneda: 'MXN',
            tiene_relacion: false,
            fecha_emision: dayjs(),
            status_pago: 'NO_PAGADA',
          });
        }
      } catch {
        message.error('Error al inicializar el formulario');
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  /* Guardado / acciones */
  const normalizeConcepto = (c: ConceptoForm) => ({
    clave_producto: c.clave_producto,
    clave_unidad: c.clave_unidad,
    descripcion: c.descripcion || 'Concepto sin descripción',
    cantidad: Number(c.cantidad ?? 0),
    valor_unitario: Number(c.valor_unitario ?? 0),
    descuento: c.descuento != null ? Number(c.descuento) : undefined,
    iva_tasa: c.iva_tasa != null ? Number(c.iva_tasa) : undefined,
    ret_iva_tasa: c.ret_iva_tasa != null ? Number(c.ret_iva_tasa) : undefined,
    ret_isr_tasa: c.ret_isr_tasa != null ? Number(c.ret_isr_tasa) : undefined,
  });

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      if (values.status_pago === 'PAGADA' && !values.fecha_cobro) {
        message.error('Para marcar PAGADA, captura la Fecha de cobro.');
        setSaving(false);
        return;
      }

      // Reglas PUE/PPD para forma de pago
      const POR_DEFINIR = '99';
      if (values.metodo_pago === 'PUE' && values.forma_pago === POR_DEFINIR) {
        message.error('Con método PUE la forma de pago no puede ser "Por definir (99)".');
        setSaving(false);
        return;
      }
      if (values.metodo_pago === 'PPD' && values.forma_pago !== POR_DEFINIR) {
        message.error('Con método PPD la forma de pago debe ser "Por definir (99)".');
        setSaving(false);
        return;
      }

      const payload = {
        ...values,
        cliente_id: values.cliente_id,
        uso_cfdi: values.uso_cfdi || null,
        fecha_emision: values.fecha_emision ? (values.fecha_emision as Dayjs).toISOString() : null,
        fecha_timbrado: values.fecha_timbrado ? (values.fecha_timbrado as Dayjs).toISOString() : null,
        fecha_pago: values.fecha_pago ? (values.fecha_pago as Dayjs).toISOString() : null,
        fecha_cobro: values.fecha_cobro ? (values.fecha_cobro as Dayjs).toISOString() : null,
        tipo_cambio:
          values.moneda === 'USD'
            ? values.tipo_cambio !== undefined && values.tipo_cambio !== null
              ? Number(values.tipo_cambio)
              : undefined
            : null,
        cfdi_relacionados_tipo: values.tiene_relacion ? values.cfdi_relacionados_tipo : null,
        cfdi_relacionados: values.tiene_relacion ? values.cfdi_relacionados : null,
        observaciones: values.observaciones || null,
        folio_fiscal: values.folio_fiscal || null,
        conceptos: conceptos.map(normalizeConcepto),
      };

      if (id) {
        await api.put(`/facturas/${id}`, payload);
        message.success('Factura actualizada');
      } else {
        delete (payload as Partial<typeof payload>).folio;
        await api.post('/facturas/', payload);
        message.success('Factura creada');
      }
      router.push('/facturas');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (Array.isArray(detail)) {
        const mensajes = detail.map((e: any) => `${e?.loc?.join('.')}: ${e?.msg}`).join('\n');
        message.error(mensajes || 'Error de validación');
      } else if (typeof detail === 'string') {
        message.error(detail);
      } else {
        message.error('Error al guardar');
      }
    } finally {
      setSaving(false);
    }
  };

  const timbrarFactura = async () => {
    if (!id) return;
    setAccionLoading((s) => ({ ...s, timbrar: true }));
    try {
      const { data } = await api.post(`/facturas/${id}/timbrar`);
      setEstatusCFDI(data.estatus);
      form.setFieldsValue({
        fecha_timbrado: data.fecha_timbrado ? dayjs(data.fecha_timbrado) : form.getFieldValue('fecha_timbrado'),
        folio_fiscal: data.folio_fiscal ?? form.getFieldValue('folio_fiscal'),
      });
      message.success('Factura timbrada');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'No se pudo timbrar');
    } finally {
      setAccionLoading((s) => ({ ...s, timbrar: false }));
    }
  };

  // Abre el modal de cancelación con motivo por defecto (del catálogo)
  const abrirModalCancelacion = () => {
    cancelForm.resetFields();
    const defaultMotivo = motivosCancel?.[0]?.value || '02';
    cancelForm.setFieldsValue({ motivo: defaultMotivo, folio_sustitucion: undefined });
    setCancelModalOpen(true);
  };

  const submitCancel = async () => {
    if (!id) return;
    try {
      const vals = await cancelForm.validateFields();
      const motivo = String(vals.motivo || '');
      const payload = {
        motivo_cancelacion: motivo,
        folio_fiscal_sustituto: motivo === '01'
          ? (vals.folio_sustitucion || '').trim() || null
          : null,
      };

      setCancelSubmitting(true);
      const { data } = await api.post(`/facturas/${id}/cancelar`, payload);
      setEstatusCFDI(data.estatus || 'CANCELADA');
      message.success(data?.message || 'Solicitud de cancelación enviada');
      setCancelModalOpen(false);
    } catch (e: any) {
      if (e?.errorFields) {
        // errores del Form
      } else {
        const detail = e?.response?.data?.detail || e?.message;
        message.error(detail || 'No se pudo cancelar');
      }
    } finally {
      setCancelSubmitting(false);
    }
  };

  const verPDF = async () => {
    if (!id) {
      message.info('Guarda la factura para generar la vista previa.');
      return;
    }
    try {
      const path =
        estatusCFDI === 'BORRADOR'
          ? `/facturas/${id}/preview-pdf`
          : `/facturas/${id}/pdf`;

      const res = await api.get(path, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);

      window.open(url, '_blank', 'noopener,noreferrer');
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      message.error(detail || 'No se pudo abrir el PDF');
    }
  };

  const descargarPDF = async () => {
    if (!id) return;
    try {
      const res = await api.get(`/facturas/${id}/pdf-download`, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const rfc = (rfcEmisor || 'RFC').toUpperCase().replace(/\s+/g, '');
      const serie = (form.getFieldValue('serie') || 'S/N').toString().replace(/\s+/g, '');
      const folio = (form.getFieldValue('folio') || id).toString().replace(/\s+/g, '');
      const safe = (s: string) => s.replace(/[^a-zA-Z0-9._-]/g, '');
      const filename = `${safe(rfc)}-factura-${safe(serie)}-${safe(folio)}.pdf`;
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      message.error(detail || 'No se pudo descargar el PDF');
    }
  };

  const descargarXML = async () => {
    if (!id) return;
    try {
      const res = await api.get(`/facturas/${id}/xml`, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'application/xml' });
      const url = window.URL.createObjectURL(blob);
      const rfc = (rfcEmisor || 'RFC').toUpperCase().replace(/\s+/g, '');
      const serie = (form.getFieldValue('serie') || 'S/N').toString().replace(/\s+/g, '');
      const folio = (form.getFieldValue('folio') || id).toString().replace(/\s+/g, '');
      const safe = (s: string) => s.replace(/[^a-zA-Z0-9._-]/g, '');
      const filename = `${safe(rfc)}-factura-${safe(serie)}-${safe(folio)}.xml`;
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      message.error(detail || 'No se pudo descargar el XML');
    }
  };

  if (loading) return <Spin style={{ margin: 48 }} />;

  /* Render */
  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">{id ? 'Editar Factura' : 'Nueva Factura'}</h1>
        </div>
      </div>

      <div className="app-content">
        <Card>
          {metadata && (
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: '0.85em' }}>
                Creada: {formatDateTj(metadata.creado_en)} &nbsp;|&nbsp; Actualizada: {formatDateTj(metadata.actualizado_en)}
              </Text>
            </div>
          )}

          <Form form={form} layout="vertical" onFinish={onFinish}>
            {/* Emisor */}
            <Card size="small" title="Emisor" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item label="Empresa" name="empresa_id" rules={[{ required: true, message: 'Requerido' }]}>
                    <Select
                      options={empresas}
                      showSearch
                      optionFilterProp="label"
                      onChange={(v) => onEmpresaChange(v)}
                      disabled={fieldDisabled(false)}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Lugar de expedición (CP)" name="lugar_expedicion">
                    <Input disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Folio" name="folio" rules={[{ required: true, message: 'Requerido' }]}>
                    <InputNumber min={1} style={{ width: '100%' }} disabled={fieldDisabled(false)} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item label="Nombre fiscal (emisor)" name="nombre_fiscal_emisor">
                    <Input disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="Régimen fiscal (emisor)" name="regimen_fiscal_emisor">
                    <Select options={regimenes} disabled />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* Receptor */}
            <Card size="small" title="Receptor" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item label="Cliente" name="cliente_id" rules={[{ required: true, message: 'Requerido' }]}>
                    <Select
                      showSearch
                      filterOption={false}
                      onSearch={buscarClientes}
                      options={clienteOpts}
                      disabled={fieldDisabled(receptorDisabled)}
                      onChange={(v) => onClienteChange(v)}
                      placeholder={receptorDisabled ? 'Selecciona una empresa' : 'Buscar cliente...'}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label="Nombre fiscal (receptor)" name="nombre_fiscal_receptor">
                    <Input disabled />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Form.Item label="RFC receptor" name="rfc_receptor">
                    <Input disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Régimen fiscal (receptor)" name="regimen_fiscal_receptor">
                    <Select options={regimenes} disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="CP receptor" name="cp_receptor">
                    <Input disabled />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* Fechas y estados */}
            <Card size="small" title="Fechas y estados" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={24} md={6}>
                  <Form.Item label="Fecha emisión" name="fecha_emision" rules={[{ required: true, message: 'Requerido' }]}>
                    <DatePicker
                      style={{ width: '100%' }}
                      onChange={(d) => onFechaEmisionChange(d)}
                      disabled={fieldDisabled(false)}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Fecha timbrado" name="fecha_timbrado">
                    <DatePicker style={{ width: '100%' }} disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Fecha pago (programada)" name="fecha_pago">
                    <DatePicker style={{ width: '100%' }} disabled={fieldDisabled(false)} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item
                    label="Fecha cobro (real)"
                    name="fecha_cobro"
                    rules={
                      form.getFieldValue('status_pago') === 'PAGADA'
                        ? [{ required: true, message: 'Captura la fecha de cobro' }]
                        : []
                    }
                  >
                    <DatePicker style={{ width: '100%' }} disabled={fieldAlwaysEditable('fecha_cobro')} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16} align="bottom">
                <Col xs={24} md={6}>
                  <Form.Item label="Estatus CFDI">
                    <Input value={estatusCFDI} disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Estatus de pago" name="status_pago" initialValue={statusPago}>
                    <Select
                      options={[
                        { value: 'NO_PAGADA', label: 'NO_PAGADA' },
                        { value: 'PAGADA', label: 'PAGADA' },
                      ]}
                      onChange={(v: StatusPago) => {
                        form.setFieldValue('status_pago', v);
                        setStatusPago(v);
                        if (v === 'PAGADA') {
                          const fe = form.getFieldValue('fecha_emision') as Dayjs | undefined;
                          if (fe && dayjs.isDayjs(fe)) {
                            form.setFieldValue('fecha_cobro', fe.add(diasCreditoCliente || 0, 'day'));
                          }
                        }
                      }}
                      disabled={fieldAlwaysEditable('status_pago')}
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* CFDI */}
            <Card size="small" title="CFDI" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={24} md={6}>
                  <Form.Item label="Moneda" name="moneda" rules={[{ required: true, message: 'Requerido' }]}>
                    <Select
                      options={[{ value: 'MXN', label: 'MXN' }, { value: 'USD', label: 'USD' }]}
                      disabled={fieldDisabled(!empresaId)}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Tipo de cambio" name="tipo_cambio">
                    <InputNumber min={0} step={0.0001} disabled={fieldDisabled(moneda !== 'USD' || cfdiDisabled)} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Método de pago" name="metodo_pago">
                    <Select allowClear options={metodosPago} disabled={fieldDisabled(!empresaId)} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Forma de pago" name="forma_pago">
                    <Select allowClear options={formaPagoOptions} disabled={fieldDisabled(!empresaId)} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item label="Folio fiscal (UUID)" name="folio_fiscal">
                    <Input disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Uso CFDI" name="uso_cfdi">
                    <Select allowClear options={usosCfdi} disabled={fieldDisabled(!empresaId)} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={6}>
                  <Form.Item label="Condiciones de pago" name="condiciones_pago">
                    <Input disabled={fieldDisabled(cfdiDisabled)} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={6}>
                  <Form.Item valuePropName="checked" name="tiene_relacion" initialValue={false}>
                    <Checkbox disabled={fieldDisabled(cfdiDisabled)}>¿Tiene relación CFDI?</Checkbox>
                  </Form.Item>
                </Col>
                <Col xs={24} md={9}>
                  <Form.Item label="Tipo relación" name="cfdi_relacionados_tipo">
                    <Select
                      allowClear
                      options={tiposRelacion}
                      disabled={fieldDisabled(!form.getFieldValue('tiene_relacion') || cfdiDisabled)}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={9}>
                  <Form.Item label="CFDIs relacionados" name="cfdi_relacionados" tooltip="Separados por coma o texto libre">
                    <Input disabled={fieldDisabled(!form.getFieldValue('tiene_relacion') || cfdiDisabled)} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={24}>
                  <Form.Item label="Observaciones" name="observaciones">
                    <Input.TextArea rows={3} disabled={fieldAlwaysEditable('observaciones')} />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* Conceptos */}
            <Card
              size="small"
              title="Conceptos"
              extra={
                <Space>
                  <Button
                    icon={<PlusOutlined />}
                    onClick={() => {
                      setEditingConcepto(null);
                      setEditingConceptoIndex(null);
                      setIsConceptoModalOpen(true);
                    }}
                    disabled={fieldDisabled(!empresaId)}
                  >
                    Agregar concepto
                  </Button>
                  <Button icon={<PlusCircleOutlined />} onClick={() => setPsModalOpen(true)} disabled={fieldDisabled(!empresaId)}>
                    Nuevo producto/servicio
                  </Button>
                </Space>
              }
            >
              <Table
                size="small"
                bordered
                dataSource={conceptos}
                rowKey={(r, i) => String((r as any).id ?? i)}
                pagination={false}
                columns={[
                  { title: 'Clave SAT', dataIndex: 'clave_producto', key: 'clave_producto' },
                  { title: 'Descripción', dataIndex: 'descripcion', key: 'descripcion' },
                  { title: 'Unidad SAT', dataIndex: 'clave_unidad', key: 'clave_unidad' },
                  { title: 'Cantidad', dataIndex: 'cantidad', key: 'cantidad', align: 'right' },
                  { title: 'P. Unitario', dataIndex: 'valor_unitario', key: 'valor_unitario', align: 'right', render: (v) => Number(v).toFixed(2) },
                  { title: 'Tasa IVA', dataIndex: 'iva_tasa', key: 'iva_tasa', align: 'right', render: (v) => (v != null ? Number(v).toFixed(3) : '0.000') },
                  { title: 'Ret IVA', dataIndex: 'ret_iva_tasa', key: 'ret_iva_tasa', align: 'right', render: (v) => (v != null ? Number(v).toFixed(6) : '0.000000') },
                  { title: 'Ret ISR', dataIndex: 'ret_isr_tasa', key: 'ret_isr_tasa', align: 'right', render: (v) => (v != null ? Number(v).toFixed(6) : '0.000000') },
                  {
                    title: 'Importe',
                    key: 'importe',
                    align: 'right',
                    render: (_: any, r: any) => {
                      const cantidad = Number(r.cantidad || 0);
                      const valor_unitario = Number(r.valor_unitario || 0);
                      const descuento = Number(r.descuento || 0);
                      const iva_tasa = Number(r.iva_tasa || 0);
                      const ret_iva_tasa = Number(r.ret_iva_tasa || 0);
                      const ret_isr_tasa = Number(r.ret_isr_tasa || 0);
                      const base = Math.max(cantidad * valor_unitario - descuento, 0);
                      const iva = base * iva_tasa;
                      const ret_iva = base * ret_iva_tasa;
                      const ret_isr = base * ret_isr_tasa;
                      const importe = base + iva - ret_iva - ret_isr;
                      return importe.toFixed(2);
                    }
                  },
                  {
                    title: 'Acciones',
                    key: 'acciones',
                    align: 'center',
                    render: (_: any, record: any, index: number) => (
                      <Space>
                        <Button
                          type="link"
                          icon={<EditOutlined />}
                          onClick={() => {
                            setEditingConcepto(record);
                            setEditingConceptoIndex(index);
                            setIsConceptoModalOpen(true);
                          }}
                          disabled={fieldDisabled(!empresaId)}
                        />
                        <Popconfirm
                          title="¿Eliminar este concepto?"
                          onConfirm={() => {
                            const newConceptos = [...conceptos];
                            newConceptos.splice(index, 1);
                            setConceptos(newConceptos);
                          }}
                          disabled={fieldDisabled(false)}
                        >
                          <Button type="link" danger icon={<DeleteOutlined />} disabled={fieldDisabled(!empresaId)} />
                        </Popconfirm>
                      </Space>
                    ),
                  },
                ]}
              />

              <Divider />

              <Row justify="end" gutter={24}>
                <Col>
                  <Text>
                    Subtotal:&nbsp;<b>{resumen.subtotal.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}</b>
                  </Text>
                </Col>
                <Col>
                  <Text>
                    Trasladados:&nbsp;<b>{resumen.traslados.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}</b>
                  </Text>
                </Col>
                <Col>
                  <Text>
                    Retenciones:&nbsp;<b>{resumen.retenciones.toLocaleString('es-MX', { style: 'currency', 'currency': 'MXN' })}</b>
                  </Text>
                </Col>
                <Col>
                  <Text>
                    Total:&nbsp;<b>{resumen.total.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })}</b>
                  </Text>
                </Col>
              </Row>
            </Card>

            <Divider />

            {/* Botones */}
            <Space>
              <Button onClick={() => router.push('/facturas')}>Regresar</Button>
              <Button type="primary" htmlType="submit" loading={saving}>
                {id ? 'Actualizar' : 'Guardar'}
              </Button>
              <Button
                icon={<ThunderboltOutlined />}
                onClick={timbrarFactura}
                loading={accionLoading.timbrar}
                disabled={!puedeTimbrar}
              >
                Timbrar
              </Button>

              {/* Botón de cancelación → abre modal */}
              <Button
                danger
                icon={<StopOutlined />}
                onClick={abrirModalCancelacion}
                loading={accionLoading.cancelar || cancelSubmitting}
                disabled={!puedeCancelar}
              >
                Cancelar CFDI
              </Button>

              {/* Botón PDF fuera del Popconfirm */}
              <Button
                icon={<FilePdfOutlined />}
                onClick={verPDF}
                disabled={!id}
              >
                Ver PDF
              </Button>
              {estatusCFDI === 'TIMBRADA' && (
                <>
                  <Button onClick={descargarXML}>Descargar XML</Button>
                  <Button onClick={descargarPDF}>Descargar PDF</Button>
                </>
              )}
            </Space>
          </Form>
        </Card>

        {/* En algún lugar del <Form> (fuera de las tarjetas) */}
        <Form.Item name="serie" hidden>
          <Input />
        </Form.Item>
      </div>

      {/* Modal: Añadir/Editar Concepto */}
      <Modal
        title={editingConcepto ? "Editar Concepto" : "Añadir Concepto"}
        open={isConceptoModalOpen}
        onOk={handleSaveConcepto}
        onCancel={() => setIsConceptoModalOpen(false)}
        width={840}
        destroyOnClose
        okButtonProps={{ disabled: isFormDisabled }}
      >
        <Form form={conceptoForm} layout="vertical">
          <Form.Item
            label="Producto/Servicio (catálogo de tu empresa)"
            name="ps_lookup"
            rules={[{ required: true, message: 'Selecciona un producto/servicio' }]}
          >
            <Select
              showSearch
              placeholder="Buscar en catálogo de la empresa…"
              filterOption={false}
              onSearch={buscarPS}
              options={psOpts}
              onSelect={onSelectPSInModal}
              disabled={!empresaId || isFormDisabled}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="Clave SAT" name="clave_producto">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Unidad SAT" name="clave_unidad">
                <Input disabled />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="Descripción" name="descripcion">
            <Input.TextArea rows={2} disabled />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="Cantidad" name="cantidad" rules={[{ required: true }]}>
                <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Valor Unitario" name="valor_unitario" rules={[{ required: true }]}>
                <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Descuento" name="descuento">
                <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="IVA Tasa">
                <Form.Item name="iva_tasa" noStyle>
                  <Select
                    options={[
                      { value: 0, label: '0%' },
                      { value: 0.08, label: '8%' },
                      { value: 0.16, label: '16%' },
                    ]}
                    defaultValue={0.16}
                    disabled={isFormDisabled}
                  />
                </Form.Item>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Ret. IVA Tasa">
                <Form.Item name="ret_iva_tasa" noStyle>
                  <Select options={RET_IVA_OPTS} disabled={isFormDisabled} />
                </Form.Item>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Ret. ISR Tasa">
                <Form.Item name="ret_isr_tasa" noStyle>
                  <Select options={RET_ISR_OPTS} disabled={isFormDisabled} />
                </Form.Item>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Modal: Cancelación CFDI */}
      <Modal
        title="Cancelar CFDI"
        open={cancelModalOpen}
        onCancel={() => setCancelModalOpen(false)}
        onOk={submitCancel}
        okText="Enviar cancelación"
        confirmLoading={cancelSubmitting}
        destroyOnClose
      >
        <Alert
          style={{ marginBottom: 12 }}
          type="info"
          message="Se enviará la solicitud de cancelación al PAC. Si el motivo es '01', debes indicar el folio fiscal del CFDI sustituto."
          showIcon
        />
        <Form form={cancelForm} layout="vertical">
          <Form.Item
            label="Motivo de cancelación"
            name="motivo"
            rules={[{ required: true, message: 'Selecciona un motivo' }]}
            tooltip="Si eliges 01 debes indicar el folio fiscal (UUID) del CFDI sustituto."
          >
            <Select
              options={motivosCancel}
              showSearch
              optionFilterProp="label"
              placeholder="Selecciona el motivo…"
            />
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(p, c) => p.motivo !== c.motivo}>
            {({ getFieldValue }) => {
              const motivo = String(getFieldValue('motivo') || '');
              const necesitaSustituto = motivo === '01';
              return (
                <Form.Item
                  label="Folio fiscal sustituto (UUID)"
                  name="folio_sustitucion"
                  rules={
                    necesitaSustituto
                      ? [
                          { required: true, message: 'Requerido cuando el motivo es 01' },
                          {
                            validator: (_, v) => {
                              if (!v) return Promise.resolve();
                              const ok = /^[0-9A-Fa-f-]{36}$/.test(String(v).trim());
                              return ok ? Promise.resolve() : Promise.reject(new Error('UUID inválido'));
                            },
                          },
                        ]
                      : []
                  }
                >
                  <Input placeholder={necesitaSustituto ? 'Ej. ABC1147C-D41E-4596-9C3E-45629B090000' : 'Opcional'} disabled={!necesitaSustituto} />
                </Form.Item>
              );
            }}
          </Form.Item>
        </Form>
      </Modal>

      {/* Modal: Crear Producto/Servicio (nuevo en tu catálogo) */}
      <Modal
        title="Nuevo producto/servicio"
        open={psModalOpen}
        onCancel={() => setPsModalOpen(false)}
        onOk={async () => {
          try {
            const vals = await psForm.validateFields();
            setPsSaving(true);
            const payload = {
              tipo: vals.tipo,
              clave_producto: lv(vals.clave_producto),
              clave_unidad: lv(vals.clave_unidad),
              descripcion: vals.descripcion,
              cantidad: vals.cantidad ?? null,
              valor_unitario: Number(vals.valor_unitario),
              empresa_id: form.getFieldValue('empresa_id'),
              stock_actual: vals.tipo === 'PRODUCTO' ? Number(vals.stock_actual || 0) : 0,
              stock_minimo: vals.tipo === 'PRODUCTO' ? Number(vals.stock_minimo || 0) : null,
              unidad_inventario: vals.tipo === 'PRODUCTO' ? vals.unidad_inventario || null : null,
              ubicacion: vals.tipo === 'PRODUCTO' ? vals.ubicacion || null : null,
              requiere_lote: vals.tipo === 'PRODUCTO' ? Boolean(vals.requiere_lote) : false,
            };
            const { data } = await api.post('/productos-servicios/', payload);
            message.success('Producto/Servicio creado');

            const opt = {
              value: data.id,
              label: `${data.clave_producto} — ${data.descripcion}`,
              meta: {
                id: data.id,
                clave_producto: data.clave_producto,
                clave_unidad: data.clave_unidad,
                descripcion: data.descripcion,
                valor_unitario: Number(data.valor_unitario ?? 0),
              },
            };
            setPsOpts((prev) => [opt, ...prev]);
            setPsModalOpen(false);
            psForm.resetFields();
          } catch (e: any) {
            const detail = e?.response?.data?.detail;
            if (Array.isArray(detail)) {
              const mensajes = detail.map((x: any) => `${x?.loc?.join('.')}: ${x?.msg}`).join('\n');
              message.error(mensajes || 'Error de validación');
            } else if (typeof detail === 'string') {
              message.error(detail);
            } else if (e?.errorFields) {
              // errores de form
            } else {
              message.error('No se pudo crear el producto/servicio');
            }
          } finally {
            setPsSaving(false);
          }
        }}
        okButtonProps={{ loading: psSaving, disabled: !empresaId || isFormDisabled }}
        destroyOnClose
      >
        <Form form={psForm} layout="vertical">
          <Form.Item label="Tipo" name="tipo" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'PRODUCTO', label: 'Producto' },
                { value: 'SERVICIO', label: 'Servicio' },
              ]}
              disabled={isFormDisabled}
            />
          </Form.Item>

          <Form.Item label="Clave producto (SAT)" name="clave_producto" rules={[{ required: true }]}>
            <Select
              labelInValue
              showSearch
              filterOption={false}
              onSearch={buscarClavesProductoSAT}
              options={claveSatOpts}
              placeholder="Buscar en catálogo del SAT (mín. 3 caracteres)…"
              disabled={isFormDisabled}
            />
          </Form.Item>

          <Form.Item label="Unidad SAT" name="clave_unidad" rules={[{ required: true }]}>
            <Select
              labelInValue
              showSearch
              filterOption={false}
              onSearch={buscarUnidadesSAT}
              options={unidadOpts}
              disabled={isFormDisabled}
            />
          </Form.Item>

          <Form.Item label="Descripción" name="descripcion" rules={[{ required: true }]}>
            <Input.TextArea rows={2} disabled={isFormDisabled} />
          </Form.Item>

          <Form.Item label="Valor unitario" name="valor_unitario" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
          </Form.Item>

          {/* Campos de inventario condicionales (PRODUCTO) */}
          <Form.Item noStyle shouldUpdate={(p, c) => p.tipo !== c.tipo}>
            {({ getFieldValue }) =>
              getFieldValue('tipo') === 'PRODUCTO' ? (
                <>
                  <Form.Item label="Stock actual" name="stock_actual">
                    <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
                  </Form.Item>
                  <Form.Item label="Stock mínimo" name="stock_minimo">
                    <InputNumber min={0} style={{ width: '100%' }} disabled={isFormDisabled} />
                  </Form.Item>
                  <Form.Item label="Unidad inventario" name="unidad_inventario">
                    <Input maxLength={20} disabled={isFormDisabled} />
                  </Form.Item>
                  <Form.Item label="Ubicación" name="ubicacion">
                    <Input maxLength={100} disabled={isFormDisabled} />
                  </Form.Item>
                  <Form.Item valuePropName="checked" name="requiere_lote" initialValue={false}>
                    <Checkbox disabled={isFormDisabled}>¿Requiere lote?</Checkbox>
                  </Form.Item>
                </>
              ) : null
            }
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default FacturaFormPage;