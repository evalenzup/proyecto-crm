import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, Layout, theme, Alert } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuth } from '@/context/AuthContext';
import Head from 'next/head';

const { Title, Text } = Typography;
const { Content } = Layout;

const LoginPage: React.FC = () => {
    const { login, isLoading, error } = useAuth();
    const {
        token: { colorBgContainer, borderRadiusLG, colorPrimary },
    } = theme.useToken();

    const onFinish = async (values: any) => {
        try {
            await login(values.email, values.password);
        } catch (err) {
            // Error manejado en el context y mostrado con message.error
        }
    };

    return (
        <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
            <Head>
                <title>Iniciar Sesión | Norton</title>
            </Head>
            <Content style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '0 20px' }}>
                <div style={{ maxWidth: 400, width: '100%' }}>

                    <div style={{ textAlign: 'center', marginBottom: 24 }}>
                        {/* Aquí puedes poner un logo si tienes */}
                        <div style={{
                            width: 120, // Ajustado para imagen
                            height: 'auto',
                            margin: '0 auto 16px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}>
                            <img
                                src="/logo-empresa.png"
                                alt="Logo empresa"
                                style={{ width: '100%', maxWidth: '100%', height: 'auto', objectFit: 'contain', display: 'block' }}
                                onError={(e) => {
                                    const t = e.currentTarget as HTMLImageElement;
                                    if (t.src.endsWith('/vercel.svg')) return;
                                    t.src = '/vercel.svg';
                                }}
                            />
                        </div>
                        <Title level={2} style={{ margin: 0 }}>Bienvenido</Title>
                        <Text type="secondary">Ingresa a tu cuenta para continuar</Text>
                    </div>

                    <Card
                        bordered={false}
                        style={{
                            boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                            borderRadius: borderRadiusLG
                        }}
                    >
                        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />}

                        <Form
                            name="login_form"
                            initialValues={{ remember: true }}
                            onFinish={onFinish}
                            layout="vertical"
                            size="large"
                        >
                            <Form.Item
                                name="email"
                                rules={[
                                    { required: true, message: 'Por favor ingresa tu correo!' },
                                    { type: 'email', message: 'El correo no es válido' }
                                ]}
                            >
                                <Input prefix={<UserOutlined />} placeholder="Correo electrónico" />
                            </Form.Item>

                            <Form.Item
                                name="password"
                                rules={[{ required: true, message: 'Por favor ingresa tu contraseña!' }]}
                            >
                                <Input.Password prefix={<LockOutlined />} placeholder="Contraseña" />
                            </Form.Item>

                            <Form.Item>
                                <Button type="primary" htmlType="submit" loading={isLoading} block>
                                    Iniciar Sesión
                                </Button>
                            </Form.Item>
                        </Form>
                    </Card>

                    <div style={{ textAlign: 'center', marginTop: 16 }}>
                        <Text type="secondary">CRM Desarrollo Norton © {new Date().getFullYear()}</Text>
                    </div>
                </div>
            </Content>
        </Layout>
    );
};

export default LoginPage;
