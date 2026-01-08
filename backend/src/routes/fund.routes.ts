import express from 'express';
import {
  createFund,
  getAllFunds,
  getFundById,
  updateFund,
  deleteFund,
  getFundStatistics,
} from '../controllers/fund.controller';
import { authenticate, authorize } from '../middleware/auth';

const router = express.Router();

router.use(authenticate);

router.post('/', authorize('ADMIN', 'MANAGER'), createFund);
router.get('/', getAllFunds);
router.get('/statistics', getFundStatistics);
router.get('/:id', getFundById);
router.put('/:id', authorize('ADMIN', 'MANAGER'), updateFund);
router.delete('/:id', authorize('ADMIN'), deleteFund);

export default router;
