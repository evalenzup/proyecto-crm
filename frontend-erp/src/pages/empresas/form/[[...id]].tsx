'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import api from '@/lib/axios';
import {
  Form, Input, Select, Button, Spin, Card, message, Space, Typography, Alert, Upload, Descriptions, Tag,
} from 'antd';
import type { UploadFile } from 'antd';
import { UploadOutlined, DownloadOutlined } from '@ant-design/icons';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { formatDate } from '@/utils/formatDate';
import LogoCropperModal from '@/components/LogoCropperModal';

const { Text } = Typography;

interface JSONSchema { properties: Record<string, any>; required?: string[]; }
const normalizeUploadSingle = (e: any) => (Array.isArray(e) ? e : e?.fileList || []).slice(-1);
const UPPERCASE_FIELDS = ['nombre', 'nombre_comercial', 'rfc', 'ruc', 'direccion'];

type CertInfo = {
  nombre_cn?: string; rfc?: string; curp?: string; numero_serie?: string;
  valido_desde?: string; valido_hasta?: string; issuer_cn?: string;
  key_usage?: string[]; extended_key_usage?: string[]; tipo_cert?: string;
};

const makeNamedFile = (blobOrFile: any, defaultName: string): File => {
  if (blobOrFile instanceof File && blobOrFile.name) return blobOrFile;
  const name = (blobOrFile?.name && typeof blobOrFile.name === 'string') ? blobOrFile.name : defaultName;
  const type = blobOrFile?.type || 'application/octet-stream';
  return new File([blobOrFile], name, { type });
};

const EmpresaFormPage: React.FC = () => {
  const router = useRouter();
  const rawId = router.query.id;
  const id = Array.isArray(rawId) ? rawId[0] : rawId;

  const [form] = Form.useForm();
  const [schema, setSchema] = useState<JSONSchema>({ properties: {}, required: [] });
  const [loadingSchema, setLoadingSchema] = useState(true);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [metadata, setMetadata] = useState<{ creado_en: string; actualizado_en: string } | null>(null);

  const [cerFile, setCerFile] = useState<File | null>(null);
  const [keyFile, setKeyFile] = useState<File | null>(null);

  const [mustReuploadCerts, setMustReuploadCerts] = useState(false);

  const [logoEditorOpen, setLogoEditorOpen] = useState(false);
  const [logoEditorInitial, setLogoEditorInitial] = useState<string | File | Blob | null>(null);
  const [currentLogoUrl, setCurrentLogoUrl] = useState<string | null>(null);

  const [certInfo, setCertInfo] = useState<CertInfo | null>(null);

  const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');

  useEffect(() => {
    api.get<JSONSchema>('/empresas/form-schema')
      .then(({ data }) => setSchema(data))
      .catch(() => message.error('Error al cargar esquema'))
      .finally(() => setLoadingSchema(false));
  }, []);

  useEffect(() => {
    if (!id) return;
    setLoadingRecord(true);
    api.get(`/empresas/${id}`)
      .then(async ({ data }) => {
        const initial: any = { ...data };
        const ts = Date.now();

        if (data.archivo_cer) initial.archivo_cer_file = [{ uid: '-1', name: data.archivo_cer, url: `${API_BASE}/empresas/certificados/${data.archivo_cer}?v=${ts}` }];
        if (data.archivo_key) initial.archivo_key_file = [{ uid: '-1', name: data.archivo_key, url: `${API_BASE}/empresas/certificados/${data.archivo_key}?v=${ts}` }];

        setCurrentLogoUrl(`${API_BASE}/empresas/logos/${id}.png?v=${ts}`);
        form.setFieldsValue(initial);
        setMetadata({ creado_en: data.creado_en, actualizado_en: data.actualizado_en });

        const cerOk = data.archivo_cer
          ? await api.get(`/empresas/certificados/${data.archivo_cer}`, { responseType: 'blob' }).then(() => true).catch(() => false)
          : false;
        const keyOk = data.archivo_key
          ? await api.get(`/empresas/certificados/${data.archivo_key}`, { responseType: 'blob' }).then(() => true).catch(() => false)
          : false;
        const missing = !(cerOk && keyOk);
        setMustReuploadCerts(missing);
        if (missing) {
          form.setFieldsValue({ archivo_cer_file: [], archivo_key_file: [] });
          message.warning('No se encontraron ambos archivos de certificado en el servidor. Debes volver a subir CER y KEY.');
        }

        if (data.archivo_cer && !missing) {
          try {
            const { data: info } = await api.get<CertInfo>(`/empresas/${id}/cert-info`);
            setCertInfo(info);
          } catch { setCertInfo(null); }
        } else {
          setCertInfo(null);
        }
      })
      .catch(() => {
        message.error('Registro no encontrado');
        router.replace('/empresas');
      })
      .finally(() => setLoadingRecord(false));
  }, [id, form, router, API_BASE]);

  const cerList = Form.useWatch('archivo_cer_file', form) as UploadFile[] | undefined;
  const keyList = Form.useWatch('archivo_key_file', form) as UploadFile[] | undefined;
  const pickedBothNew = useMemo(() => {
    const hasNew = (l?: UploadFile[]) => Array.isArray(l) && l.some(f => (f as any)?.originFileObj);
    return hasNew(cerList) && hasNew(keyList);
  }, [cerList, keyList]);

  const needPassword = id ? (mustReuploadCerts || pickedBothNew || !!(cerFile && keyFile)) : true;

  const openLogoEditor = () => {
    const list = (form.getFieldValue('logo_file') as UploadFile[] | undefined) || [];
    const f = list[0] as any;
    const src = f?.originFileObj ? (f.originFileObj as File) : (currentLogoUrl || null);
    setLogoEditorInitial(src);
    setLogoEditorOpen(true);
  };
  const onLogoCropped = (file: File, previewURL: string) => {
    const fileList: UploadFile[] = [{ uid: String(Date.now()), name: file.name, status: 'done', originFileObj: file as any, thumbUrl: previewURL } as any];
    form.setFieldsValue({ logo_file: fileList });
    setLogoEditorOpen(false);
    setCurrentLogoUrl(previewURL);
    message.success('Logo recortado listo para guardar.');
  };

  const onFinish = async (values: any) => {
    const payload = new FormData();

    const empresaData: Record<string, any> = {};
    Object.entries(values).forEach(([k, v]) => {
      if (k.endsWith('_file')) return;
      if (v !== undefined && v !== null && v !== '') empresaData[k] = v;
    });
    payload.append('empresa_data', JSON.stringify(empresaData));

    const firstNew = (list?: UploadFile[]) =>
      (list || []).find((f: any) => !!f?.originFileObj) as UploadFile | undefined;
    const logoUF = firstNew(values.logo_file);
    const logoBlob = logoUF && (logoUF as any).originFileObj;

    if ((cerFile && !keyFile) || (!cerFile && keyFile)) {
      message.error('Si actualizas certificados, sube ambos archivos: CER y KEY.');
      return;
    }
    if (id && mustReuploadCerts && !(cerFile && keyFile)) {
      message.error('Faltan certificados en el servidor. Debes subir CER y KEY para continuar.');
      return;
    }
    const needsPasswordNow = mustReuploadCerts || (!!cerFile && !!keyFile) || !id;
    if (needsPasswordNow && !empresaData.contrasena) {
      message.error('Debes capturar la contraseña para validar los certificados.');
      return;
    }

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
        await api.put(`/empresas/${id}`, payload);
        message.success('Empresa actualizada');
      } else {
        await api.post(`/empresas/`, payload);
        message.success('Empresa creada');
      }
      router.push('/empresas');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((e: any) => e.msg).join(', ') : 'Error inesperado');
    }
  };

  if (loadingSchema || loadingRecord) {
    return <Spin spinning tip="Cargando..."><div style={{ minHeight: 200 }} /></Spin>;
  }

  const expWarning = (() => {
    if (!certInfo?.valido_hasta) return null;
    try {
      const exp = new Date(certInfo.valido_hasta).getTime();
      const now = Date.now();
      const days = Math.ceil((exp - now) / (1000 * 60 * 60 * 24));
      if (days <= 30) return `El certificado vence en ${days} día(s).`;
    } catch {}
    return null;
  })();

  const CertInfoBlock: React.FC = () => {
    if (!id || !certInfo) return null;
    return (
      <Card size="small" style={{ marginTop: 8, marginBottom: 12 }}>
        <Space style={{ marginBottom: 8 }}>
          <Text strong>Información del certificado</Text>
          {certInfo.tipo_cert && (
            <Tag color={certInfo.tipo_cert === 'CSD' ? 'processing' : certInfo.tipo_cert === 'FIEL' ? 'success' : 'default'}>
              {certInfo.tipo_cert}
            </Tag>
          )}
        </Space>
        {expWarning && <Alert style={{ marginBottom: 8 }} type="warning" showIcon message={expWarning} />}
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="Nombre (CN)">{certInfo.nombre_cn || '-'}</Descriptions.Item>
          <Descriptions.Item label="RFC">{certInfo.rfc || '-'}</Descriptions.Item>
          <Descriptions.Item label="CURP">{certInfo.curp || '-'}</Descriptions.Item>
          <Descriptions.Item label="No. de serie">{certInfo.numero_serie || '-'}</Descriptions.Item>
          <Descriptions.Item label="Emisor (CN)">{certInfo.issuer_cn || '-'}</Descriptions.Item>
          <Descriptions.Item label="Key Usage">{certInfo.key_usage?.join(', ') || '-'}</Descriptions.Item>
          <Descriptions.Item label="Extended Key Usage">{certInfo.extended_key_usage?.join(', ') || '-'}</Descriptions.Item>
          <Descriptions.Item label="Válido desde">{certInfo.valido_desde ? formatDate(certInfo.valido_desde) : '-'}</Descriptions.Item>
          <Descriptions.Item label="Válido hasta">{certInfo.valido_hasta ? formatDate(certInfo.valido_hasta) : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>
    );
  };

  const renderField = (key: string, prop: any) => {
    const required = schema.required?.includes(key);

    if (key === 'logo') {
      return (
        <Form.Item key={key} label={prop.title}>
          <Space wrap>
            <Button icon={<UploadOutlined />} onClick={openLogoEditor}>Subir logo</Button>
            {id && (
              <a href={`${API_BASE}/empresas/logos/${id}.png?v=${Date.now()}`} target="_blank" rel="noopener noreferrer">
                <Button icon={<DownloadOutlined />} type="link">Descargar logo actual</Button>
              </a>
            )}
            {currentLogoUrl && <img src={currentLogoUrl} alt="preview logo" style={{ height: 40, borderRadius: 6, border: '1px solid #eee', marginLeft: 8 }} />}
          </Space>
          <Form.Item name="logo_file" valuePropName="fileList" getValueFromEvent={normalizeUploadSingle} style={{ display: 'none' }}>
            <Upload beforeUpload={() => false} />
          </Form.Item>
        </Form.Item>
      );
    }

    if ((prop as any).format === 'binary') {
      const isCer = key === 'archivo_cer';
      const isKey = key === 'archivo_key';
      const accept = isCer ? '.cer' : isKey ? '.key' : 'image/*';
      const ext = isCer ? 'cer' : isKey ? 'key' : 'png';

      return (
        <Form.Item
          key={key}
          label={prop.title}
          name={`${key}_file`}
          valuePropName="fileList"
          getValueFromEvent={normalizeUploadSingle}
          rules={required ? [{ required: true, message: `Se requiere ${prop.title}` }] : []}
        >
          <>
            <Upload
              maxCount={1}
              multiple={false}
              accept={accept}
              beforeUpload={(file) => {
                const named = makeNamedFile(file, `${id || 'empresa'}.${ext}`);
                if (isCer) setCerFile(named);
                if (isKey) setKeyFile(named);
                return false;
              }}
              onRemove={() => {
                if (isCer) setCerFile(null);
                if (isKey) setKeyFile(null);
                return true;
              }}
            >
              <Button icon={<UploadOutlined />}>Subir {prop.title}</Button>
            </Upload>

            {id && (isCer || isKey) && !mustReuploadCerts && (
              (() => {
                const current = (form.getFieldValue(`${key}_file`) as any[] | undefined)?.[0];
                const fileName = current?.name || `${id}.${ext}`;
                return (
                  <a href={`${API_BASE}/empresas/certificados/${fileName}?v=${Date.now()}`} target="_blank" rel="noopener noreferrer" style={{ display: 'block', marginTop: 8 }}>
                    <Button icon={<DownloadOutlined />} type="link">Descargar {prop.title}</Button>
                  </a>
                );
              })()
            )}
          </>
        </Form.Item>
      );
    }

    if ((prop as any).enum || (prop as any)['x-options']) {
      return (
        <Form.Item key={key} label={prop.title} name={key} rules={schema.required?.includes(key) ? [{ required: true, message: `Se requiere ${prop.title}` }] : []}>
          <Select>
            {(prop as any)['x-options']?.map((opt: any) => (
              <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
            ))}
          </Select>
        </Form.Item>
      );
    }

    // Campo contraseña normal
    if (key === 'contrasena') {
      return (
        <Form.Item
          key={key}
          label={prop.title || 'Contraseña del CSD (.key)'}
          name={key}
          rules={needPassword ? [{ required: true, message: 'Requerida para validar certificados' }] : []}
        >
          <Input maxLength={(schema.properties?.contrasena as any)?.maxLength || 255} />
        </Form.Item>
      );
    }

    return (
      <Form.Item
        key={key}
        label={prop.title}
        name={key}
        rules={schema.required?.includes(key) ? [{ required: true, message: `Se requiere ${prop.title}` }] : []}
        getValueFromEvent={(e) => {
          const val = e?.target?.value;
          return UPPERCASE_FIELDS.includes(key) && val != null ? String(val).toUpperCase() : val;
        }}
      >
        <Input
          maxLength={(prop as any).maxLength}
          type={(prop as any).format === 'password' ? 'password' : 'text'}
          style={UPPERCASE_FIELDS.includes(key) ? { textTransform: 'uppercase' } : undefined}
        />
      </Form.Item>
    );
  };

  // Orden: todos los campos normales primero; al final → CER, KEY, CONTRASEÑA, CertInfo
  const keysAll = Object.keys(schema.properties || {});
  const certKeys = ['archivo_cer', 'archivo_key', 'contrasena'];
  const normalKeys = keysAll.filter(k => !certKeys.includes(k));
  const certKeysPresent = certKeys.filter(k => keysAll.includes(k));

  return (
    <>
      <div className="app-page-header">
        <div className="app-page-header__left">
          <Breadcrumbs />
          <h1 className="app-title">{id ? 'Editar Empresa' : 'Nueva Empresa'}</h1>
        </div>
      </div>

      <div className="app-content">
        <Card>
          {metadata && (
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: '0.85em' }}>
                Creado: {formatDate(metadata.creado_en)} &nbsp;|&nbsp; Actualizado: {formatDate(metadata.actualizado_en)}
              </Text>
            </div>
          )}

          {id && mustReuploadCerts && (
            <Alert style={{ marginBottom: 12 }} type="warning" showIcon message="Faltan certificados en el servidor" description="Para guardar cambios debes volver a subir los archivos CER y KEY." />
          )}

          <Form form={form} layout="vertical" onFinish={onFinish}>
            {/* Campos normales primero */}
            {normalKeys.map((k) => renderField(k, (schema.properties as any)[k]))}

            {/* Bloque de certificados al final */}
            <Card size="small" style={{ marginTop: 16 }}>
              <Text strong>Certificados</Text>
              <div style={{ height: 8 }} />
              {certKeysPresent
                .filter(k => k !== 'contrasena')
                .map((k) => renderField(k, (schema.properties as any)[k]))}
              {/* Contraseña del CSD */}
              {certKeysPresent.includes('contrasena') && renderField('contrasena', (schema.properties as any)['contrasena'])}
              {/* Info del certificado */}
              <CertInfoBlock />
            </Card>

            <Form.Item style={{ marginTop: 16 }}>
              <Space>
                <Button onClick={() => router.push('/empresas')}>Cancelar</Button>
                <Button type="primary" htmlType="submit">{id ? 'Actualizar' : 'Guardar'}</Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      </div>

      <LogoCropperModal
        open={logoEditorOpen}
        initialImage={logoEditorInitial}
        onClose={() => setLogoEditorOpen(false)}
        onConfirm={onLogoCropped}
        empresaId={id || 'empresa'}
        initialImageUrl={id ? `${API_BASE}/empresas/logos/${id}.png` : undefined}
      />
    </>
  );
};

export default EmpresaFormPage;