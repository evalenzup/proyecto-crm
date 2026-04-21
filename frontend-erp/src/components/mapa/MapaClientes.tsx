import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { ClienteMapa } from '@/services/mapaService';
import { Tag, Typography, Space } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';

const { Text } = Typography;

// Fix del ícono por defecto de Leaflet en Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const ACTIVIDAD_COLOR: Record<string, string> = {
    RESIDENCIAL: '#52c41a',
    COMERCIAL: '#1890ff',
    INDUSTRIAL: '#fa8c16',
};

const ACTIVIDAD_TAG_COLOR: Record<string, string> = {
    RESIDENCIAL: 'green',
    COMERCIAL: 'blue',
    INDUSTRIAL: 'orange',
};

function crearIcono(actividad?: string): L.Icon {
    const color = actividad ? (ACTIVIDAD_COLOR[actividad] ?? '#888888') : '#888888';

    const svgIcon = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="24" height="36">
            <path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 24 12 24S24 21 24 12C24 5.373 18.627 0 12 0z"
                fill="${color}" stroke="#fff" stroke-width="1.5"/>
            <circle cx="12" cy="12" r="5" fill="#fff"/>
        </svg>`;

    return L.icon({
        iconUrl: `data:image/svg+xml;base64,${btoa(svgIcon)}`,
        iconSize: [24, 36],
        iconAnchor: [12, 36],
        popupAnchor: [0, -36],
    });
}

// Ajusta los bounds del mapa a los marcadores visibles
function AjustarBounds({ clientes }: { clientes: ClienteMapa[] }) {
    const map = useMap();

    useEffect(() => {
        if (clientes.length === 0) return;

        const bounds = L.latLngBounds(
            clientes.map((c) => [c.latitud, c.longitud] as [number, number])
        );
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }, [clientes, map]);

    return null;
}

interface Props {
    clientes: ClienteMapa[];
    onClienteClick: (cliente: ClienteMapa) => void;
    clienteSeleccionado: ClienteMapa | null;
    height?: string | number;
}

export default function MapaClientes({ clientes, onClienteClick, clienteSeleccionado, height = 'calc(100vh - 210px)' }: Props) {
    // Centro inicial: México
    const centroInicial: [number, number] = [23.6345, -102.5528];

    return (
        <MapContainer
            center={centroInicial}
            zoom={5}
            style={{ height, width: '100%' }}
            scrollWheelZoom
        >
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {clientes.length > 0 && <AjustarBounds clientes={clientes} />}

            {clientes.map((cliente) => (
                <Marker
                    key={cliente.id}
                    position={[cliente.latitud, cliente.longitud]}
                    icon={crearIcono(cliente.actividad)}
                    eventHandlers={{
                        click: () => onClienteClick(cliente),
                    }}
                >
                    <Popup minWidth={200}>
                        <Space direction="vertical" size={4} style={{ width: '100%' }}>
                            <Text strong style={{ fontSize: 13 }}>
                                {cliente.nombre_comercial}
                            </Text>

                            {cliente.actividad && (
                                <Tag color={ACTIVIDAD_TAG_COLOR[cliente.actividad] ?? 'default'} style={{ fontSize: 11 }}>
                                    {cliente.actividad}
                                </Tag>
                            )}

                            <Space>
                                <FileTextOutlined style={{ color: '#1890ff' }} />
                                <Text style={{ fontSize: 12 }}>{cliente.total_facturas} factura(s)</Text>
                            </Space>

                            {cliente.telefono && (
                                <Text style={{ fontSize: 12 }}>📞 {cliente.telefono}</Text>
                            )}
                        </Space>
                    </Popup>
                </Marker>
            ))}
        </MapContainer>
    );
}
