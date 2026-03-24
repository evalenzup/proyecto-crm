import React from 'react';
import { WifiOutlined } from '@ant-design/icons';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';

export const OfflineBanner: React.FC = () => {
  const isOnline = useNetworkStatus();

  if (isOnline) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        background: '#faad14',
        color: '#000',
        textAlign: 'center',
        padding: '6px 16px',
        fontSize: 13,
        fontWeight: 500,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      }}
    >
      <WifiOutlined style={{ fontSize: 15 }} />
      Sin conexión — verifica tu red. Los cambios no se guardarán hasta que se restablezca.
    </div>
  );
};
