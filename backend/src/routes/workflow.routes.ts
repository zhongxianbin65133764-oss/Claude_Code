import express from 'express';
import {
  createWorkflow,
  getWorkflowsByProject,
  approveWorkflow,
  rejectWorkflow,
  getMyPendingApprovals,
} from '../controllers/workflow.controller';
import { authenticate, authorize } from '../middleware/auth';

const router = express.Router();

router.use(authenticate);

router.post('/', authorize('ADMIN', 'MANAGER'), createWorkflow);
router.get('/project/:projectId', getWorkflowsByProject);
router.get('/my-approvals', getMyPendingApprovals);
router.post('/:id/approve', authorize('ADMIN', 'MANAGER'), approveWorkflow);
router.post('/:id/reject', authorize('ADMIN', 'MANAGER'), rejectWorkflow);

export default router;
