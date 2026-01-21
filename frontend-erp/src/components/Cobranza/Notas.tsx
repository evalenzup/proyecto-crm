import React, { useEffect, useState } from 'react';
import { formatDate } from '@/utils/formatDate';
import { Modal, List, Input, Button, DatePicker, message, Timeline, Typography, Empty, Avatar, Popconfirm } from 'antd';
import { UserOutlined, ClockCircleOutlined, SaveOutlined, DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { CobranzaNota, CobranzaNotaCreate } from '@/types/cobranza';
import { createNota, getNotasByCliente, deleteNota } from '@/services/cobranzaService';
import { useAuth } from '@/context/AuthContext';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Text } = Typography;

interface NotasProps {
    visible: boolean;
    onClose: () => void;
    clienteId: string;
    clienteNombre: string;
    empresaId?: string;
}

const Notas: React.FC<NotasProps> = ({ visible, onClose, clienteId, clienteNombre, empresaId }) => {
    const [notas, setNotas] = useState<CobranzaNota[]>([]);
    const [loading, setLoading] = useState(false);
    const { user } = useAuth();

    // Form states
    const [newNota, setNewNota] = useState('');
    const [promesaFecha, setPromesaFecha] = useState<dayjs.Dayjs | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const fetchNotas = async () => {
        if (!clienteId) return;
        setLoading(true);
        try {
            const data = await getNotasByCliente(clienteId, empresaId);
            setNotas(data);
        } catch (error) {
            console.error(error);
            message.error("Error al cargar notas");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (visible && clienteId) {
            fetchNotas();
            setNewNota('');
            setPromesaFecha(null);
        }
    }, [visible, clienteId, empresaId]);

    const handleSubmit = async () => {
        if (!newNota.trim()) {
            message.warning("Escribe una nota");
            return;
        }

        setSubmitting(true);
        try {
            const payload: CobranzaNotaCreate = {
                cliente_id: clienteId,
                nota: newNota,
                fecha_promesa_pago: promesaFecha ? promesaFecha.toISOString() : undefined
            };

            await createNota(payload, empresaId);
            message.success("Nota guardada");
            setNewNota('');
            setPromesaFecha(null);
            await fetchNotas(); // Refresh list
        } catch (error) {
            console.error(error);
            message.error("Error al guardar nota");
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = (notaId: string) => {
        Modal.confirm({
            title: '¿Eliminar nota?',
            icon: <ExclamationCircleOutlined />,
            content: 'Esta acción no se puede deshacer.',
            okText: 'Eliminar',
            okType: 'danger',
            cancelText: 'Cancelar',
            onOk: async () => {
                try {
                    await deleteNota(notaId);
                    message.success('Nota eliminada');
                    fetchNotas();
                } catch (error) {
                    console.error(error);
                    message.error('Error al eliminar nota');
                }
            }
        });
    };

    return (
        <Modal
            title={`Bitácora de Cobranza: ${clienteNombre}`}
            open={visible}
            onCancel={onClose}
            footer={null}
            width={700}
        >
            <div style={{ marginBottom: 20, background: '#f5f5f5', padding: 15, borderRadius: 8 }}>
                <Typography.Title level={5}>Nueva Nota / Seguimiento</Typography.Title>
                <TextArea
                    rows={3}
                    placeholder="Escribe el resultado de la llamada, correo, etc..."
                    value={newNota}
                    onChange={(e) => setNewNota(e.target.value)}
                    style={{ marginBottom: 10 }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <span style={{ marginRight: 10 }}>Promesa de Pago:</span>
                        <DatePicker
                            onChange={setPromesaFecha}
                            value={promesaFecha}
                            placeholder="Fecha comprometida"
                            style={{ width: 200 }}
                        />
                    </div>
                    <Button
                        type="primary"
                        icon={<SaveOutlined />}
                        onClick={handleSubmit}
                        loading={submitting}
                    >
                        Guardar Nota
                    </Button>
                </div>
            </div>

            <Typography.Title level={5} style={{ marginTop: 20 }}>Historial</Typography.Title>

            {loading ? (
                <div>Cargando historial...</div>
            ) : notas.length === 0 ? (
                <Empty description="No hay notas registradas" />
            ) : (
                <div style={{ maxHeight: 400, overflowY: 'auto', paddingRight: 10 }}>
                    <Timeline>
                        {notas.map(nota => (
                            <Timeline.Item
                                key={nota.id}
                                color={nota.fecha_promesa_pago ? "green" : "blue"}
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, paddingTop: 4 }}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                        {formatDate(nota.creado_en)}
                                    </Text>
                                    <Text strong style={{ fontSize: 13 }}>
                                        {nota.nombre_creador || "Usuario"}
                                    </Text>
                                    {(user?.rol === 'admin' || user?.id === nota.creado_po) && (
                                        <Button
                                            type="text"
                                            danger
                                            size="small"
                                            icon={<DeleteOutlined />}
                                            onClick={() => handleDelete(nota.id)}
                                            style={{ marginLeft: 8 }}
                                        />
                                    )}
                                </div>

                                <p style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                    {nota.nota}
                                </p>

                                {nota.fecha_promesa_pago && (
                                    <div style={{ marginTop: 4 }}>
                                        <Text type="success" style={{ fontSize: 12 }}>
                                            <ClockCircleOutlined /> Promesa de Pago: {dayjs(nota.fecha_promesa_pago).format('DD/MM/YYYY')}
                                        </Text>
                                    </div>
                                )}
                            </Timeline.Item>
                        ))}
                    </Timeline>
                </div>
            )}
        </Modal>
    );
};

export default Notas;
