// src/pages/conciliacion/index.tsx
'use client';

/** Lista de conciliaciones bancarias, una por mes. */

import React from 'react';
import { useRouter } from 'next/router';
import { PageHeader } from '@/components/PageHeader';
import {
  Button, Card, Empty, Modal, Progress, Space, Table, Tag, Upload, message,
} from 'antd';
import {
  DeleteOutlined, FilePdfOutlined, InboxOutlined, UploadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import conciliacionService, { ConciliacionResumen } from '@/services/conciliacionService';
import { useEmpresaContext } from '@/context/EmpresaContext';
import VisorPdfModal from '@/components/VisorPdfModal';

const dinero = (n: number) =>
  n.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });

const ConciliacionesPage: React.FC = () => {
  const router = useRouter();
  const { selectedEmpresaId } = useEmpresaContext();
  const [items, setItems] = React.useState<ConciliacionResumen[]>([]);
  const [cargando, setCargando] = React.useState(false);
  const [subiendo, setSubiendo] = React.useState(false);
  const [verPdf, setVerPdf] = React.useState<ConciliacionResumen | null>(null);

  const cargar = React.useCallback(async () => {
    if (!selectedEmpresaId) return;
    setCargando(true);
    try {
      setItems(await conciliacionService.listar(selectedEmpresaId));
    } catch (e: any) {
      if (!e?._handled) message.error('No se pudieron cargar las conciliaciones');
    } finally {
      setCargando(false);
    }
  }, [selectedEmpresaId]);

  React.useEffect(() => { cargar(); }, [cargar]);

  const importar = async (archivo: File) => {
    setSubiendo(true);
    try {
      const conc = await conciliacionService.importar(archivo, selectedEmpresaId ?? undefined);
      message.success(
        `Importado: ${conc.total_movimientos} movimientos de ${dayjs(conc.periodo_inicio).format('MMMM YYYY')}`,
      );
      router.push(`/conciliacion/${conc.id}`);
    } catch (e: any) {
      // El backend explica por qué no cuadró; ese texto es el que importa.
      if (!e?._handled) {
        message.error(e?.response?.data?.error?.detail ?? 'No se pudo importar el estado de cuenta');
      }
    } finally {
      setSubiendo(false);
    }
    return false;   // Upload no sube por su cuenta
  };

  const eliminar = (c: ConciliacionResumen) => {
    Modal.confirm({
      title: '¿Eliminar esta conciliación?',
      content: (
        <>
          <p>
            Se borra el trabajo de {dayjs(c.periodo_inicio).format('MMMM YYYY')}:
            los comentarios, las áreas y las facturas enlazadas.
          </p>
          <p>También se borra el PDF del estado de cuenta. Esto no se puede deshacer.</p>
        </>
      ),
      okText: 'Eliminar',
      okButtonProps: { danger: true },
      cancelText: 'Cancelar',
      onOk: async () => {
        await conciliacionService.eliminar(c.id);
        message.success('Conciliación eliminada');
        cargar();
      },
    });
  };

  const columnas = [
    {
      title: 'Periodo',
      key: 'periodo',
      render: (_: unknown, c: ConciliacionResumen) => (
        <a onClick={() => router.push(`/conciliacion/${c.id}`)}>
          <strong style={{ textTransform: 'capitalize' }}>
            {dayjs(c.periodo_inicio).format('MMMM YYYY')}
          </strong>
          <div style={{ fontSize: 12, color: '#888' }}>
            {dayjs(c.periodo_inicio).format('DD/MM')} al {dayjs(c.periodo_fin).format('DD/MM/YYYY')}
          </div>
        </a>
      ),
    },
    {
      title: 'Cuenta',
      key: 'cuenta',
      render: (_: unknown, c: ConciliacionResumen) => (
        <>
          <Tag>{c.banco}</Tag>
          <div style={{ fontSize: 12, color: '#888' }}>{c.cuenta}</div>
        </>
      ),
    },
    {
      title: 'Depósitos',
      key: 'dep',
      align: 'right' as const,
      render: (_: unknown, c: ConciliacionResumen) => (
        <>
          <div style={{ color: '#389e0d' }}>{dinero(c.total_depositos)}</div>
          <div style={{ fontSize: 12, color: '#888' }}>{c.n_depositos} movimientos</div>
        </>
      ),
    },
    {
      title: 'Retiros',
      key: 'ret',
      align: 'right' as const,
      render: (_: unknown, c: ConciliacionResumen) => (
        <>
          <div style={{ color: '#cf1322' }}>{dinero(c.total_retiros)}</div>
          <div style={{ fontSize: 12, color: '#888' }}>{c.n_retiros} movimientos</div>
        </>
      ),
    },
    {
      title: 'Avance',
      key: 'avance',
      width: 200,
      render: (_: unknown, c: ConciliacionResumen) => {
        const pct = c.total_movimientos
          ? Math.round((c.conciliados / c.total_movimientos) * 100) : 0;
        return (
          <>
            <Progress percent={pct} size="small" status={pct === 100 ? 'success' : 'active'} />
            <div style={{ fontSize: 12, color: '#888' }}>
              {c.conciliados} de {c.total_movimientos}
            </div>
          </>
        );
      },
    },
    {
      title: '',
      key: 'acciones',
      width: 90,
      render: (_: unknown, c: ConciliacionResumen) => (
        <Space size={4}>
          {c.tiene_archivo && (
            <Button
              size="small"
              icon={<FilePdfOutlined />}
              title="Ver el estado de cuenta"
              onClick={() => setVerPdf(c)}
            />
          )}
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => eliminar(c)} />
        </Space>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Conciliación bancaria"
        extra={
          <Upload accept=".pdf" showUploadList={false} beforeUpload={importar}>
            <Button type="primary" icon={<UploadOutlined />} loading={subiendo}>
              Subir estado de cuenta
            </Button>
          </Upload>
        }
      />
      <div className="app-content">
        <Card size="small" variant="borderless">
          {items.length === 0 && !cargando ? (
            <Upload.Dragger accept=".pdf" showUploadList={false} beforeUpload={importar}
                            disabled={subiendo} style={{ padding: 24 }}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">Arrastra aquí el estado de cuenta en PDF</p>
              <p className="ant-upload-hint">
                Se leen los movimientos y se comprueba que cuadren con los totales del
                banco. Si algo no cuadra, no se importa y se te dice por qué.
              </p>
            </Upload.Dragger>
          ) : (
            <Table<ConciliacionResumen>
              rowKey="id"
              loading={cargando}
              dataSource={items}
              columns={columnas}
              pagination={false}
              locale={{ emptyText: <Empty description="Sin conciliaciones" /> }}
            />
          )}
        </Card>
      </div>

      <VisorPdfModal
        url={verPdf ? conciliacionService.urlPdf(verPdf.id) : null}
        titulo={verPdf ? `Estado de cuenta · ${dayjs(verPdf.periodo_inicio).format('MMMM YYYY')}` : ''}
        nombreArchivo={verPdf ? `estado-cuenta-${dayjs(verPdf.periodo_inicio).format('YYYY-MM')}.pdf` : ''}
        onClose={() => setVerPdf(null)}
      />
    </>
  );
};

export default ConciliacionesPage;
