// frontend-erp/src/hooks/useEmpresaForm.ts
import { useEffect, useState, useMemo } from 'react';
import { message, Form } from 'antd';
import type { UploadFile } from 'antd';
import { empresaService } from '../services/empresaService';
import { CertInfoOut, EmpresaOut } from '../services/empresaService'; // Reutilizamos las interfaces del servicio
import { useRouter } from 'next/router'; // Para redirección
import { normalizeHttpError } from '@/utils/httpError';
import { applyFormErrors } from '@/utils/formErrors';

interface EmpresaFormData {
  // Campos del formulario, incluyendo los de EmpresaCreate/Update
  // y los archivos de subida
  id?: string;
  nombre?: string;
  nombre_comercial?: string;
  rfc?: string;
  ruc?: string;
  direccion?: string;
  telefono?: string;
  email?: string;
  regimen_fiscal?: string;
  codigo_postal?: string;
  contrasena?: string;
  archivo_cer_file?: UploadFile[];
  archivo_key_file?: UploadFile[];
  logo_file?: UploadFile[];
}

interface UseEmpresaFormResult {
  form: any; // Ant Design Form instance
  schema: any; // JSON Schema for form rendering
  loading: boolean;
  metadata: { creado_en: string; actualizado_en: string } | null;
  cerFile: File | null;
  setCerFile: (file: File | null) => void;
  keyFile: File | null;
  setKeyFile: (file: File | null) => void;
  logoEditorOpen: boolean;
  setLogoEditorOpen: (open: boolean) => void;
  logoEditorInitial: string | File | Blob | null;
  currentLogoUrl: string | null;
  certInfo: CertInfoOut | null;
  mustReuploadCerts: boolean;
  needPassword: boolean;
  onFinish: (values: EmpresaFormData) => Promise<void>;
  onLogoCropped: (file: File, previewURL: string) => void;
  API_BASE: string;
}

const makeNamedFile = (blobOrFile: any, defaultName: string): File => {
  if (blobOrFile instanceof File && blobOrFile.name) return blobOrFile;
  const name = (blobOrFile?.name && typeof blobOrFile.name === 'string') ? blobOrFile.name : defaultName;
  const type = blobOrFile?.type || 'application/octet-stream';
  return new File([blobOrFile], name, { type });
};

export const useEmpresaForm = (id?: string): UseEmpresaFormResult => {
  const [form] = Form.useForm();
  const router = useRouter();

  const [schema, setSchema] = useState<any>({ properties: {}, required: [] });
  const [loadingSchema, setLoadingSchema] = useState(true);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);

  const [cerFile, setCerFile] = useState<File | null>(null);
  const [keyFile, setKeyFile] = useState<File | null>(null);
  const [mustReuploadCerts, setMustReuploadCerts] = useState(false);

  const [logoEditorOpen, setLogoEditorOpen] = useState(false);
  const [logoEditorInitial, setLogoEditorInitial] = useState<string | File | Blob | null>(null);
  const [currentLogoUrl, setCurrentLogoUrl] = useState<string | null>(null);

  const [certInfo, setCertInfo] = useState<CertInfoOut | null>(null);

  const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');

  // Cargar esquema del formulario
  useEffect(() => {
    empresaService.getEmpresaSchema()
      .then(setSchema)
      .catch((e) => message.error(normalizeHttpError(e)))
      .finally(() => setLoadingSchema(false));
  }, []);

  // Cargar datos del registro si es edición
  useEffect(() => {
    if (!id) return;
    setLoadingRecord(true);
    empresaService.getEmpresa(id)
      .then(async (data: EmpresaOut) => {
        const initial: any = { ...data };
        const ts = Date.now();

        // Pre-llenar campos de archivo para Ant Design
        if (data.archivo_cer) initial.archivo_cer_file = [{ uid: '-1', name: data.archivo_cer, url: empresaService.descargarCertificado(data.archivo_cer) + `?v=${ts}` }];
        if (data.archivo_key) initial.archivo_key_file = [{ uid: '-1', name: data.archivo_key, url: empresaService.descargarCertificado(data.archivo_key) + `?v=${ts}` }];

        setCurrentLogoUrl(empresaService.descargarLogo(id) + `?v=${ts}`);
        form.setFieldsValue(initial);
        setMetadata({ creado_en: data.creado_en, actualizado_en: data.actualizado_en });

        // Verificar si los archivos de certificado existen en el servidor
        const cerOk = data.archivo_cer
          ? await fetch(empresaService.descargarCertificado(data.archivo_cer)).then(res => res.ok).catch(() => false)
          : false;
        const keyOk = data.archivo_key
          ? await fetch(empresaService.descargarCertificado(data.archivo_key)).then(res => res.ok).catch(() => false)
          : false;
        const missing = !(cerOk && keyOk);
        setMustReuploadCerts(missing);
        if (missing) {
          form.setFieldsValue({ archivo_cer_file: [], archivo_key_file: [] });
          message.warning('No se encontraron ambos archivos de certificado en el servidor. Debes volver a subir CER y KEY.');
        }

        // Obtener información del certificado si existe y no falta
        if (data.archivo_cer && !missing) {
          try {
            const info = await empresaService.getCertInfo(id);
            setCertInfo(info);
          } catch { setCertInfo(null); }
        } else {
          setCertInfo(null);
        }
      })
      .catch((e) => {
        message.error(normalizeHttpError(e) || 'Registro no encontrado');
        router.replace('/empresas'); // Redirigir si no se encuentra el registro
      })
      .finally(() => setLoadingRecord(false));
  }, [id, form, router]);

  // Lógica para determinar si se necesita la contraseña
  const cerList = Form.useWatch('archivo_cer_file', form) as UploadFile[] | undefined;
  const keyList = Form.useWatch('archivo_key_file', form) as UploadFile[] | undefined;
  const pickedBothNew = useMemo(() => {
    const hasNew = (l?: UploadFile[]) => Array.isArray(l) && l.some(f => (f as any)?.originFileObj);
    return hasNew(cerList) && hasNew(keyList);
  }, [cerList, keyList]);

  const needPassword = id ? (mustReuploadCerts || pickedBothNew || !!(cerFile && keyFile)) : true;

  // Manejo del logo
  const onLogoCropped = (file: File, previewURL: string) => {
    const fileList: UploadFile[] = [{ uid: String(Date.now()), name: file.name, status: 'done', originFileObj: file as any, thumbUrl: previewURL } as any];
    form.setFieldsValue({ logo_file: fileList });
    setLogoEditorOpen(false);
    setCurrentLogoUrl(previewURL);
    message.success('Logo recortado listo para guardar.');
  };

  // Manejo del envío del formulario
  const onFinish = async (values: EmpresaFormData) => {
    const payload = new FormData();

    const empresaData: Record<string, any> = {};
    Object.entries(values).forEach(([k, v]) => {
      if (k.endsWith('_file')) return; // Ignorar campos de archivo
      if (v !== undefined && v !== null && v !== '') empresaData[k] = v;
    });
    payload.append('empresa_data', JSON.stringify(empresaData));

    const firstNew = (list?: UploadFile[]) =>
      (list || []).find((f: any) => !!f?.originFileObj) as UploadFile | undefined;
    const logoUF = firstNew(values.logo_file);
    const logoBlob = logoUF && (logoUF as any).originFileObj;

    // Validaciones de certificados y contraseña
    if ((cerFile && !keyFile) || (!cerFile && keyFile)) {
      message.error('Si actualizas certificados, sube ambos archivos: CER y KEY.');
      return;
    }
    if (id && mustReuploadCerts && !(cerFile && keyFile)) {
      message.error('Faltan certificados en el servidor. Debes subir CER y KEY para continuar.');
      return;
    }
    if (needPassword && !empresaData.contrasena) {
      message.error('Debes capturar la contraseña para validar los certificados.');
      return;
    }

    // Adjuntar archivos al FormData
    if (cerFile && keyFile) {
      const cerNamed = makeNamedFile(cerFile, `${id || 'empresa'}.cer`);
      const keyNamed = makeNamedFile(keyFile, `${id || 'empresa'}.key`);
      payload.append('archivo_cer', cerNamed, cerNamed.name);
      payload.append('archivo_key', keyNamed, keyNamed.name);
    }
    if (logoBlob) {
      const logoFile = makeNamedFile(logoBlob, `${id || 'empresa'}.png`);
      payload.append('logo', logoFile, logoFile.name);
    }

    try {
      if (id) {
        await empresaService.updateEmpresa(id, payload);
        message.success('Empresa actualizada');
      } else {
        await empresaService.createEmpresa(payload);
        message.success('Empresa creada');
      }
      router.push('/empresas'); // Redirigir al listado
    } catch (err: any) {
      // Marcar errores de validación en campos y mostrar mensaje amigable
      applyFormErrors(err, form);
      message.error(normalizeHttpError(err));
    }
  };

  return {
    form,
    schema,
    loading: loadingSchema || loadingRecord,
    metadata,
    cerFile,
    setCerFile,
    keyFile,
    setKeyFile,
    logoEditorOpen,
    setLogoEditorOpen,
    logoEditorInitial: logoEditorInitial,
    currentLogoUrl,
    certInfo,
    mustReuploadCerts,
    needPassword,
    onFinish,
    onLogoCropped,
    API_BASE,
  };
};
