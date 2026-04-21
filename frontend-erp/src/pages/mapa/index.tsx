import React, { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/router';
import { Typography, Spin, Alert, Badge, Card, Space, Tag, Statistic, Input, Checkbox, Select } from 'antd';
import { EnvironmentOutlined, FileTextOutlined, PhoneOutlined, SearchOutlined, FilterOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { useAuth } from '@/context/AuthContext';
import { mapaService, canViewMapa, ClienteMapa } from '@/services/mapaService';
import { useEmpresaSelector } from '@/hooks/useEmpresaSelector';

const { Text } = Typography;

const MapaClientes = dynamic(() => import('@/components/mapa/MapaClientes'), {
    ssr: false,
    loading: () => (
        <div style={{ height: 'calc(100vh - 210px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Spin size="large" tip="Cargando mapa..." />
        </div>
    ),
});

const ACTIVIDADES = ['RESIDENCIAL', 'COMERCIAL', 'INDUSTRIAL'];

const ACTIVIDAD_COLOR: Record<string, string> = {
    RESIDENCIAL: 'green',
    COMERCIAL: 'blue',
    INDUSTRIAL: 'orange',
};

export default function MapaPage() {
    const router = useRouter();
    const { user, isLoading: authLoading } = useAuth();
    const { selectedEmpresaId } = useEmpresaSelector();

    const [clienteSeleccionado, setClienteSeleccionado] = useState<ClienteMapa | null>(null);
    const [busqueda, setBusqueda] = useState('');
    const [actividadesFiltro, setActividadesFiltro] = useState<string[]>([]);
    const [empresasFiltro, setEmpresasFiltro] = useState<string[]>([]);

    // Sincronizar el filtro de empresa con el selector global del sidebar
    useEffect(() => {
        if (selectedEmpresaId) {
            setEmpresasFiltro([selectedEmpresaId]);
        } else {
            setEmpresasFiltro([]);
        }
    }, [selectedEmpresaId]);

    useEffect(() => {
        if (!authLoading && !canViewMapa(user?.rol)) {
            router.replace('/');
        }
    }, [user, authLoading, router]);

    const { data, isLoading, isError } = useQuery({
        queryKey: ['mapa-clientes'],
        queryFn: mapaService.getClientesConServicio,
        enabled: canViewMapa(user?.rol),
        staleTime: 1000 * 60 * 5,
    });

    // Filtrado client-side: instantáneo sin llamadas al servidor
    const clientesFiltrados = useMemo(() => {
        let lista = data?.clientes ?? [];

        if (busqueda.trim()) {
            const q = busqueda.toLowerCase();
            lista = lista.filter(c => c.nombre_comercial.toLowerCase().includes(q));
        }

        if (actividadesFiltro.length > 0) {
            lista = lista.filter(c =>
                c.actividad ? actividadesFiltro.includes(c.actividad) : actividadesFiltro.includes('SIN_CLASIFICAR')
            );
        }

        if (empresasFiltro.length > 0) {
            lista = lista.filter(c =>
                c.empresas.some(e => empresasFiltro.includes(e.id))
            );
        }

        return lista;
    }, [data, busqueda, actividadesFiltro, empresasFiltro]);

    const hayFiltrosActivos = busqueda.trim() !== '' || actividadesFiltro.length > 0 || empresasFiltro.length > 0;

    const handleActividadChange = (actividad: string, checked: boolean) => {
        setActividadesFiltro(prev =>
            checked ? [...prev, actividad] : prev.filter(a => a !== actividad)
        );
    };

    const limpiarFiltros = () => {
        setBusqueda('');
        setActividadesFiltro([]);
        setEmpresasFiltro([]);
    };

    if (authLoading || (!canViewMapa(user?.rol) && !authLoading)) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <Spin size="large" />
            </div>
        );
    }

    return (
        <Layout
            title="Mapa de Clientes"
            breadcrumbs={[
                { path: '/', label: 'Inicio' },
                { path: '/mapa', label: 'Mapa de Clientes' },
            ]}
        >
            <div style={{ padding: '8px 16px' }}>
                {/* Estadísticas rápidas */}
                <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
                    <Card size="small" style={{ minWidth: 160 }}>
                        <Statistic
                            title="Mostrando"
                            value={clientesFiltrados.length}
                            suffix={hayFiltrosActivos ? `/ ${data?.total ?? 0}` : undefined}
                            prefix={<EnvironmentOutlined />}
                            loading={isLoading}
                        />
                    </Card>
                    <Card size="small" style={{ minWidth: 160 }}>
                        <Statistic
                            title="Facturas (filtrado)"
                            value={clientesFiltrados.reduce((acc, c) => acc + c.total_facturas, 0)}
                            prefix={<FileTextOutlined />}
                            loading={isLoading}
                        />
                    </Card>
                </div>

                {isError && (
                    <Alert
                        type="error"
                        message="Error al cargar los clientes"
                        description="No se pudo obtener la información del servidor."
                        showIcon
                        style={{ marginBottom: 12 }}
                    />
                )}

                <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                    {/* Mapa principal */}
                    <div style={{ flex: 1, minWidth: 320 }}>
                        <Card
                            bodyStyle={{ padding: 0, overflow: 'hidden', borderRadius: 8 }}
                            style={{ borderRadius: 8 }}
                        >
                            {isLoading ? (
                                <div style={{ height: 'calc(100vh - 210px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <Spin size="large" tip="Cargando datos..." />
                                </div>
                            ) : (
                                <MapaClientes
                                    clientes={clientesFiltrados}
                                    onClienteClick={setClienteSeleccionado}
                                    clienteSeleccionado={clienteSeleccionado}
                                    height="calc(100vh - 210px)"
                                />
                            )}
                        </Card>
                    </div>

                    {/* Panel lateral */}
                    <div style={{ width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>

                        {/* Filtros */}
                        <Card
                            size="small"
                            title={
                                <Space>
                                    <FilterOutlined />
                                    <Text strong>Filtros</Text>
                                    {hayFiltrosActivos && (
                                        <Text
                                            type="secondary"
                                            style={{ fontSize: 11, cursor: 'pointer', color: '#1890ff' }}
                                            onClick={limpiarFiltros}
                                        >
                                            Limpiar
                                        </Text>
                                    )}
                                </Space>
                            }
                        >
                            <Space direction="vertical" style={{ width: '100%' }} size={10}>
                                <Input
                                    placeholder="Buscar cliente..."
                                    prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
                                    value={busqueda}
                                    onChange={e => setBusqueda(e.target.value)}
                                    allowClear
                                    size="small"
                                />
                                <div>
                                    <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 6 }}>
                                        EMPRESA
                                    </Text>
                                    <Select
                                        mode="multiple"
                                        size="small"
                                        style={{ width: '100%' }}
                                        placeholder="Todas las empresas"
                                        value={empresasFiltro}
                                        onChange={setEmpresasFiltro}
                                        allowClear
                                        maxTagCount="responsive"
                                        options={(data?.empresas ?? []).map(e => ({
                                            label: e.nombre,
                                            value: e.id,
                                        }))}
                                    />
                                </div>
                                <div>
                                    <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 6 }}>
                                        ACTIVIDAD
                                    </Text>
                                    <Space direction="vertical" size={4}>
                                        {ACTIVIDADES.map(act => (
                                            <Checkbox
                                                key={act}
                                                checked={actividadesFiltro.includes(act)}
                                                onChange={e => handleActividadChange(act, e.target.checked)}
                                            >
                                                <Space size={6}>
                                                    <Badge color={ACTIVIDAD_COLOR[act]} />
                                                    <Text style={{ fontSize: 12 }}>{act}</Text>
                                                </Space>
                                            </Checkbox>
                                        ))}
                                        <Checkbox
                                            checked={actividadesFiltro.includes('SIN_CLASIFICAR')}
                                            onChange={e => handleActividadChange('SIN_CLASIFICAR', e.target.checked)}
                                        >
                                            <Space size={6}>
                                                <Badge color="default" />
                                                <Text style={{ fontSize: 12 }}>SIN CLASIFICAR</Text>
                                            </Space>
                                        </Checkbox>
                                    </Space>
                                </div>
                            </Space>
                        </Card>

                        {/* Detalle del cliente seleccionado */}
                        <Card
                            title={<Text strong>Detalle</Text>}
                            size="small"
                            style={{ minHeight: 140 }}
                        >
                            {clienteSeleccionado ? (
                                <Space direction="vertical" style={{ width: '100%' }} size={8}>
                                    <Text strong style={{ fontSize: 14 }}>
                                        {clienteSeleccionado.nombre_comercial}
                                    </Text>
                                    {clienteSeleccionado.actividad && (
                                        <Tag color={ACTIVIDAD_COLOR[clienteSeleccionado.actividad] ?? 'default'}>
                                            {clienteSeleccionado.actividad}
                                        </Tag>
                                    )}
                                    <Space>
                                        <FileTextOutlined />
                                        <Text>{clienteSeleccionado.total_facturas} factura(s)</Text>
                                    </Space>
                                    {clienteSeleccionado.telefono && (
                                        <Space>
                                            <PhoneOutlined />
                                            <Text>{clienteSeleccionado.telefono}</Text>
                                        </Space>
                                    )}
                                    {clienteSeleccionado.email && (
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            {clienteSeleccionado.email}
                                        </Text>
                                    )}
                                    <Text type="secondary" style={{ fontSize: 11 }}>
                                        {clienteSeleccionado.latitud.toFixed(6)}, {clienteSeleccionado.longitud.toFixed(6)}
                                    </Text>
                                </Space>
                            ) : (
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                    Haz clic en un marcador para ver el detalle.
                                </Text>
                            )}
                        </Card>
                    </div>
                </div>
            </div>
        </Layout>
    );
}
