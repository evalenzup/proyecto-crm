import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { PageHeader } from '@/components/PageHeader';
import {
    Form, Input, Button, Card, Select, Switch, message,
    Spin, Row, Col, Checkbox, Divider, Typography, TimePicker, Alert,
} from 'antd';
import dayjs from 'dayjs';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { usuarioService, UsuarioCreate, UsuarioUpdate } from '@/services/usuarioService';
import { empresaService, EmpresaOut } from '@/services/empresaService';
import { useAuth } from '@/context/AuthContext';

const { Text } = Typography;

// ISO: 1=lunes … 7=domingo, igual que el backend
const DIAS_SEMANA = [
    { value: '1', label: 'Lun' },
    { value: '2', label: 'Mar' },
    { value: '3', label: 'Mié' },
    { value: '4', label: 'Jue' },
    { value: '5', label: 'Vie' },
    { value: '6', label: 'Sáb' },
    { value: '7', label: 'Dom' },
];

const FORMATO_HORA = 'HH:mm';

// Módulos disponibles para usuarios ESTANDAR
const MODULOS_DISPONIBLES = [
    { value: 'empresas',        label: 'Empresas' },
    { value: 'clientes',        label: 'Clientes' },
    { value: 'productos',       label: 'Productos' },
    { value: 'facturas',        label: 'Facturación' },
    { value: 'presupuestos',    label: 'Presupuestos' },
    { value: 'pagos',           label: 'Pagos' },
    { value: 'cobranza',        label: 'Cobranza' },
    { value: 'egresos',         label: 'Egresos' },
    { value: 'auditoria',       label: 'Auditoría' },
    { value: 'mapa',            label: 'Mapa Clientes' },
];

const UsuarioFormPage: React.FC = () => {
    const router = useRouter();
    const { id } = router.query;
    const isEditing = !!id;
    const [form] = Form.useForm();
    const { user: currentUser } = useAuth();

    const [loading, setLoading] = useState(false);
    const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
    const [selectedRol, setSelectedRol] = useState<string>('supervisor');

    const isSuperadmin = currentUser?.rol === 'superadmin';

    useEffect(() => {
        // Cargar empresas para los selectores / checkboxes
        empresaService.getEmpresas().then(res => {
            // getEmpresas retorna EmpresaPageOut con .items
            const items = (res as any).items ?? res;
            setEmpresas(Array.isArray(items) ? items : []);
        }).catch(console.error);

        if (isEditing && typeof id === 'string') {
            const fetchUser = async () => {
                setLoading(true);
                try {
                    const user = await usuarioService.getUsuario(id);
                    form.setFieldsValue({
                        nombre_completo: user.nombre_completo,
                        email: user.email,
                        rol: user.rol,
                        empresa_id: user.empresa_id,
                        is_active: user.is_active,
                        password: '',
                        empresas_ids: user.empresas_ids ?? [],
                        // Separar los permisos especiales de los módulos de estándar
                        permisos: (user.permisos ?? []).filter(
                            (p) => p !== 'reportes_actividad' && p !== 'ingresos_no_facturados'
                        ),
                        ver_actividad: (user.permisos ?? []).includes('reportes_actividad'),
                        ver_ingresos: (user.permisos ?? []).includes('ingresos_no_facturados'),
                        puede_eliminar: user.puede_eliminar ?? true,
                        horario: user.horario_inicio && user.horario_fin
                            ? [dayjs(user.horario_inicio, FORMATO_HORA),
                               dayjs(user.horario_fin, FORMATO_HORA)]
                            : undefined,
                        dias_laborales: user.dias_laborales
                            ? user.dias_laborales.split(',').map((d) => d.trim())
                            : [],
                        ips_permitidas: user.ips_permitidas ?? '',
                    });
                    setSelectedRol(user.rol);
                } catch (error) {
                    console.error(error);
                    message.error('Error al cargar usuario');
                    router.push('/usuarios');
                } finally {
                    setLoading(false);
                }
            };
            fetchUser();
        }
    }, [id, isEditing, form, router]);

    const onFinish = async (values: any) => {
        setLoading(true);
        try {
            const isMultiEmpresa = values.rol === 'admin';
            const isSingleEmpresa = ['supervisor', 'estandar', 'operativo'].includes(values.rol);

            const payload: any = {
                nombre_completo: values.nombre_completo,
                email: values.email,
                rol: values.rol,
                is_active: values.is_active,
                empresa_id: isSingleEmpresa ? values.empresa_id : null,
                empresas_ids: isMultiEmpresa ? (values.empresas_ids ?? []) : undefined,
            };

            // Permisos: módulos (solo estándar) + permiso especial de reportes de
            // actividad (cualquier rol, solo lo modifica el superadmin). Se envía
            // siempre para que el backend lo sincronice.
            const modPerms: string[] = values.rol === 'estandar' ? (values.permisos ?? []) : [];
            const permisos = modPerms.filter(
                (p: string) => p !== 'reportes_actividad' && p !== 'ingresos_no_facturados'
            );
            // Solo el superadmin puede otorgar los permisos especiales; el backend,
            // además, ignora cambios a estos permisos si el que edita no es superadmin
            // (aquí solo los incluimos cuando aplica).
            if (isSuperadmin && values.ver_actividad) permisos.push('reportes_actividad');
            if (isSuperadmin && values.ver_ingresos) permisos.push('ingresos_no_facturados');
            payload.permisos = permisos;

            // Restricciones de acceso. Se mandan siempre para que se puedan
            // limpiar: vacío significa "sin restricción".
            const [desde, hasta] = values.horario ?? [];
            payload.restricciones = {
                puede_eliminar: values.puede_eliminar !== false,
                horario_inicio: desde ? desde.format(FORMATO_HORA) : null,
                horario_fin: hasta ? hasta.format(FORMATO_HORA) : null,
                dias_laborales: (values.dias_laborales ?? []).length
                    ? (values.dias_laborales as string[]).join(',')
                    : null,
                ips_permitidas: (values.ips_permitidas ?? '').trim() || null,
            };

            if (isEditing && !values.password) {
                delete payload.password;
            } else if (values.password) {
                payload.password = values.password;
            }

            if (isEditing && typeof id === 'string') {
                await usuarioService.updateUsuario(id, payload as UsuarioUpdate);
                message.success('Usuario actualizado');
            } else {
                await usuarioService.createUsuario(payload as UsuarioCreate);
                message.success('Usuario creado');
            }
            router.push('/usuarios');
        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.detail || 'Error al guardar usuario';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleRolChange = (value: string) => {
        setSelectedRol(value);
        // Limpiar campos que no aplican al nuevo rol
        if (value !== 'supervisor' && value !== 'estandar' && value !== 'operativo') {
            form.setFieldValue('empresa_id', undefined);
        }
        if (value !== 'admin') {
            form.setFieldValue('empresas_ids', []);
        }
        if (value !== 'estandar') {
            form.setFieldValue('permisos', []);
        }
    };

    // Roles disponibles según quién crea
    const rolesDisponibles = isSuperadmin
        ? [
            { value: 'admin',      label: 'Administrador' },
            { value: 'supervisor', label: 'Supervisor' },
            { value: 'estandar',   label: 'Estándar' },
            { value: 'operativo',  label: 'Operativo' },
          ]
        : [
            { value: 'supervisor', label: 'Supervisor' },
            { value: 'estandar',   label: 'Estándar' },
            { value: 'operativo',  label: 'Operativo' },
          ];

    const needsSingleEmpresa = ['supervisor', 'estandar', 'operativo'].includes(selectedRol);
    const needsMultiEmpresa  = selectedRol === 'admin';
    const needsPermisos      = selectedRol === 'estandar';

    return (
        <>
            <PageHeader title={isEditing ? 'Editar Usuario' : 'Nuevo Usuario'} />
            <div className="app-content">
                <Card>
                    {loading && isEditing ? (
                        <Spin />
                    ) : (
                        <Form
                            form={form}
                            layout="vertical"
                            onFinish={onFinish}
                            initialValues={{ rol: 'supervisor', is_active: true, empresas_ids: [], permisos: [] }}
                        >
                            <Row gutter={16}>
                                <Col xs={24} md={12}>
                                    <Form.Item
                                        name="nombre_completo"
                                        label="Nombre Completo"
                                        rules={[{ required: true, message: 'Requerido' }]}
                                    >
                                        <Input />
                                    </Form.Item>
                                </Col>
                                <Col xs={24} md={12}>
                                    <Form.Item
                                        name="email"
                                        label="Email"
                                        rules={[{ required: true, type: 'email', message: 'Email válido requerido' }]}
                                    >
                                        <Input disabled={isEditing} />
                                    </Form.Item>
                                </Col>
                                <Col xs={24} md={12}>
                                    <Form.Item
                                        name="password"
                                        label={isEditing ? 'Nueva Contraseña (dejar en blanco para no cambiar)' : 'Contraseña'}
                                        rules={[{ required: !isEditing, message: 'Requerido' }]}
                                    >
                                        <Input.Password autoComplete="new-password" />
                                    </Form.Item>
                                </Col>
                                <Col xs={24} md={6}>
                                    <Form.Item
                                        name="rol"
                                        label="Rol"
                                        rules={[{ required: true, message: 'Requerido' }]}
                                    >
                                        <Select onChange={handleRolChange} options={rolesDisponibles} />
                                    </Form.Item>
                                </Col>
                                <Col xs={24} md={6}>
                                    <Form.Item name="is_active" label="Activo" valuePropName="checked">
                                        <Switch />
                                    </Form.Item>
                                </Col>
                            </Row>

                            {/* Empresa única (supervisor / estandar / operativo) */}
                            {needsSingleEmpresa && (
                                <Row gutter={16}>
                                    <Col xs={24} md={12}>
                                        <Form.Item
                                            name="empresa_id"
                                            label="Empresa Asignada"
                                            rules={[{ required: true, message: 'Requerido para este rol' }]}
                                        >
                                            <Select
                                                placeholder="Seleccionar empresa"
                                                options={empresas.map(e => ({ label: e.nombre_comercial, value: e.id }))}
                                                showSearch
                                                filterOption={(input, opt) =>
                                                    (opt?.label ?? '').toLowerCase().includes(input.toLowerCase())
                                                }
                                            />
                                        </Form.Item>
                                    </Col>
                                </Row>
                            )}

                            {/* Empresas múltiples (admin) — solo superadmin puede asignar */}
                            {needsMultiEmpresa && isSuperadmin && (
                                <>
                                    <Divider orientation="left">Empresas Accesibles</Divider>
                                    <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                                        Selecciona las empresas a las que este administrador tendrá acceso.
                                    </Text>
                                    <Form.Item name="empresas_ids">
                                        <Checkbox.Group style={{ width: '100%' }}>
                                            <Row gutter={[8, 8]}>
                                                {empresas.map(e => (
                                                    <Col xs={24} sm={12} md={8} key={e.id}>
                                                        <Checkbox value={e.id}>{e.nombre_comercial}</Checkbox>
                                                    </Col>
                                                ))}
                                            </Row>
                                        </Checkbox.Group>
                                    </Form.Item>
                                </>
                            )}

                            {/* Permisos de módulo (estandar) */}
                            {needsPermisos && (
                                <>
                                    <Divider orientation="left">Módulos Permitidos</Divider>
                                    <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                                        Selecciona los módulos a los que este usuario tendrá acceso.
                                    </Text>
                                    <Form.Item name="permisos">
                                        <Checkbox.Group style={{ width: '100%' }}>
                                            <Row gutter={[8, 8]}>
                                                {MODULOS_DISPONIBLES.map(m => (
                                                    <Col xs={24} sm={12} md={8} key={m.value}>
                                                        <Checkbox value={m.value}>{m.label}</Checkbox>
                                                    </Col>
                                                ))}
                                            </Row>
                                        </Checkbox.Group>
                                    </Form.Item>
                                </>
                            )}

                            {/* Permiso especial (info sensible) — solo el superadmin lo edita */}
                            {(isSuperadmin || isEditing) && (
                                <>
                                    <Divider orientation="left">Permisos especiales</Divider>
                                    <Form.Item name="ver_actividad" valuePropName="checked" style={{ marginBottom: 4 }}>
                                        <Checkbox disabled={!isSuperadmin}>
                                            Puede ver los reportes de actividad del personal
                                        </Checkbox>
                                    </Form.Item>
                                    <Form.Item name="ver_ingresos" valuePropName="checked" style={{ marginBottom: 4 }}>
                                        <Checkbox disabled={!isSuperadmin}>
                                            Puede ver los ingresos no facturados
                                        </Checkbox>
                                    </Form.Item>
                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                        {isSuperadmin
                                            ? 'Información sensible: otórgalos solo a las personas de confianza.'
                                            : 'Solo el superadministrador puede modificar estos permisos.'}
                                    </Text>
                                </>
                            )}

                            <Divider orientation="left">Restricciones de acceso</Divider>
                            <Alert
                                type="info"
                                showIcon
                                style={{ marginBottom: 16 }}
                                message="Déjalas vacías para no restringir nada."
                                description="Se aplican en cada petición, así que una sesión ya abierta también se corta al salir del horario o de la red permitida."
                            />

                            <Form.Item name="puede_eliminar" valuePropName="checked" style={{ marginBottom: 12 }}>
                                <Checkbox>Puede eliminar registros</Checkbox>
                            </Form.Item>

                            <Row gutter={16}>
                                <Col xs={24} md={10}>
                                    <Form.Item
                                        name="horario"
                                        label="Horario permitido"
                                        tooltip="Hora del centro. Fuera de este rango no puede entrar ni seguir trabajando."
                                    >
                                        <TimePicker.RangePicker
                                            format={FORMATO_HORA}
                                            minuteStep={15}
                                            style={{ width: '100%' }}
                                            placeholder={['Desde', 'Hasta']}
                                        />
                                    </Form.Item>
                                </Col>
                                <Col xs={24} md={14}>
                                    <Form.Item name="dias_laborales" label="Días permitidos">
                                        <Checkbox.Group options={DIAS_SEMANA} />
                                    </Form.Item>
                                </Col>
                            </Row>

                            <Form.Item
                                name="ips_permitidas"
                                label="Solo desde estas IP"
                                tooltip="IP pública de las instalaciones. Acepta varias separadas por coma y rangos como 192.168.1.0/24."
                                extra="Requiere que el internet de la oficina tenga IP fija; si el proveedor la cambia, el usuario queda fuera."
                            >
                                <Input placeholder="Ej. 189.223.202.22, 192.168.1.0/24" allowClear />
                            </Form.Item>

                            <Form.Item style={{ textAlign: 'right', marginTop: 16 }}>
                                <Button onClick={() => router.back()} style={{ marginRight: 8 }}>
                                    Cancelar
                                </Button>
                                <Button type="primary" htmlType="submit" loading={loading}>
                                    Guardar
                                </Button>
                            </Form.Item>
                        </Form>
                    )}
                </Card>
            </div>
        </>
    );
};

export default UsuarioFormPage;
