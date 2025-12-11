import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Form, Input, Button, Card, Select, Switch, message, Spin, Row, Col } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { usuarioService, UsuarioCreate, UsuarioUpdate } from '@/services/usuarioService';
import { empresaService, EmpresaOut } from '@/services/empresaService';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/axios';

const UsuarioFormPage: React.FC = () => {
    const router = useRouter();
    const { id } = router.query;
    const isEditing = !!id;
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);

    // Default es supervisor (true), a menos que estemos validando otra cosa.
    // Inicialmente el form values dice 'supervisor', así que esto debería ser true.
    const [isSupervisor, setIsSupervisor] = useState(true);

    useEffect(() => {
        // Cargar empresas para el selector
        empresaService.getEmpresas().then(setEmpresas).catch(console.error);

        if (isEditing && typeof id === 'string') {
            const fetchUser = async () => {
                setLoading(true);
                try {
                    const response = await api.get(`/users/${id}`);
                    const user = response.data;
                    form.setFieldsValue({
                        ...user,
                        password: '', // No mostrar password
                    });
                    setIsSupervisor(user.rol === 'supervisor');
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
            const payload = {
                ...values,
                // Si es admin, empresa_id debe ser null probablemente, o opcional.
                empresa_id: values.rol === 'supervisor' ? values.empresa_id : null
            };

            // Si estamos editando y el password está vacío, lo quitamos del payload
            if (isEditing && !payload.password) {
                delete payload.password;
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
        setIsSupervisor(value === 'supervisor');
    };

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
                            initialValues={{
                                rol: 'supervisor',
                                is_active: true,
                            }}
                        >
                            <Row gutter={16}>
                                <Col span={24}>
                                    <Form.Item
                                        name="nombre_completo"
                                        label="Nombre Completo"
                                        rules={[{ required: true, message: 'Requerido' }]}
                                    >
                                        <Input />
                                    </Form.Item>
                                </Col>
                                <Col span={24}>
                                    <Form.Item
                                        name="email"
                                        label="Email"
                                        rules={[{ required: true, type: 'email', message: 'Email válido requerido' }]}
                                    >
                                        <Input disabled={isEditing} />
                                    </Form.Item>
                                </Col>
                                <Col span={24}>
                                    <Form.Item
                                        name="password"
                                        label={isEditing ? "Nueva Contraseña (dejar en blanco para no cambiar)" : "Contraseña"}
                                        rules={[{ required: !isEditing, message: 'Requerido' }]}
                                    >
                                        <Input.Password />
                                    </Form.Item>
                                </Col>
                                <Col span={12}>
                                    <Form.Item
                                        name="rol"
                                        label="Rol"
                                        rules={[{ required: true, message: 'Requerido' }]}
                                    >
                                        <Select onChange={handleRolChange}>
                                            <Select.Option value="admin">Administrador</Select.Option>
                                            <Select.Option value="supervisor">Supervisor</Select.Option>
                                        </Select>
                                    </Form.Item>
                                </Col>
                                {isSupervisor && (
                                    <Col span={12}>
                                        <Form.Item
                                            name="empresa_id"
                                            label="Empresa Asignada"
                                            rules={[{ required: true, message: 'Requerido para supervisores' }]}
                                        >
                                            <Select
                                                placeholder="Seleccionar empresa"
                                                options={empresas.map(e => ({ label: e.nombre_comercial, value: e.id }))}
                                            />
                                        </Form.Item>
                                    </Col>
                                )}
                                <Col span={24}>
                                    <Form.Item
                                        name="is_active"
                                        label="Activo"
                                        valuePropName="checked"
                                    >
                                        <Switch />
                                    </Form.Item>
                                </Col>
                            </Row>

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
