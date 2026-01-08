import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Input, message } from 'antd';
import { CheckOutlined, CloseOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const { TextArea } = Input;

const WorkflowList = () => {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [currentWorkflow, setCurrentWorkflow] = useState<any>(null);
  const [action, setAction] = useState<'approve' | 'reject'>('approve');
  const [comments, setComments] = useState('');

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const response: any = await api.get('/workflows/my-approvals');
      if (response.success) {
        setWorkflows(response.data);
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '获取审批列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = (workflow: any) => {
    setCurrentWorkflow(workflow);
    setAction('approve');
    setModalVisible(true);
  };

  const handleReject = (workflow: any) => {
    setCurrentWorkflow(workflow);
    setAction('reject');
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const url = `/workflows/${currentWorkflow.id}/${action}`;
      const response: any = await api.post(url, { comments });
      if (response.success) {
        message.success(action === 'approve' ? '审批通过' : '已拒绝');
        setModalVisible(false);
        setComments('');
        fetchWorkflows();
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '操作失败');
    }
  };

  const columns: ColumnsType<any> = [
    {
      title: '项目名称',
      dataIndex: ['project', 'name'],
      key: 'projectName',
    },
    {
      title: '项目编号',
      dataIndex: ['project', 'code'],
      key: 'projectCode',
    },
    {
      title: '所属基金',
      dataIndex: ['project', 'fund', 'name'],
      key: 'fundName',
    },
    {
      title: '流程类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => getWorkflowTypeName(type),
    },
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
    {
      title: '操作',
      key: 'action',
      render: (_, record) =>
        record.status === 'PENDING' ? (
          <Space>
            <Button
              type="primary"
              size="small"
              icon={<CheckOutlined />}
              onClick={() => handleApprove(record)}
            >
              通过
            </Button>
            <Button
              danger
              size="small"
              icon={<CloseOutlined />}
              onClick={() => handleReject(record)}
            >
              拒绝
            </Button>
          </Space>
        ) : (
          '-'
        ),
    },
  ];

  return (
    <>
      <Card title="待审批流程">
        <Table
          columns={columns}
          dataSource={workflows}
          rowKey="id"
          loading={loading}
        />
      </Card>

      <Modal
        title={action === 'approve' ? '审批通过' : '拒绝审批'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setComments('');
        }}
        okText="确定"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <strong>项目名称：</strong>
          {currentWorkflow?.project?.name}
        </div>
        <div style={{ marginBottom: 16 }}>
          <strong>流程类型：</strong>
          {getWorkflowTypeName(currentWorkflow?.type)}
        </div>
        <TextArea
          rows={4}
          placeholder="请输入审批意见（可选）"
          value={comments}
          onChange={(e) => setComments(e.target.value)}
        />
      </Modal>
    </>
  );
};

const getWorkflowTypeName = (type: string) => {
  const typeMap: Record<string, string> = {
    PROJECT_INITIATION: '项目立项',
    INVESTMENT_DECISION: '投资决策',
    POST_INVESTMENT: '投后管理',
    EXIT_APPROVAL: '退出审批',
  };
  return typeMap[type] || type;
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

export default WorkflowList;
