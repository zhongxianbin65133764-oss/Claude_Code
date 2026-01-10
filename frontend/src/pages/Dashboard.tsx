import { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import {
  FundOutlined,
  ProjectOutlined,
  UserOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import api from '../services/api';

const Dashboard = () => {
  const [statistics, setStatistics] = useState<any>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStatistics();
  }, []);

  const fetchStatistics = async () => {
    try {
      const response: any = await api.get('/funds/statistics');
      if (response.success) {
        setStatistics(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>工作台</h1>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="基金总数"
              value={statistics.totalFunds || 0}
              prefix={<FundOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="项目总数"
              value={statistics.totalProjects || 0}
              prefix={<ProjectOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="投资者总数"
              value={statistics.totalInvestors || 0}
              prefix={<UserOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="基金总规模"
              value={statistics.totalSize || 0}
              precision={2}
              prefix={<RiseOutlined />}
              suffix="万"
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="基金状态分布" loading={loading}>
            <Row gutter={16}>
              {statistics.fundsByStatus?.map((item: any) => (
                <Col key={item.status} span={6}>
                  <Statistic
                    title={getFundStatusName(item.status)}
                    value={item._count}
                  />
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

const getFundStatusName = (status: string) => {
  const statusMap: Record<string, string> = {
    FUNDRAISING: '募集中',
    INVESTING: '投资期',
    MANAGEMENT: '管理期',
    EXIT: '退出期',
    LIQUIDATED: '已清算',
  };
  return statusMap[status] || status;
};

export default Dashboard;
