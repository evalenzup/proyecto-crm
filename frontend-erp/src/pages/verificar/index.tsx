import React from 'react';
import Head from 'next/head';
import { CloseCircleFilled } from '@ant-design/icons';
import { Typography } from 'antd';

const { Text } = Typography;

export default function VerificarIndex() {
  return (
    <>
      <Head>
        <title>Verificación de Credencial</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div style={{ minHeight: '100vh', background: '#f0f2f5', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
        <CloseCircleFilled style={{ fontSize: 56, color: '#d9d9d9' }} />
        <Text strong style={{ fontSize: 16, color: '#555' }}>Código QR inválido</Text>
        <Text type="secondary" style={{ fontSize: 13 }}>Escanea el código QR de la credencial para verificar.</Text>
      </div>
    </>
  );
}
