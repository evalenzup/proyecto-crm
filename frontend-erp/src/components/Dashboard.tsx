// src/components/Dashboard.tsx
import React from 'react';
import { Row, Col, Card, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

export const Dashboard: React.FC = () => (
  <Row gutter={[16, 16]}>
    <Col span={8}>
      <Card>
        <Statistic
          title="Facturación Mensual"
          value={12450}
          precision={2}
          valueStyle={{ color: '#3f8600' }}
          prefix={<ArrowUpOutlined />}
          suffix="USD"
        />
      </Card>
    </Col>
    <Col span={8}>
      <Card>
        <Statistic
          title="Órdenes Pendientes"
          value={32}
          valueStyle={{ color: '#cf1322' }}
        />
      </Card>
    </Col>
    <Col span={8}>
      <Card>
        <Statistic
          title="Valor de Inventario"
          value={75800}
          precision={0}
          prefix={<ArrowDownOutlined />}
          suffix="USD"
        />
      </Card>
    </Col>
  </Row>
);

