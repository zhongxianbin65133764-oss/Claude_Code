import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Button, Space, Tag, message } from 'antd';
import { PlusOutlined, EyeOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import type { Fund } from '../../types';

const FundList = () => {
  const navigate = useNavigate();
  const [funds, setFunds] = useState<Fund[]>([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  useEffect(() => {
    fetchFunds();
  }, [pagination.current, pagination.pageSize]);

  const fetchFunds = async () => {
    setLoading(true);
    try {
      const response: any = await api.get('/funds', {
        params: {
          page: pagination.current,
          limit: pagination.pageSize,
        },
      });
      if (response.success) {
        setFunds(response.data.funds);
        setPagination((prev) => ({
          ...prev,
          total: response.data.pagination.total,
        }));
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '获取基金列表失败');
    } finally {
      setLoading(false);
    }
  };

  const columns: ColumnsType<Fund> = [
    {
      title: '基金名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '基金编号',
      dataIndex: 'code',
      key: 'code',
    },
    {
      title: '基金类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => getFundTypeName(type),
    },
    {
      title: '基金规模',
      dataIndex: 'totalSize',
      key: 'totalSize',
      render: (value) => `${value.toLocaleString()} 万`,
    },
    {
      title: '已募集',
      dataIndex: 'raisedAmount',
      key: 'raisedAmount',
      render: (value) => `${value.toLocaleString()} 万`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>{getFundStatusName(status)}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/funds/${record.id}`)}
          >
            查看
          </Button>
        </Space>
      ),
    },
  ];

  const handleTableChange = (newPagination: any) => {
    setPagination({
      current: newPagination.current,
      pageSize: newPagination.pageSize,
      total: pagination.total,
    });
  };

  return (
    <Card
      title="基金列表"
      extra={
        <Button type="primary" icon={<PlusOutlined />}>
          新建基金
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={funds}
        rowKey="id"
        loading={loading}
        pagination={pagination}
        onChange={handleTableChange}
      />
    </Card>
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

const getStatusColor = (status: string) => {
  const colorMap: Record<string, string> = {
    FUNDRAISING: 'blue',
    INVESTING: 'green',
    MANAGEMENT: 'orange',
    EXIT: 'purple',
    LIQUIDATED: 'default',
  };
  return colorMap[status] || 'default';
};

export default FundList;
