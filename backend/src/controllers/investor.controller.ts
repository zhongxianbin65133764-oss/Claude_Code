import { Response } from 'express';
import prisma from '../utils/prisma';
import { AuthRequest } from '../middleware/auth';

export const createInvestor = async (req: AuthRequest, res: Response) => {
  try {
    const {
      name,
      type,
      idNumber,
      contactName,
      contactPhone,
      contactEmail,
      commitment,
      fundId,
      joinDate,
    } = req.body;

    const fund = await prisma.fund.findUnique({ where: { id: fundId } });
    if (!fund) {
      return res.status(404).json({ success: false, message: '基金不存在' });
    }

    const investor = await prisma.investor.create({
      data: {
        name,
        type,
        idNumber,
        contactName,
        contactPhone,
        contactEmail,
        commitment,
        fundId,
        joinDate: new Date(joinDate),
      },
    });

    res.status(201).json({ success: true, data: investor });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const getInvestorsByFund = async (req: AuthRequest, res: Response) => {
  try {
    const { fundId } = req.params;

    const investors = await prisma.investor.findMany({
      where: { fundId },
      include: {
        fund: {
          select: {
            id: true,
            name: true,
            code: true,
          },
        },
      },
      orderBy: { joinDate: 'desc' },
    });

    res.json({ success: true, data: investors });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const updateInvestor = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const data = req.body;

    if (data.joinDate) {
      data.joinDate = new Date(data.joinDate);
    }

    const investor = await prisma.investor.update({
      where: { id },
      data,
    });

    res.json({ success: true, data: investor });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};

export const deleteInvestor = async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;

    await prisma.investor.delete({ where: { id } });

    res.json({ success: true, message: '投资者已删除' });
  } catch (error: any) {
    res.status(500).json({ success: false, message: error.message });
  }
};
