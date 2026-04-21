// src/hooks/useEgresoForm.ts
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { Form, message } from 'antd';
import dayjs from 'dayjs';
import { normalizeISOToUTC } from '@/utils/formatDate';
import * as egresoService from '@/services/egresoService';
import * as facturaService from '@/services/facturaService'; // for getEmpresas
import { useEmpresaSelector } from './useEmpresaSelector';

export const useEgresoForm = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const [form] = Form.useForm();
  const [egreso, setEgreso] = useState<egresoService.Egreso | null>(null);

  // Empresa global del sidebar
  const { selectedEmpresaId: globalEmpresaId } = useEmpresaSelector();
  const globalEmpresaIdRef = useRef(globalEmpresaId);
  useEffect(() => { globalEmpresaIdRef.current = globalEmpresaId; }, [globalEmpresaId]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [empresas, setEmpresas] = useState<{ label: string; value: string }[]>([]);
  const [categorias, setCategorias] = useState<string[]>([]);
  const [estatus, setEstatus] = useState<string[]>([]);
  const [metodosPago, setMetodosPago] = useState<{ label: string; value: string }[]>([]);

  useEffect(() => {
    const fetchInitialData = async () => {
      setLoading(true);
      try {
        const [empresasData, enumsData, formasPagoData] = await Promise.all([
          facturaService.getEmpresas(),
          egresoService.getEgresoEnums(),
          facturaService.getFormasPago(),
        ]);

        setEmpresas(
          (empresasData || []).map((e: any) => ({
            value: e.id,
            label: e.nombre_comercial ?? e.nombre,
          }))
        );

        const empOptions = (empresasData || []);

        setCategorias(enumsData.categorias);
        setEstatus(enumsData.estatus);
        setMetodosPago(
          (formasPagoData || []).map((fp: any) => ({
            value: fp.clave,
            label: `${fp.clave} - ${fp.descripcion}`,
          }))
        );

        if (id) {
          const egresoData = await egresoService.getEgresoById(id);
          setEgreso(egresoData);
          form.setFieldsValue({
            ...egresoData,
            fecha_egreso: egresoData.fecha_egreso ? dayjs(normalizeISOToUTC(egresoData.fecha_egreso)) : null,
          });
        } else {
          // Auto-selección: preferir empresa global del sidebar, o empresa única
          const globalId = globalEmpresaIdRef.current;
          const defaultEmpresaId = (globalId && empOptions.some((e: any) => e.id === globalId))
            ? globalId
            : empOptions.length === 1 ? empOptions[0].id : null;

          form.setFieldsValue({
            empresa_id: defaultEmpresaId,
            fecha_egreso: dayjs(),
            moneda: 'MXN',
            estatus: 'Pendiente',
            categoria: 'Gastos Generales',
            metodo_pago: '03', // Default to Transferencia electrónica
          });
        }
      } catch (error) {
        message.error('Error al cargar datos iniciales.');
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
  }, [id, form]);

  const onFinish = async (values: any) => {
    setSaving(true);
    try {
      const payload = {
        ...values,
        fecha_egreso: values.fecha_egreso ? dayjs(values.fecha_egreso).format('YYYY-MM-DD') : null,
      };

      if (id) {
        await egresoService.updateEgreso(id, payload);
      } else {
        await egresoService.createEgreso(payload);
      }

      if (payload.empresa_id) {
        localStorage.setItem('selectedEmpresaId', payload.empresa_id);
      }

      message.success(`Egreso ${id ? 'actualizado' : 'creado'} con éxito.`);
      router.push('/egresos');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Error al guardar el egreso.');
    } finally {
      setSaving(false);
    }
  };

  return {
    id,
    form,
    egreso,
    loading,
    saving,
    empresas,
    categorias,
    estatus,
    metodosPago,
    onFinish,
  };
};
