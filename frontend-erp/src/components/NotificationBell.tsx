import React, { useState } from 'react';
import { Badge, Button, List, Popover, Tooltip, Typography } from 'antd';
import {
  BellOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { NotificacionOut, TipoNotificacion } from '@/services/notificacionService';
import { useNotificaciones } from '@/hooks/useNotificaciones';
import { normalizeISOToUTC } from '@/utils/formatDate';

const TIPO_CONFIG: Record<TipoNotificacion, { icon: React.ReactNode; color: string }> = {
  EXITO:      { icon: <CheckCircleOutlined />,      color: '#52c41a' },
  INFO:       { icon: <InfoCircleOutlined />,        color: '#1890ff' },
  ADVERTENCIA:{ icon: <ExclamationCircleOutlined />, color: '#faad14' },
  ERROR:      { icon: <CloseCircleOutlined />,       color: '#ff4d4f' },
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(normalizeISOToUTC(dateStr) ?? dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'ahora';
  if (mins < 60) return `hace ${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `hace ${hrs}h`;
  return `hace ${Math.floor(hrs / 24)}d`;
}

interface Props {
  collapsed?: boolean;
}

export const NotificationBell: React.FC<Props> = ({ collapsed = false }) => {
  const { items, noLeidas, marcarLeida, marcarTodasLeidas } = useNotificaciones();
  const [open, setOpen] = useState(false);

  const content = (
    <div style={{ width: 320 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Typography.Text strong>Notificaciones</Typography.Text>
        {noLeidas > 0 && (
          <Button type="link" size="small" onClick={marcarTodasLeidas} style={{ padding: 0 }}>
            Marcar todas como leídas
          </Button>
        )}
      </div>

      {items.length === 0 ? (
        <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: '16px 0' }}>
          Sin notificaciones
        </Typography.Text>
      ) : (
        <List
          dataSource={items}
          style={{ maxHeight: 360, overflowY: 'auto' }}
          renderItem={(notif: NotificacionOut) => {
            const cfg = TIPO_CONFIG[notif.tipo] ?? TIPO_CONFIG.INFO;
            return (
              <List.Item
                style={{
                  padding: '8px 4px',
                  cursor: notif.leida ? 'default' : 'pointer',
                  background: notif.leida ? 'transparent' : 'var(--ant-color-primary-bg, #e6f7ff)',
                  borderRadius: 6,
                  marginBottom: 2,
                }}
                onClick={() => !notif.leida && marcarLeida(notif.id)}
              >
                <List.Item.Meta
                  avatar={
                    <span style={{ color: cfg.color, fontSize: 18, lineHeight: 1 }}>
                      {cfg.icon}
                    </span>
                  }
                  title={
                    <Typography.Text strong={!notif.leida} style={{ fontSize: 13 }}>
                      {notif.titulo}
                    </Typography.Text>
                  }
                  description={
                    <>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {notif.mensaje}
                      </Typography.Text>
                      <br />
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                        {timeAgo(notif.creada_en)}
                      </Typography.Text>
                    </>
                  }
                />
              </List.Item>
            );
          }}
        />
      )}
    </div>
  );

  const bell = (
    <Badge count={noLeidas} size="small" offset={[-2, 2]}>
      <BellOutlined style={{ fontSize: collapsed ? 16 : 14, cursor: 'pointer', color: 'var(--ant-color-text-description)' }} />
    </Badge>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement={collapsed ? 'rightBottom' : 'rightTop'}
      arrow={false}
    >
      {collapsed ? (
        <Tooltip title={`Notificaciones${noLeidas > 0 ? ` (${noLeidas})` : ''}`} placement="right">
          <div style={{ display: 'flex', justifyContent: 'center', cursor: 'pointer' }}>
            {bell}
          </div>
        </Tooltip>
      ) : (
        <div style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}>
          {bell}
        </div>
      )}
    </Popover>
  );
};
