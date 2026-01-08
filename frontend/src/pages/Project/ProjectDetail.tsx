import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Descriptions, Table, Tabs, Tag, message, Spin } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const ProjectDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchProjectDetail();
    }
  }, [id]);

  const fetchProjectDetail = async () => {
    setLoading(true);
    try {
      const response: any = await api.get(`/projects/${id}`);
      if (response.success) {
        setProject(response.data);
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '获取项目详情失败');
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

  if (!project) {
    return <Card>项目不存在</Card>;
  }

  const postInvestmentColumns: ColumnsType<any> = [
    {
      title: '报告日期',
      dataIndex: 'reportDate',
      key: 'reportDate',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: '营收',
      dataIndex: 'revenue',
      key: 'revenue',
      render: (value) => (value ? `${value.toLocaleString()} 万` : '-'),
    },
    {
      title: '利润',
      dataIndex: 'profit',
      key: 'profit',
      render: (value) => (value ? `${value.toLocaleString()} 万` : '-'),
    },
    { title: '问题记录', dataIndex: 'issues', key: 'issues' },
  ];

  const workflowColumns: ColumnsType<any> = [
    { title: '流程类型', dataIndex: 'type', key: 'type' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getWorkflowStatusColor(status)}>
          {getWorkflowStatusName(status)}
        </Tag>
      ),
    },
    {
      title: '当前步骤',
      key: 'step',
      render: (_, record) => `${record.currentStep}/${record.totalSteps}`,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date) => new Date(date).toLocaleString(),
    },
  ];

  const tabItems = [
    {
      key: 'due-diligence',
      label: '尽职调查',
      children: project.dueDiligence ? (
        <Descriptions bordered column={1}>
          <Descriptions.Item label="财务尽调">
            {project.dueDiligence.financial || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="法律尽调">
            {project.dueDiligence.legal || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="商业尽调">
            {project.dueDiligence.business || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="技术尽调">
            {project.dueDiligence.technical || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="风险评估">
            {project.dueDiligence.riskAssessment || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="尽调结论">
            {project.dueDiligence.conclusion || '-'}
          </Descriptions.Item>
        </Descriptions>
      ) : (
        <div>暂无尽职调查数据</div>
      ),
    },
    {
      key: 'post-investment',
      label: '投后管理',
      children: (
        <Table
          columns={postInvestmentColumns}
          dataSource={project.postInvestments}
          rowKey="id"
          pagination={false}
        />
      ),
    },
    {
      key: 'workflows',
      label: '审批流程',
      children: (
        <Table
          columns={workflowColumns}
          dataSource={project.workflows}
          rowKey="id"
          pagination={false}
        />
      ),
    },
  ];

  return (
    <div>
      <Card title="项目基本信息" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="项目名称">
            {project.name}
          </Descriptions.Item>
          <Descriptions.Item label="项目编号">
            {project.code}
          </Descriptions.Item>
          <Descriptions.Item label="所属基金">
            {project.fund?.name}
          </Descriptions.Item>
          <Descriptions.Item label="行业">
            {project.industry}
          </Descriptions.Item>
          <Descriptions.Item label="阶段">
            {getProjectStageName(project.stage)}
          </Descriptions.Item>
          <Descriptions.Item label="地区">
            {project.region}
          </Descriptions.Item>
          <Descriptions.Item label="投资金额">
            {project.investmentAmount
              ? `${project.investmentAmount.toLocaleString()} 万`
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="估值">
            {project.valuation
              ? `${project.valuation.toLocaleString()} 万`
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="持股比例">
            {project.shareholding
              ? `${(project.shareholding * 100).toFixed(2)}%`
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="投资日期">
            {project.investmentDate
              ? new Date(project.investmentDate).toLocaleDateString()
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={getStatusColor(project.status)}>
              {getProjectStatusName(project.status)}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="项目描述" span={2}>
            {project.description || '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card>
        <Tabs items={tabItems} />
      </Card>
    </div>
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

const getWorkflowStatusName = (status: string) => {
  const statusMap: Record<string, string> = {
    PENDING: '待审批',
    APPROVED: '已通过',
    REJECTED: '已拒绝',
    CANCELLED: '已取消',
  };
  return statusMap[status] || status;
};

const getWorkflowStatusColor = (status: string) => {
  const colorMap: Record<string, string> = {
    PENDING: 'processing',
    APPROVED: 'success',
    REJECTED: 'error',
    CANCELLED: 'default',
  };
  return colorMap[status] || 'default';
};

export default ProjectDetail;
