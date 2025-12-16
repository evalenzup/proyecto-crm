import React from 'react';
import { Card, Typography, Divider, Steps, Collapse, Alert } from 'antd';
import {
    LoginOutlined,
    ShopOutlined,
    FileSyncOutlined,
    BarChartOutlined,
    SettingOutlined,
    TableOutlined
} from '@ant-design/icons';
import { Layout } from '@/components/Layout';

const { Title, Paragraph, Text } = Typography;
const { Panel } = Collapse;

const ManualUsuarioPage: React.FC = () => {
    return (
        <Layout title="Manual de Usuario" breadcrumbs={[{ path: '/ayuda', label: 'Ayuda' }]}>
            <Card style={{ maxWidth: 1000, margin: '0 auto', opacity: 0.95 }}>
                <Typography>
                    <Title level={2}>Sistema CRM/ERP - Manual Operativo</Title>
                    <Paragraph>
                        Bienvenido al manual operativo del sistema. Este documento describe las funciones principales para el uso diario de la plataforma.
                    </Paragraph>

                    <Collapse defaultActiveKey={['1']} ghost size='large'>
                        {/* Sección 1: Acceso */}
                        <Panel header={<Title level={4} style={{ margin: 0 }}><LoginOutlined /> 1. Acceso al Sistema</Title>} key="1">
                            <Paragraph>
                                <ol>
                                    <li>Ingresa a la dirección web proporcionada por tu administrador (ej: <Text code>http://localhost:3001</Text> para Producción).</li>
                                    <li>Introduce tu correo electrónico y contraseña.</li>
                                    <li>Haz clic en <strong>"Ingresar"</strong>.</li>
                                </ol>
                                <Alert message="Importante" type="info" description="Si no tienes cuenta o olvidaste tu contraseña, contacta al administrador del sistema." />
                            </Paragraph>
                        </Panel>

                        {/* Sección 2: Catálogos */}
                        <Panel header={<Title level={4} style={{ margin: 0 }}><ShopOutlined /> 2. Gestión de Catálogos</Title>} key="2">
                            <Paragraph>Para que el sistema funcione correctamente, es vital tener la información base completa y sin errores.</Paragraph>

                            <Title level={5}>Clientes</Title>
                            <ul>
                                <li>Ve al menú <strong>Clientes</strong> y haz clic en <strong>"+ Nuevo Cliente"</strong>.</li>
                                <li><strong>Datos Fiscales:</strong>
                                    <ul>
                                        <li><strong>Razón Social:</strong> Sin régimen capital (ej: "Empresa S.A. de C.V." -{'>'} "Empresa").</li>
                                        <li><strong>RFC:</strong> Verifica la homoclave.</li>
                                        <li><strong>CP:</strong> Debe coincidir con la Constancia de Situación Fiscal.</li>
                                    </ul>
                                </li>
                            </ul>

                            <Title level={5}>Productos y Servicios</Title>
                            <ul>
                                <li>Ve al menú <strong>Productos</strong>.</li>
                                <li><strong>Clave SAT:</strong> Es vital para la deducibilidad (ej: 80141605).</li>
                                <li><strong>Clave Unidad:</strong> Usualmente E48 (Servicio) o H87 (Pieza).</li>
                            </ul>
                        </Panel>

                        {/* Sección 3: Ciclo de Ventas */}
                        <Panel header={<Title level={4} style={{ margin: 0 }}><FileSyncOutlined /> 3. Ciclo de Ventas (Flujo Detallado)</Title>} key="3">
                            <Paragraph>El flujo más común y seguro es: <strong>Facturar la venta → Registrar el cobro cuando ocurra</strong>.</Paragraph>

                            <Steps direction="vertical" current={-1} items={[
                                {
                                    title: 'Paso 1: Emitir Factura',
                                    description: (
                                        <ul>
                                            <li>Ve a <strong>Facturas</strong> {'>'} "+ Nueva".</li>
                                            <li><strong>Encabezado:</strong>
                                                <ul>
                                                    <li><strong>Método de Pago:</strong> Usa <em>PUE</em> si ya pagaron, o <em>PPD</em> si es crédito.</li>
                                                    <li><strong>Uso CFDI:</strong> Generalmente "G03 - Gastos en general".</li>
                                                </ul>
                                            </li>
                                            <li><strong>Conceptos:</strong> Agrega tus productos.</li>
                                            <li>Haz clic en <strong>"Timbrar ante el SAT"</strong> para enviar el correo al cliente.</li>
                                        </ul>
                                    )
                                },
                                {
                                    title: 'Paso 2: Registrar Cobranza (Complemento de Pago)',
                                    description: (
                                        <ul>
                                            <li><em>(Solo si la factura fue PPD)</em></li>
                                            <li>Ve a <strong>Pagos</strong> {'>'} "+ Nuevo Pago".</li>
                                            <li>Selecciona Cliente e ingresa el <strong>Monto Real</strong> recibido.</li>
                                            <li>En la tabla, asigna el pago a la(s) factura(s) pendiente(s).</li>
                                            <li>Clic en <strong>"Timbrar Pago"</strong> para generar el REP.</li>
                                        </ul>
                                    )
                                }
                            ]} />
                        </Panel>

                        {/* Sección 4: Egresos */}
                        <Panel header={<Title level={4} style={{ margin: 0 }}><TableOutlined /> 4. Gestión de Gastos (Egresos)</Title>} key="4">
                            <Paragraph>Registra tus compras y gastos operativos.</Paragraph>
                            <ul>
                                <li>Ve al menú <strong>Egresos</strong> {'>'} "+ Nuevo Egreso".</li>
                                <li><strong>Proveedor:</strong> Busca por nombre (min 3 letras).</li>
                                <li><strong>Categoría:</strong> Vital para saber en qué gastas (ej: Renta, Nómina).</li>
                                <li><strong>Evidencia:</strong> Puedes adjuntar el PDF/XML de tu compra.</li>
                            </ul>
                        </Panel>

                        {/* Sección 5: Reportes */}
                        <Panel header={<Title level={4} style={{ margin: 0 }}><BarChartOutlined /> 5. Reportes y Consultas</Title>} key="5">
                            <Paragraph>En el módulo de <strong>Facturas</strong>:</Paragraph>
                            <ul>
                                <li><strong>Buscador:</strong> Por nombre de cliente.</li>
                                <li><strong>Filtro Folio:</strong> Escribe el folio exacto y presiona Enter.</li>
                                <li><strong>Columnas:</strong> Visualiza Fecha Emisión vs Fecha Pago (Prog/Real).</li>
                                <li><strong>Exportar:</strong> Botón "Exportar Excel" arriba a la derecha.</li>
                            </ul>
                        </Panel>

                        {/* Sección 6: Admin */}
                        <Panel header={<Title level={4} style={{ margin: 0 }}><SettingOutlined /> 6. Administración</Title>} key="6">
                            <Paragraph>
                                <em>(Solo Administradores)</em> Ve a <strong>Configuración {'>'} Usuarios</strong> para invitar colaboradores y asignar roles.
                            </Paragraph>
                        </Panel>
                    </Collapse>
                </Typography>
            </Card>
        </Layout>
    );
};

export default ManualUsuarioPage;
