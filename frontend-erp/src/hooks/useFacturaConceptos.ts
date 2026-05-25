// Manages conceptos (line items) state, modal flow, PS/SAT search, and totals
import { useState, useMemo } from 'react';
import { message } from 'antd';
import type { FormInstance } from 'antd';
import debounce from 'lodash/debounce';
import * as svc from '@/services/facturaService';

export interface ConceptoForm {
  ps_lookup?: unknown;
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

interface SatOpt { value: string; label: string }
interface PsOpt { value: string; label: string; meta: { id: string; clave_producto: string; clave_unidad: string; descripcion: string; valor_unitario: number } }

export const useFacturaConceptos = (form: FormInstance, conceptoForm: FormInstance) => {
  // ── Line-items state ──────────────────────────────────────────────────────────
  const [conceptos, setConceptos] = useState<ConceptoForm[]>([]);
  const [isConceptoModalOpen, setIsConceptoModalOpen] = useState(false);
  const [editingConcepto, setEditingConcepto] = useState<ConceptoForm | null>(null);
  const [editingConceptoIndex, setEditingConceptoIndex] = useState<number | null>(null);

  // ── PS / SAT search state ────────────────────────────────────────────────────
  const [psOpts, setPsOpts] = useState<PsOpt[]>([]);
  const [unidadOpts, setUnidadOpts] = useState<SatOpt[]>([]);
  const [claveSatOpts, setClaveSatOpts] = useState<SatOpt[]>([]);
  const [psModalOpen, setPsModalOpen] = useState(false);
  const [psSaving, setPsSaving] = useState(false);

  // ── Retention suggestion ─────────────────────────────────────────────────────
  const sugerirRetencionesSiAplica = async () => {
    try {
      const reg = form.getFieldValue('regimen_fiscal_emisor') as string | undefined;
      if (!reg) return;
      let receptorMoral = false;
      const cid = form.getFieldValue('cliente_id');
      if (cid) {
        const data = await svc.getClienteById(cid);
        receptorMoral = (data?.tipo_persona ?? '').toUpperCase() === 'MORAL';
      }
      const esRIFoRESICO = /Régimen Simplificado de Confianza|Incorporación Fiscal|RESICO|RIF/i.test(reg);
      if (esRIFoRESICO && receptorMoral) {
        if (conceptoForm.getFieldValue('ret_iva_tasa') == null) conceptoForm.setFieldValue('ret_iva_tasa', 0.106667);
        if (conceptoForm.getFieldValue('ret_isr_tasa') == null) conceptoForm.setFieldValue('ret_isr_tasa', 0.0125);
        message.info('Sugeridas retenciones para RESICO/RIF a persona moral (ajústalas si es necesario).');
      }
    } catch { /* no-op */ }
  };

  const onSelectPSInModal = (_: unknown, option: any) => {
    const meta = option?.meta || {};
    conceptoForm.setFieldsValue({
      clave_producto: meta.clave_producto,
      clave_unidad: meta.clave_unidad,
      descripcion: meta.descripcion,
      valor_unitario: meta.valor_unitario,
    });
    sugerirRetencionesSiAplica();
  };

  // ── Save concepto ────────────────────────────────────────────────────────────
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
      const updated = [...conceptos];
      updated[editingConceptoIndex] = newConcepto;
      setConceptos(updated);
    } else {
      setConceptos([...conceptos, newConcepto]);
    }
    setIsConceptoModalOpen(false);
  };

  // ── PS / SAT debounced searches ──────────────────────────────────────────────
  const buscarPS = useMemo(
    () =>
      debounce(async (q: string) => {
        const empId = form.getFieldValue('empresa_id');
        if (!empId || !q || q.trim().length < 2) { setPsOpts([]); return; }
        try {
          const data = await svc.searchProductosServicios(empId, q);
          setPsOpts(
            (data || []).map((it: any) => ({
              value: it.id,
              label: `${it.clave_producto} — ${it.descripcion}`,
              meta: {
                id: it.id,
                clave_producto: it.clave_producto,
                clave_unidad: it.clave_unidad,
                descripcion: it.descripcion,
                valor_unitario: Number(it.valor_unitario ?? 0),
              },
            })),
          );
        } catch { setPsOpts([]); }
      }, 300),
    [form],
  );

  const buscarClavesProductoSAT = useMemo(
    () =>
      debounce(async (q: string) => {
        if (!q || q.trim().length < 3) { setClaveSatOpts([]); return; }
        try {
          const data = await svc.searchSatProductos(q);
          setClaveSatOpts(
            (data || []).map((x: any) => {
              const value = x?.value ?? x?.clave;
              const desc = x?.descripcion ?? x?.label;
              return { value, label: value && desc ? `${value} - ${desc}` : String(value ?? desc ?? '') };
            }),
          );
        } catch { setClaveSatOpts([]); }
      }, 350),
    [],
  );

  const buscarUnidadesSAT = useMemo(
    () =>
      debounce(async (q: string) => {
        if (!q || q.trim().length < 2) { setUnidadOpts([]); return; }
        try {
          const data = await svc.searchSatUnidades(q);
          setUnidadOpts(
            (data || []).map((u: any) => {
              const value = u?.value ?? u?.clave;
              const desc = u?.descripcion ?? u?.label;
              return { value, label: value && desc ? `${value} - ${desc}` : String(value ?? desc ?? '') };
            }),
          );
        } catch { setUnidadOpts([]); }
      }, 250),
    [],
  );

  // ── Totals ───────────────────────────────────────────────────────────────────
  const resumen = useMemo(() => {
    let subtotal = 0, traslados = 0, retencionesList = 0;
    conceptos.forEach((c) => {
      const base = Math.max(
        Number(c.cantidad || 0) * Number(c.valor_unitario || 0) - Number(c.descuento || 0),
        0,
      );
      traslados += base * Number(c.iva_tasa || 0);
      retencionesList += base * (Number(c.ret_iva_tasa || 0) + Number(c.ret_isr_tasa || 0));
      subtotal += base;
    });
    const total = subtotal + traslados - retencionesList;
    const fmt = (n: number) => n.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
    return { subtotal: fmt(subtotal), traslados: fmt(traslados), retenciones: fmt(retencionesList), total: fmt(total) };
  }, [conceptos]);

  return {
    // line-items
    conceptos, setConceptos,
    isConceptoModalOpen, setIsConceptoModalOpen,
    editingConcepto, setEditingConcepto,
    editingConceptoIndex, setEditingConceptoIndex,
    handleSaveConcepto,
    // PS/SAT search
    psOpts, unidadOpts, claveSatOpts,
    psModalOpen, setPsModalOpen,
    psSaving, setPsSaving,
    buscarPS, buscarClavesProductoSAT, buscarUnidadesSAT,
    onSelectPSInModal,
    // totals
    resumen,
  };
};
