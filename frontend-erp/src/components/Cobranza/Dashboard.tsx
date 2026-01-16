import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Row, Col, Statistic, Typography } from 'antd';
import { DollarOutlined, SolutionOutlined, TeamOutlined, RiseOutlined } from '@ant-design/icons';
import { AgingReportResponse } from '@/types/cobranza';
import { formatCurrency } from '@/utils/format';

const { Title } = Typography;

interface DashboardProps {
    data: AgingReportResponse | null;
    loading: boolean;
}

const CobranzaDashboard: React.FC<DashboardProps> = ({ data, loading }) => {
    // 1. Prepare Data for Pie Chart (Aging Buckets)
    const pieData = [
        { value: data?.items.reduce((sum, item) => sum + item.por_vencer, 0) || 0, name: 'Por Vencer', itemStyle: { color: '#87d068' } },
        { value: data?.items.reduce((sum, item) => sum + item.vencido_0_30, 0) || 0, name: '0-30 Días', itemStyle: { color: '#faad14' } },
        { value: data?.items.reduce((sum, item) => sum + item.vencido_31_60, 0) || 0, name: '31-60 Días', itemStyle: { color: '#fa8c16' } },
        { value: data?.items.reduce((sum, item) => sum + item.vencido_61_90, 0) || 0, name: '61-90 Días', itemStyle: { color: '#fa541c' } },
        { value: data?.items.reduce((sum, item) => sum + item.vencido_mas_90, 0) || 0, name: '> 90 Días', itemStyle: { color: '#f5222d' } },
    ].filter(i => i.value > 0); // Only show buckets with value? Or show all 0? Charts usually better if filtered or handle 0 well.

    const pieOption = {
        tooltip: {
            trigger: 'item',
            formatter: (params: any) => {
                return `${params.name}: <b>${formatCurrency(params.value)}</b> (${params.percent}%)`;
            }
        },
        legend: {
            bottom: '0%',
            left: 'center'
        },
        series: [
            {
                name: 'Antigüedad',
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false,
                    position: 'center'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 16,
                        fontWeight: 'bold'
                    }
                },
                labelLine: {
                    show: false
                },
                data: pieData
            }
        ]
    };

    // 2. Prepare Data for Bar Chart (Top 5 Debtors)
    // Sort items by total_deuda desc
    const sortedDebtors = [...(data?.items || [])].sort((a, b) => b.total_deuda - a.total_deuda).slice(0, 5);

    // Reverse for horizontal bar chart (to show highest at top if using inverse, or just reverse array)
    // ECharts category axis usually draws bottom-to-top. For top-to-bottom list feel, we often provide data in reverse.
    const topDebtors = [...sortedDebtors].reverse();

    const barOption = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: any) => {
                const p = params[0];
                return `${p.name}: <b>${formatCurrency(p.value)}</b>`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'value',
            axisLabel: {
                formatter: (value: number) => `$${(value / 1000).toFixed(0)}k`
            }
        },
        yAxis: {
            type: 'category',
            data: topDebtors.map(d => d.nombre_cliente.length > 15 ? d.nombre_cliente.substring(0, 15) + '...' : d.nombre_cliente),
            axisLabel: {
                interval: 0
            }
        },
        series: [
            {
                name: 'Deuda Total',
                type: 'bar',
                data: topDebtors.map(d => d.total_deuda),
                itemStyle: {
                    color: '#1890ff',
                    borderRadius: [0, 4, 4, 0]
                },
                label: {
                    show: true,
                    position: 'right',
                    formatter: (p: any) => formatCurrency(p.value)
                }
            }
        ]
    };

    return (
        <div style={{ marginBottom: 24 }}>
            <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col xs={24} sm={12} md={6}>
                    <Card bordered={false}>
                        <Statistic
                            title="Cartera Vencida Total"
                            value={data?.total_general_vencido || 0}
                            precision={2}
                            valueStyle={{ color: '#cf1322' }}
                            prefix={<DollarOutlined />}
                            suffix="MXN"
                            loading={loading}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card bordered={false}>
                        <Statistic
                            title="Clientes con Deuda"
                            value={data?.items.length || 0}
                            prefix={<TeamOutlined />}
                            loading={loading}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card bordered={false}>
                        {/* Placeholder for DSO or other metric */}
                        <Statistic
                            title="Por Vencer (Próx.)"
                            value={data?.items.reduce((sum, i) => sum + i.por_vencer, 0) || 0}
                            precision={2}
                            valueStyle={{ color: '#3f8600' }}
                            prefix={<RiseOutlined />}
                            loading={loading}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card bordered={false}>
                        <Statistic
                            title="Mayor Deudor"
                            value={sortedDebtors.length > 0 ? sortedDebtors[0].nombre_cliente : '-'}
                            valueStyle={{ fontSize: 16 }}
                            prefix={<SolutionOutlined />}
                            loading={loading}
                        />
                    </Card>
                </Col>
            </Row>

            <Row gutter={16}>
                <Col xs={24} lg={12}>
                    <Card title="Distribución de Antigüedad" bordered={false} loading={loading}>
                        <ReactECharts option={pieOption} style={{ height: 300, width: '100%' }} />
                    </Card>
                </Col>
                <Col xs={24} lg={12}>
                    <Card title="Top 5 Deudores" bordered={false} loading={loading}>
                        <ReactECharts option={barOption} style={{ height: 300, width: '100%' }} />
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default CobranzaDashboard;
