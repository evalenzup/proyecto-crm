// src/components/FilterBar.tsx
// Barra de filtros estándar: tarjeta con contenedor sticky y los controles
// envueltos en un Space que hace wrap. Reemplaza el bloque
// Card > div.sticky > Space repetido en cada listado.
import React from 'react';
import { Card, Space, Button, theme } from 'antd';
import { ClearOutlined } from '@ant-design/icons';

interface FilterBarProps {
  /** Controles de filtro (inputs, selects, etc.) */
  children: React.ReactNode;
  /** Si se pasa, muestra un botón "Limpiar" al final de la barra */
  onClear?: () => void;
  /** Contenido alineado a la derecha (acciones secundarias) */
  extra?: React.ReactNode;
}

export const FilterBar: React.FC<FilterBarProps> = ({ children, onClear, extra }) => {
  const { token } = theme.useToken();
  return (
    <Card
      size="small"
      variant="borderless"
      styles={{ body: { padding: 12 } }}
      style={{ marginBottom: 8 }}
    >
      <div
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 9,
          padding: 4,
          background: token.colorBgContainer,
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
        }}
      >
        <Space wrap size={[8, 8]}>{children}</Space>
        {(onClear || extra) && (
          <Space wrap size={[8, 8]}>
            {extra}
            {onClear && (
              <Button icon={<ClearOutlined />} onClick={onClear}>
                Limpiar
              </Button>
            )}
          </Space>
        )}
      </div>
    </Card>
  );
};

export default FilterBar;
