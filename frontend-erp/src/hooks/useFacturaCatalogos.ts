// Fetches and holds all SAT catalog option lists needed by the factura form
import { useState } from 'react';
import * as svc from '@/services/facturaService';

interface Opcion { value: string; label: string }

const toOpts = (list: any[], key = 'clave') =>
  (list || []).map((x: any) => ({ value: x[key], label: `${x[key]} — ${x.descripcion}` }));

export const useFacturaCatalogos = () => {
  const [empresas, setEmpresas] = useState<Opcion[]>([]);
  const [regimenes, setRegimenes] = useState<Opcion[]>([]);
  const [metodosPago, setMetodosPago] = useState<Opcion[]>([]);
  const [formasPago, setFormasPago] = useState<Opcion[]>([]);
  const [usosCfdi, setUsosCfdi] = useState<Opcion[]>([]);
  const [tiposRelacion, setTiposRelacion] = useState<Opcion[]>([]);
  const [motivosCancel, setMotivosCancel] = useState<Opcion[]>([]);

  /**
   * Fetches all catalogs in parallel.
   * Returns the processed empresa options so the caller can do auto-selection.
   */
  const fetchCatalogos = async (): Promise<Opcion[]> => {
    const [empresasData, mpData, fpData, ucData, rfData, trData, mcData] = await Promise.all([
      svc.getEmpresas(),
      svc.getMetodosPago(),
      svc.getFormasPago(),
      svc.getUsosCfdi(),
      svc.getRegimenesFiscales(),
      svc.getTiposRelacion(),
      svc.getMotivosCancelacion(),
    ]);

    const empOptions = (empresasData || []).map((e: any) => ({
      value: e.id,
      label: e.nombre_comercial ?? e.nombre,
    }));

    setEmpresas(empOptions);
    setMetodosPago(toOpts(mpData));
    setFormasPago(toOpts(fpData));
    setUsosCfdi(toOpts(ucData));
    setRegimenes(toOpts(rfData));
    setTiposRelacion(toOpts(trData));
    setMotivosCancel(toOpts(mcData));

    return empOptions;
  };

  return {
    empresas,
    regimenes,
    metodosPago,
    formasPago,
    usosCfdi,
    tiposRelacion,
    motivosCancel,
    fetchCatalogos,
  };
};
