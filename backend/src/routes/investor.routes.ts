import express from 'express';
import {
  createInvestor,
  getInvestorsByFund,
  updateInvestor,
  deleteInvestor,
} from '../controllers/investor.controller';
import { authenticate, authorize } from '../middleware/auth';

const router = express.Router();

router.use(authenticate);

router.post('/', authorize('ADMIN', 'MANAGER'), createInvestor);
router.get('/fund/:fundId', getInvestorsByFund);
router.put('/:id', authorize('ADMIN', 'MANAGER'), updateInvestor);
router.delete('/:id', authorize('ADMIN'), deleteInvestor);

export default router;
