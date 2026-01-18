import React, { useEffect, useState } from 'react';
import { Table, Card, Row, Col, Typography, Statistic, Tag, Button, Tooltip, message, Select, Modal, Form, Input } from 'antd';
import { DollarOutlined, SolutionOutlined, CommentOutlined, WarningOutlined, FilePdfOutlined, MailOutlined } from '@ant-design/icons';
import { AgingReportResponse, ClienteAging } from '@/types/cobranza';
import { getAgingReport, fetchEstadoCuentaBlob, sendEstadoCuentaEmail } from '@/services/cobranzaService';
import Notas from '@/components/Cobranza/Notas';
import CobranzaDashboard from '@/components/Cobranza/Dashboard';
import { formatCurrency } from '@/utils/format';

import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';

const { Title, Text } = Typography;

const CobranzaPage: React.FC = () => {
    const { selectedEmpresaId, empresas, setSelectedEmpresaId, isAdmin } = useEmpresaSelector();
    const [data, setData] = useState<AgingReportResponse | null>(null);
    const [loading, setLoading] = useState(true);

    // Notas Modal State
    const [notasVisible, setNotasVisible] = useState(false);
    const [selectedCliente, setSelectedCliente] = useState<{ id: string, nombre: string } | null>(null);

    const fetchData = async () => {
        if (!selectedEmpresaId) return;
        setLoading(true);
        try {
            const result = await getAgingReport(selectedEmpresaId);
            setData(result);
        } catch (error) {
            console.error(error);
            message.error("Error al cargar reporte de antigüedad");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (selectedEmpresaId) {
            fetchData();
        }
    }, [selectedEmpresaId]);

    const handleOpenNotas = (record: ClienteAging) => {
        setSelectedCliente({ id: record.cliente_id, nombre: record.nombre_cliente });
        setNotasVisible(true);
    };

    // Preview
    const [previewOpen, setPreviewOpen] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [previewCliente, setPreviewCliente] = useState<{ nombre: string } | null>(null);

    const handlePreviewEstadoCuenta = async (record: ClienteAging) => {
        try {
            message.loading({ content: 'Generando PDF...', key: 'pdfGen' });
            const blob = await fetchEstadoCuentaBlob(record.cliente_id, selectedEmpresaId);
            const url = window.URL.createObjectURL(blob);
            setPreviewUrl(url);
            setPreviewCliente({ nombre: record.nombre_cliente });
            setPreviewOpen(true);
            message.success({ content: 'Listo', key: 'pdfGen' });
        } catch (e) {
            console.error(e);
            message.error({ content: 'Error al generar PDF', key: 'pdfGen' });
        }
    };

    // Email
    const [emailModalOpen, setEmailModalOpen] = useState(false);
    const [emailLoading, setEmailLoading] = useState(false);
    const [emailRow, setEmailRow] = useState<ClienteAging | null>(null);
    const [emailForm] = Form.useForm();

    const handleOpenEmail = (record: ClienteAging) => {
        setEmailRow(record);
        if (record.email) {
            emailForm.setFieldsValue({ recipient_emails: record.email });
        } else {
            emailForm.resetFields(['recipient_emails']);
        }
        setEmailModalOpen(true);
    };

    const handleEmailSubmit = (values: { recipient_emails: string }) => {
        if (!emailRow) return;
        const recips = (values.recipient_emails || '').split(/[;,\n]+/).map(r => r.trim()).filter(Boolean);

        if (recips.length === 0) {
            message.error("Ingrese al menos un correo");
            return;
        }

        setEmailLoading(true);
        sendEstadoCuentaEmail(emailRow.cliente_id, recips, selectedEmpresaId)
            .then(() => {
                message.success('Estado de Cuenta enviado por correo.');
                setEmailModalOpen(false);
                emailForm.resetFields();
            })
            .catch((e: any) => {
                console.error(e);
                message.error('Error al enviar correo.');
            })
            .finally(() => setEmailLoading(false));
    };

    const columns = [
        {
            title: 'Cliente',
            dataIndex: 'nombre_cliente',
            key: 'nombre_cliente',
            render: (text: string, record: ClienteAging) => (
                <div>
                    <div style={{ fontWeight: 'bold' }}>{text}</div>
                    {record.rfc && <div style={{ fontSize: 12, color: '#888' }}>{record.rfc}</div>}
                    {record.nota_mas_reciente && (
                        <div style={{ fontSize: 11, color: '#1890ff', fontStyle: 'italic', marginTop: 4 }}>
                            <CommentOutlined /> {record.nota_mas_reciente.substring(0, 50)}...
                        </div>
                    )}
                </div>
            )
        },
        {
            title: 'Total Deuda',
            dataIndex: 'total_deuda',
            key: 'total_deuda',
            align: 'right' as const,
            sorter: (a: ClienteAging, b: ClienteAging) => a.total_deuda - b.total_deuda,
            render: (val: number) => <Text strong>{formatCurrency(val)}</Text>
        },
        {
            title: 'Por Vencer',
            dataIndex: 'por_vencer',
            key: 'por_vencer',
            align: 'right' as const,
            render: (val: number) => val > 0 ? formatCurrency(val) : '-'
        },
        {
            title: '0-30 Días',
            dataIndex: 'vencido_0_30',
            key: 'vencido_0_30',
            align: 'right' as const,
            render: (val: number) => val > 0 ? <Tag color="gold">{formatCurrency(val)}</Tag> : '-'
        },
        {
            title: '31-60 Días',
            dataIndex: 'vencido_31_60',
            key: 'vencido_31_60',
            align: 'right' as const,
            render: (val: number) => val > 0 ? <Tag color="orange">{formatCurrency(val)}</Tag> : '-'
        },
        {
            title: '61-90 Días',
            dataIndex: 'vencido_61_90',
            key: 'vencido_61_90',
            align: 'right' as const,
            render: (val: number) => val > 0 ? <Tag color="volcano">{formatCurrency(val)}</Tag> : '-'
        },
        {
            title: '> 90 Días',
            dataIndex: 'vencido_mas_90',
            key: 'vencido_mas_90',
            align: 'right' as const,
            render: (val: number) => val > 0 ? <Tag color="red">{formatCurrency(val)}</Tag> : '-'
        },
        {
            title: 'Acciones',
            key: 'acciones',
            align: 'center' as const,
            render: (_: any, record: ClienteAging) => (
                <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                    <Tooltip title="Descargar Estado de Cuenta">
                        <Button
                            icon={<FilePdfOutlined />}
                            danger
                            onClick={() => handlePreviewEstadoCuenta(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Enviar por Correo">
                        <Button
                            icon={<MailOutlined />}
                            onClick={() => handleOpenEmail(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Ver Bitácora / Agregar Nota">
                        <Button
                            icon={<SolutionOutlined />}
                            onClick={() => handleOpenNotas(record)}
                        />
                    </Tooltip>
                </div>
            )
        }
    ];

    return (
        <div style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <Title level={2} style={{ margin: 0 }}>
                    <WarningOutlined style={{ marginRight: 10 }} />
                    Cobranza y Antigüedad de Saldos
                </Title>
                {isAdmin && (
                    <Select
                        value={selectedEmpresaId}
                        onChange={setSelectedEmpresaId}
                        style={{ width: 250 }}
                        placeholder="Seleccionar Empresa"
                        options={empresas.map(e => ({
                            label: e.nombre_comercial || e.nombre,
                            value: e.id
                        }))}
                    />
                )}
            </div>

            <CobranzaDashboard data={data} loading={loading} />

            <Card title="Detalle por Cliente" bordered={false}>

                <Table
                    columns={columns}
                    dataSource={data?.items || []}
                    rowKey="cliente_id"
                    loading={loading}
                    pagination={{
                        defaultPageSize: 20,
                        showSizeChanger: true,
                        pageSizeOptions: ['10', '20', '50', '100'],
                        showTotal: (total, range) => `${range[0]}-${range[1]} de ${total} clientes`,
                    }}
                    bordered
                />
            </Card>

            {selectedCliente && (
                <Notas
                    visible={notasVisible}
                    onClose={() => setNotasVisible(false)}
                    clienteId={selectedCliente.id}
                    clienteNombre={selectedCliente.nombre}
                    empresaId={selectedEmpresaId}
                />
            )}

            <Modal
                title="Vista Previa de Estado de Cuenta"
                open={previewOpen}
                onCancel={() => {
                    setPreviewOpen(false);
                    // Optional: release blob URL if needed
                }}
                footer={[
                    <Button key="close" onClick={() => setPreviewOpen(false)}>Cerrar</Button>,
                    <Button
                        key="download"
                        type="primary"
                        icon={<FilePdfOutlined />}
                        onClick={() => {
                            if (previewUrl) {
                                const a = document.createElement('a');
                                a.href = previewUrl;
                                a.download = `estado_cuenta_${previewCliente?.nombre || 'cliente'}.pdf`;
                                a.click();
                            }
                        }}
                    >
                        Descargar
                    </Button>
                ]}
                width="80%"
                style={{ top: 20 }}
                styles={{ body: { height: '80vh', padding: 0 } }}
                destroyOnHidden
            >
                {previewUrl && (
                    <iframe
                        src={previewUrl}
                        style={{ width: '100%', height: '100%', border: 'none' }}
                        title="Estado de Cuenta"
                    />
                )}
            </Modal>

            <Modal
                title={`Enviar Estado de Cuenta - ${emailRow?.nombre_cliente || ''}`}
                open={emailModalOpen}
                onCancel={() => {
                    setEmailModalOpen(false);
                    emailForm.resetFields();
                }}
                onOk={() => emailForm.submit()}
                confirmLoading={emailLoading}
                okText="Enviar"
                cancelText="Cancelar"
            >
                <Form form={emailForm} layout="vertical" onFinish={handleEmailSubmit}>
                    <Form.Item
                        label="Correos del Destinatario (separados por coma)"
                        name="recipient_emails"
                        rules={[{ required: true, message: 'Ingrese al menos un destinatario' }]}
                    >
                        <Input.TextArea rows={4} placeholder="cliente@empresa.com, pagos@empresa.com" />
                    </Form.Item>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        Se adjuntará automáticamente el PDF del Estado de Cuenta.
                    </Typography.Text>
                </Form>
            </Modal>
        </div>
    );
};

export default CobranzaPage;
