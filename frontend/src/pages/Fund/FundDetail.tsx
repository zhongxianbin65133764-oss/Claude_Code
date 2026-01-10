import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Descriptions, Table, Tabs, message, Spin } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const FundDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [fund, setFund] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchFundDetail();
    }
  }, [id]);

  const fetchFundDetail = async () => {
    setLoading(true);
    try {
      const response: any = await api.get(`/funds/${id}`);
      if (response.success) {
        setFund(response.data);
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '获取基金详情失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!fund) {
    return <Card>基金不存在</Card>;
  }

  const investorColumns: ColumnsType<any> = [
    { title: '投资者名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'type', key: 'type' },
    { title: '联系人', dataIndex: 'contactName', key: 'contactName' },
    {
      title: '承诺出资',
      dataIndex: 'commitment',
      key: 'commitment',
      render: (value) => `${value.toLocaleString()} 万`,
    },
    {
      title: '已实缴',
      dataIndex: 'paidAmount',
      key: 'paidAmount',
      render: (value) => `${value.toLocaleString()} 万`,
    },
  ];

  const projectColumns: ColumnsType<any> = [
    { title: '项目名称', dataIndex: 'name', key: 'name' },
    { title: '项目编号', dataIndex: 'code', key: 'code' },
    { title: '状态', dataIndex: 'status', key: 'status' },
    {
      title: '投资金额',
      dataIndex: 'investmentAmount',
      key: 'investmentAmount',
      render: (value) => (value ? `${value.toLocaleString()} 万` : '-'),
    },
  ];

  const tabItems = [
    {
      key: 'investors',
      label: '投资者',
      children: (
        <Table
          columns={investorColumns}
          dataSource={fund.investors}
          rowKey="id"
          pagination={false}
        />
      ),
    },
    {
      key: 'projects',
      label: '投资项目',
      children: (
        <Table
          columns={projectColumns}
          dataSource={fund.projects}
          rowKey="id"
          pagination={false}
        />
      ),
    },
  ];

  return (
    <div>
      <Card title="基金基本信息" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="基金名称">{fund.name}</Descriptions.Item>
          <Descriptions.Item label="基金编号">{fund.code}</Descriptions.Item>
          <Descriptions.Item label="基金类型">
            {getFundTypeName(fund.type)}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            {getFundStatusName(fund.status)}
          </Descriptions.Item>
          <Descriptions.Item label="基金规模">
            {fund.totalSize.toLocaleString()} 万 {fund.currency}
          </Descriptions.Item>
          <Descriptions.Item label="已募集金额">
            {fund.raisedAmount.toLocaleString()} 万
          </Descriptions.Item>
          <Descriptions.Item label="存续期">
            {fund.duration} 个月
          </Descriptions.Item>
          <Descriptions.Item label="管理费率">
            {(fund.managementFee * 100).toFixed(2)}%
          </Descriptions.Item>
          <Descriptions.Item label="业绩报酬">
            {(fund.carriedInterest * 100).toFixed(2)}%
          </Descriptions.Item>
          <Descriptions.Item label="成立日期">
            {new Date(fund.establishDate).toLocaleDateString()}
          </Descriptions.Item>
          <Descriptions.Item label="基金描述" span={2}>
            {fund.description || '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card>
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
};

const getFundTypeName = (type: string) => {
  const typeMap: Record<string, string> = {
    VC: '风险投资',
    PE: '私募股权',
    GROWTH: '成长基金',
    BUYOUT: '并购基金',
  };
  return typeMap[type] || type;
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

export default FundDetail;
