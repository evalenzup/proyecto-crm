import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import {
    Form, Input, Button, Card, Select, Switch, message,
    Spin, Row, Col, Checkbox, Divider, Typography,
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { usuarioService, UsuarioCreate, UsuarioUpdate } from '@/services/usuarioService';
import { empresaService, EmpresaOut } from '@/services/empresaService';
import { useAuth } from '@/context/AuthContext';

const { Text } = Typography;

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
                        permisos: user.permisos ?? [],
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
                permisos: values.rol === 'estandar' ? (values.permisos ?? []) : undefined,
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
            <div className="app-page-header">
                <div className="app-page-header__left">
                    <Breadcrumbs />
                    <h1 className="app-title">{isEditing ? 'Editar Usuario' : 'Nuevo Usuario'}</h1>
                </div>
            </div>
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
