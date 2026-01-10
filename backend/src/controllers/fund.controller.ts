import { Response } from 'express';
import prisma from '../utils/prisma';
import { AuthRequest } from '../middleware/auth';

export const createFund = async (req: AuthRequest, res: Response) => {
  try {
    const {
      name,
      code,
      type,
      totalSize,
      currency,
      establishDate,
      duration,
      managementFee,
      carriedInterest,
      description,
    } = req.body;

    const existingFund = await prisma.fund.findUnique({ where: { code } });
    if (existingFund) {
      return res.status(400).json({ success: false, message: '基金编号已存在' });
    }

    const fund = await prisma.fund.create({
      data: {
        name,
        code,
        type,
        totalSize,
        currency: currency || 'CNY',
        establishDate: new Date(establishDate),
        duration,
        managementFee,
        carriedInterest,
        description,
        creatorId: req.user!.id,
      },
    });

    res.status(201).json({ success: true, data: fund });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const getAllFunds = async (req: AuthRequest, res: Response) => {
  try {
    const { status, type, page = 1, limit = 10 } = req.query;

    const where: any = {};
    if (status) where.status = status;
    if (type) where.type = type;

    const skip = (Number(page) - 1) * Number(limit);

    const [funds, total] = await Promise.all([
      prisma.fund.findMany({
        where,
        include: {
          creator: {
            select: {
              id: true,
              name: true,
              email: true,
            },
          },
          _count: {
            select: {
              investors: true,
              projects: true,
            },
          },
        },
        skip,
        take: Number(limit),
        orderBy: { createdAt: 'desc' },
      }),
      prisma.fund.count({ where }),
    ]);

    res.json({
      success: true,
      data: {
        funds,
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

export const getFundById = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;

    const fund = await prisma.fund.findUnique({
      where: { id },
      include: {
        creator: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
        investors: true,
        projects: {
          select: {
            id: true,
            name: true,
            code: true,
            status: true,
            investmentAmount: true,
          },
        },
        navRecords: {
          orderBy: { date: 'desc' },
          take: 10,
        },
      },
    });

    if (!fund) {
      return res.status(404).json({ success: false, message: '基金不存在' });
    }

    res.json({ success: true, data: fund });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const updateFund = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const data = req.body;

    if (data.establishDate) {
      data.establishDate = new Date(data.establishDate);
    }

    const fund = await prisma.fund.update({
      where: { id },
      data,
    });

    res.json({ success: true, data: fund });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const deleteFund = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;

    await prisma.fund.delete({ where: { id } });

    res.json({ success: true, message: '基金已删除' });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const getFundStatistics = async (req: AuthRequest, res: Response) => {
  try {
    const totalFunds = await prisma.fund.count();

    const fundsByStatus = await prisma.fund.groupBy({
      by: ['status'],
      _count: true,
    });

    const totalSize = await prisma.fund.aggregate({
      _sum: {
        totalSize: true,
        raisedAmount: true,
      },
    });

    const totalInvestors = await prisma.investor.count();
    const totalProjects = await prisma.project.count();

    res.json({
      success: true,
      data: {
        totalFunds,
        fundsByStatus,
        totalSize: totalSize._sum.totalSize,
        raisedAmount: totalSize._sum.raisedAmount,
        totalInvestors,
        totalProjects,
      },
    });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};
