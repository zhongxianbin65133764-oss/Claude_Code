import { Response } from 'express';
import prisma from '../utils/prisma';
import { AuthRequest } from '../middleware/auth';

export const createWorkflow = async (req: AuthRequest, res: Response) => {
  try {
    const { projectId, type, totalSteps, description } = req.body;

    const project = await prisma.project.findUnique({ where: { id: projectId } });
    if (!project) {
      return res.status(404).json({ success: false, message: '项目不存在' });
    }

    const workflow = await prisma.workflow.create({
      data: {
        projectId,
        type,
        totalSteps,
        initiator: req.user!.id,
        description,
      },
    });

    res.status(201).json({ success: true, data: workflow });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const getWorkflowsByProject = async (req: AuthRequest, res: Response) => {
  try {
    const { projectId } = req.params;

    const workflows = await prisma.workflow.findMany({
      where: { projectId },
      include: {
        project: {
          select: {
            id: true,
            name: true,
            code: true,
          },
        },
        approvalRecords: {
          include: {
            approver: {
              select: {
                id: true,
                name: true,
                email: true,
              },
            },
          },
          orderBy: { createdAt: 'asc' },
        },
      },
      orderBy: { createdAt: 'desc' },
    });

    res.json({ success: true, data: workflows });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const approveWorkflow = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const { comments } = req.body;

    const workflow = await prisma.workflow.findUnique({
      where: { id },
      include: { approvalRecords: true },
    });

    if (!workflow) {
      return res.status(404).json({ success: false, message: '工作流不存在' });
    }

    if (workflow.status !== 'PENDING') {
      return res.status(400).json({ success: false, message: '工作流已处理' });
    }

    // 创建审批记录
    await prisma.approvalRecord.create({
      data: {
        workflowId: id,
        approverId: req.user!.id,
        step: workflow.currentStep,
        action: 'APPROVE',
        comments,
      },
    });

    // 判断是否完成所有审批
    if (workflow.currentStep >= workflow.totalSteps) {
      await prisma.workflow.update({
        where: { id },
        data: { status: 'APPROVED' },
      });

      // 根据工作流类型更新项目状态
      if (workflow.type === 'PROJECT_INITIATION') {
        await prisma.project.update({
          where: { id: workflow.projectId },
          data: { status: 'SCREENING' },
        });
      } else if (workflow.type === 'INVESTMENT_DECISION') {
        await prisma.project.update({
          where: { id: workflow.projectId },
          data: { status: 'INVESTED' },
        });
      }
    } else {
      await prisma.workflow.update({
        where: { id },
        data: { currentStep: workflow.currentStep + 1 },
      });
    }

    const updatedWorkflow = await prisma.workflow.findUnique({
      where: { id },
      include: { approvalRecords: true },
    });

    res.json({ success: true, data: updatedWorkflow });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const rejectWorkflow = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const { comments } = req.body;

    const workflow = await prisma.workflow.findUnique({ where: { id } });

    if (!workflow) {
      return res.status(404).json({ success: false, message: '工作流不存在' });
    }

    if (workflow.status !== 'PENDING') {
      return res.status(400).json({ success: false, message: '工作流已处理' });
    }

    // 创建审批记录
    await prisma.approvalRecord.create({
      data: {
        workflowId: id,
        approverId: req.user!.id,
        step: workflow.currentStep,
        action: 'REJECT',
        comments,
      },
    });

    // 更新工作流状态为已拒绝
    await prisma.workflow.update({
      where: { id },
      data: { status: 'REJECTED' },
    });

    const updatedWorkflow = await prisma.workflow.findUnique({
      where: { id },
      include: { approvalRecords: true },
    });

    res.json({ success: true, data: updatedWorkflow });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const getMyPendingApprovals = async (req: AuthRequest, res: Response) => {
  try {
    // 获取待审批的工作流（当前步骤尚未被该用户审批）
    const workflows = await prisma.workflow.findMany({
      where: {
        status: 'PENDING',
      },
      include: {
        project: {
          select: {
            id: true,
            name: true,
            code: true,
            fund: {
              select: {
                id: true,
                name: true,
              },
            },
          },
        },
        approvalRecords: {
          include: {
            approver: {
              select: {
                id: true,
                name: true,
                email: true,
              },
            },
          },
        },
      },
      orderBy: { createdAt: 'desc' },
    });

    res.json({ success: true, data: workflows });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};
