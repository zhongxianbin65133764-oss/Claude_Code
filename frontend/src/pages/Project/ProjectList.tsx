import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Button, Space, Tag, message } from 'antd';
import { PlusOutlined, EyeOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const ProjectList = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  useEffect(() => {
    fetchProjects();
  }, [pagination.current, pagination.pageSize]);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const response: any = await api.get('/projects', {
        params: {
          page: pagination.current,
          limit: pagination.pageSize,
        },
      });
      if (response.success) {
        setProjects(response.data.projects);
        setPagination((prev) => ({
          ...prev,
          total: response.data.pagination.total,
        }));
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '获取项目列表失败');
    } finally {
      setLoading(false);
    }
  };

  const columns: ColumnsType<any> = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '项目编号',
      dataIndex: 'code',
      key: 'code',
    },
    {
      title: '所属基金',
      dataIndex: ['fund', 'name'],
      key: 'fund',
    },
    {
      title: '行业',
      dataIndex: 'industry',
      key: 'industry',
    },
    {
      title: '阶段',
      dataIndex: 'stage',
      key: 'stage',
      render: (stage) => getProjectStageName(stage),
    },
    {
      title: '投资金额',
      dataIndex: 'investmentAmount',
      key: 'investmentAmount',
      render: (value) => (value ? `${value.toLocaleString()} 万` : '-'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>{getProjectStatusName(status)}</Tag>
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
            onClick={() => navigate(`/projects/${record.id}`)}
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
      title="项目列表"
      extra={
        <Button type="primary" icon={<PlusOutlined />}>
          新建项目
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={projects}
        rowKey="id"
        loading={loading}
        pagination={pagination}
        onChange={handleTableChange}
      />
    </Card>
  );
};

const getProjectStageName = (stage: string) => {
  const stageMap: Record<string, string> = {
    SEED: '种子期',
    ANGEL: '天使轮',
    A_ROUND: 'A轮',
    B_ROUND: 'B轮',
    C_ROUND: 'C轮',
    PRE_IPO: 'Pre-IPO',
    GROWTH: '成长期',
    MATURE: '成熟期',
  };
  return stageMap[stage] || stage;
};

const getProjectStatusName = (status: string) => {
  const statusMap: Record<string, string> = {
    SOURCING: '项目寻源',
    SCREENING: '初步筛选',
    DUE_DILIGENCE: '尽职调查',
    DECISION: '投资决策',
    INVESTED: '已投资',
    POST_INVESTMENT: '投后管理',
    EXITING: '退出中',
    EXITED: '已退出',
    REJECTED: '已拒绝',
  };
  return statusMap[status] || status;
};

const getStatusColor = (status: string) => {
  const colorMap: Record<string, string> = {
    SOURCING: 'default',
    SCREENING: 'blue',
    DUE_DILIGENCE: 'cyan',
    DECISION: 'orange',
    INVESTED: 'green',
    POST_INVESTMENT: 'purple',
    EXITING: 'gold',
    EXITED: 'success',
    REJECTED: 'error',
  };
  return colorMap[status] || 'default';
};

export default ProjectList;
