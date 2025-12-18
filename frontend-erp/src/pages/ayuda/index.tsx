import React, { useState } from 'react';
import fs from 'fs';
import path from 'path';
import { Card, Typography, Button, Modal, Divider, FloatButton } from 'antd';
import { BookOutlined, FileTextOutlined, ArrowUpOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Layout } from '@/components/Layout';

const { Title, Text, Paragraph } = Typography;

interface ManualProps {
    manualOperativo: string;
    manualRapido: string;
}

export async function getStaticProps() {
    const contentDir = path.join(process.cwd(), 'content');

    // Leer Manual Operativo (Detallado)
    const manualOperativoPath = path.join(contentDir, 'manual-operativo.md');
    const manualOperativo = fs.readFileSync(manualOperativoPath, 'utf8');

    // Leer Manual Rápido (Resumen)
    const manualRapidoPath = path.join(contentDir, 'manual-rapido.md');
    const manualRapido = fs.readFileSync(manualRapidoPath, 'utf8');

    return {
        props: {
            manualOperativo,
            manualRapido,
        },
    };
}

const ManualUsuarioPage: React.FC<ManualProps> = ({ manualOperativo, manualRapido }) => {
    const [isModalOpen, setIsModalOpen] = useState(false);



    return (
        <Layout title="Manual de Usuario" breadcrumbs={[{ path: '/ayuda', label: 'Ayuda' }]}>
            <Card
                style={{
                    maxWidth: 1000,
                    margin: '0 auto',
                    marginBottom: 40
                }}
                extra={
                    <Button
                        type="primary"
                        icon={<BookOutlined />}
                        onClick={() => setIsModalOpen(true)}
                    >
                        Ver Guía Rápida (Resumen)
                    </Button>
                }
            >
                <div className="markdown-body">
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                            h1: ({ node, ...props }) => <Title level={1} style={{ marginTop: 0 }} {...props} />,
                            h2: ({ node, ...props }) => <Title level={2} style={{ marginTop: 32, borderBottom: '1px solid #eee', paddingBottom: 8 }} {...props} />,
                            h3: ({ node, ...props }) => <Title level={3} style={{ marginTop: 24 }} {...props} />,
                            p: ({ node, ...props }) => <Paragraph style={{ marginBottom: 16 }} {...props} />,
                            li: ({ node, ...props }) => (
                                <li style={{ marginBottom: 8 }}>
                                    <Text>{props.children}</Text>
                                </li>
                            ),
                            blockquote: ({ node, ...props }) => (
                                <blockquote style={{
                                    borderLeft: '4px solid #1890ff',
                                    paddingLeft: 16,
                                    color: 'var(--ant-color-text-secondary)',
                                    fontStyle: 'italic',
                                    margin: '16px 0'
                                }} {...props}>
                                    <Paragraph style={{ margin: 0, color: 'inherit' }}>{props.children}</Paragraph>
                                </blockquote>
                            )
                        }}
                    >
                        {manualOperativo}
                    </ReactMarkdown>
                </div>
            </Card>

            <FloatButton.BackTop />

            {/* Modal para Guía Rápida */}
            <Modal
                title={<span><FileTextOutlined /> Guía Rápida de Referencia</span>}
                open={isModalOpen}
                onCancel={() => setIsModalOpen(false)}
                footer={[
                    <Button key="close" onClick={() => setIsModalOpen(false)}>
                        Cerrar
                    </Button>
                ]}
                width={800}
                style={{ top: 20 }}
                bodyStyle={{ maxHeight: '80vh', overflowY: 'auto' }}
            >
                <div className="markdown-body-modal">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {manualRapido}
                    </ReactMarkdown>
                </div>
            </Modal>
        </Layout>
    );
};

export default ManualUsuarioPage;

