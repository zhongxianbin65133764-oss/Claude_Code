import { Response } from 'express';
import prisma from '../utils/prisma';
import { AuthRequest } from '../middleware/auth';

export const createProject = async (req: AuthRequest, res: Response) => {
  try {
    const {
      name,
      code,
      industry,
      stage,
      region,
      description,
      fundId,
      investmentAmount,
      valuation,
      shareholding,
      investmentDate,
    } = req.body;

    const existingProject = await prisma.project.findUnique({ where: { code } });
    if (existingProject) {
      return res.status(400).json({ success: false, message: '项目编号已存在' });
    }

    const fund = await prisma.fund.findUnique({ where: { id: fundId } });
    if (!fund) {
      return res.status(404).json({ success: false, message: '基金不存在' });
    }

    const project = await prisma.project.create({
      data: {
        name,
        code,
        industry,
        stage,
        region,
        description,
        fundId,
        investmentAmount,
        valuation,
        shareholding,
        investmentDate: investmentDate ? new Date(investmentDate) : null,
        creatorId: req.user!.id,
      },
    });

    res.status(201).json({ success: true, data: project });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const getAllProjects = async (req: AuthRequest, res: Response) => {
  try {
    const { status, stage, fundId, page = 1, limit = 10 } = req.query;

    const where: any = {};
    if (status) where.status = status;
    if (stage) where.stage = stage;
    if (fundId) where.fundId = fundId;

    const skip = (Number(page) - 1) * Number(limit);

    const [projects, total] = await Promise.all([
      prisma.project.findMany({
        where,
        include: {
          creator: {
            select: {
              id: true,
              name: true,
              email: true,
            },
          },
          fund: {
            select: {
              id: true,
              name: true,
              code: true,
            },
          },
          dueDiligence: true,
          _count: {
            select: {
              postInvestments: true,
              exitRecords: true,
            },
          },
        },
        skip,
        take: Number(limit),
        orderBy: { createdAt: 'desc' },
      }),
      prisma.project.count({ where }),
    ]);

    res.json({
      success: true,
      data: {
        projects,
        pagination: {
          total,
          page: Number(page),
          limit: Number(limit),
          pages: Math.ceil(total / Number(limit)),
        },
      },
    });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const getProjectById = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;

    const project = await prisma.project.findUnique({
      where: { id },
      include: {
        creator: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
        fund: true,
        dueDiligence: true,
        postInvestments: {
          orderBy: { reportDate: 'desc' },
        },
        exitRecords: true,
        workflows: {
          include: {
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
        },
      },
    });

    if (!project) {
      return res.status(404).json({ success: false, message: '项目不存在' });
    }

    res.json({ success: true, data: project });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const updateProject = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const data = req.body;

    if (data.investmentDate) {
      data.investmentDate = new Date(data.investmentDate);
    }

    const project = await prisma.project.update({
      where: { id },
      data,
    });

    res.json({ success: true, data: project });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const deleteProject = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;

    await prisma.project.delete({ where: { id } });

    res.json({ success: true, message: '项目已删除' });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const createDueDiligence = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const { financial, legal, business, technical, riskAssessment, conclusion } = req.body;

    const project = await prisma.project.findUnique({ where: { id } });
    if (!project) {
      return res.status(404).json({ success: false, message: '项目不存在' });
    }

    const dueDiligence = await prisma.dueDiligence.upsert({
      where: { projectId: id },
      update: {
        financial,
        legal,
        business,
        technical,
        riskAssessment,
        conclusion,
      },
      create: {
        projectId: id,
        financial,
        legal,
        business,
        technical,
        riskAssessment,
        conclusion,
      },
    });

    res.status(201).json({ success: true, data: dueDiligence });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const createPostInvestment = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const { reportDate, revenue, profit, keyMetrics, issues, actions } = req.body;

    const project = await prisma.project.findUnique({ where: { id } });
    if (!project) {
      return res.status(404).json({ success: false, message: '项目不存在' });
    }

    const postInvestment = await prisma.postInvestment.create({
      data: {
        projectId: id,
        reportDate: new Date(reportDate),
        revenue,
        profit,
        keyMetrics,
        issues,
        actions,
      },
    });

    res.status(201).json({ success: true, data: postInvestment });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const createExitRecord = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const { exitType, exitDate, exitAmount, returnMultiple, irr, description } = req.body;

    const project = await prisma.project.findUnique({ where: { id } });
    if (!project) {
      return res.status(404).json({ success: false, message: '项目不存在' });
    }

    const exitRecord = await prisma.exitRecord.create({
      data: {
        projectId: id,
        exitType,
        exitDate: new Date(exitDate),
        exitAmount,
        returnMultiple,
        irr,
        description,
      },
    });

    // 更新项目状态为已退出
    await prisma.project.update({
      where: { id },
      data: { status: 'EXITED' },
    });

    res.status(201).json({ success: true, data: exitRecord });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};
