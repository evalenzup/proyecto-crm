// src/pages/usuarios/index.tsx

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Table, Button, Popconfirm, Space, Tag, message, Tooltip } from 'antd';
import { EditOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Breadcrumbs } from '@/components/Breadcrumb';
import { usuarioService, Usuario } from '@/services/usuarioService';
import { useAuth } from '@/context/AuthContext';
import { useTableHeight } from '@/hooks/useTableHeight';

const UsuariosPage: React.FC = () => {
    const router = useRouter();
    const { containerRef, tableY } = useTableHeight();
    const { user: currentUser } = useAuth();
    const [usuarios, setUsuarios] = useState<Usuario[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchUsuarios = async () => {
        setLoading(true);
        try {
            const data = await usuarioService.getUsuarios();
            setUsuarios(data);
        } catch (error) {
            console.error(error);
            message.error('Error al cargar usuarios');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (currentUser?.rol === 'admin') {
            fetchUsuarios();
        } else {
            // Redirect or show access denied if somehow accessed (though ProtectedRoute should handle)
        }
    }, [currentUser]);

    const handleDelete = async (id: string) => {
        try {
            await usuarioService.deleteUsuario(id);
            message.success('Usuario eliminado');
            fetchUsuarios();
        } catch (error) {
            console.error(error);
            message.error('Error al eliminar usuario');
        }
    };

    const columns: ColumnsType<Usuario> = [
        { title: 'Nombre', dataIndex: 'nombre_completo', key: 'nombre' },
        { title: 'Email', dataIndex: 'email', key: 'email' },
        {
            title: 'Rol',
            dataIndex: 'rol',
            key: 'rol',
            render: (rol: string) => (
                <Tag color={rol === 'admin' ? 'red' : 'blue'}>
                    {rol.toUpperCase()}
                </Tag>
            )
        },
        {
            title: 'Estado',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (active: boolean) => (
                <Tag color={active ? 'green' : 'default'}>
                    {active ? 'ACTIVO' : 'INACTIVO'}
                </Tag>
            )
        },
        {
            title: 'Acciones',
            key: 'acciones',
            render: (_, record) => (
                <Space>
                    <Tooltip title="Editar">
                        <Button
                            type="link"
                            icon={<EditOutlined />}
                            onClick={() => router.push(`/usuarios/form/${record.id}`)}
                        />
                    </Tooltip>
                    <Tooltip title="Eliminar">
                        <Popconfirm
                            title="¿Eliminar usuario?"
                            onConfirm={() => handleDelete(record.id)}
                            okText="Sí"
                            cancelText="No"
                            disabled={record.id === currentUser?.id}
                        >
                            <Button type="link" danger icon={<DeleteOutlined />} disabled={record.id === currentUser?.id} />
                        </Popconfirm>
                    </Tooltip>
                </Space>
            ),
        },
    ];

    return (
        <>
            <div className="app-page-header">
                <div className="app-page-header__left">
                    <Breadcrumbs />
                    <h1 className="app-title">Gestión de Usuarios</h1>
                </div>
                <div className="app-page-header__right">
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => router.push('/usuarios/form')}
                    >
                        Agregar Usuario
                    </Button>
                </div>
            </div>
            <div className="app-content" ref={containerRef}>
                <Table<Usuario>
                    rowKey="id"
                    columns={columns}
                    dataSource={usuarios}
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                    scroll={{ x: 800, y: tableY }}
                    locale={{ emptyText: 'No hay usuarios' }}
                />
            </div>
        </>
    );
};

export default UsuariosPage;
