// src/hooks/useEgresoForm.ts
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { Form, message } from 'antd';
import dayjs from 'dayjs';
import * as egresoService from '@/services/egresoService';
import * as facturaService from '@/services/facturaService'; // for getEmpresas

export const useEgresoForm = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const [form] = Form.useForm();
  const [egreso, setEgreso] = useState<egresoService.Egreso | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [empresas, setEmpresas] = useState<{ label: string; value: string }[]>([]);
  const [categorias, setCategorias] = useState<string[]>([]);
  const [estatus, setEstatus] = useState<string[]>([]);

  useEffect(() => {
    const fetchInitialData = async () => {
      setLoading(true);
      try {
        const [empresasData, enumsData] = await Promise.all([
          facturaService.getEmpresas(),
          egresoService.getEgresoEnums(),
        ]);

        setEmpresas(
          (empresasData || []).map((e: any) => ({
            value: e.id,
            label: e.nombre_comercial ?? e.nombre,
          }))
        );

        setCategorias(enumsData.categorias);
        setEstatus(enumsData.estatus);

        if (id) {
          const egresoData = await egresoService.getEgresoById(id);
          setEgreso(egresoData);
          form.setFieldsValue({
            ...egresoData,
            fecha_egreso: egresoData.fecha_egreso ? dayjs(egresoData.fecha_egreso) : null,
          });
        } else {
          form.setFieldsValue({
            fecha_egreso: dayjs(),
            moneda: 'MXN',
            estatus: 'Pendiente',
            categoria: 'Gastos Generales',
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
    onFinish,
  };
};
