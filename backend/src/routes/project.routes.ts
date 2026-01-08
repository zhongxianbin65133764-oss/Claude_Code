import express from 'express';
import {
  createProject,
  getAllProjects,
  getProjectById,
  updateProject,
  deleteProject,
  createDueDiligence,
  createPostInvestment,
  createExitRecord,
} from '../controllers/project.controller';
import { authenticate, authorize } from '../middleware/auth';

const router = express.Router();

router.use(authenticate);

router.post('/', authorize('ADMIN', 'MANAGER'), createProject);
router.get('/', getAllProjects);
router.get('/:id', getProjectById);
router.put('/:id', authorize('ADMIN', 'MANAGER'), updateProject);
router.delete('/:id', authorize('ADMIN'), deleteProject);

// 尽职调查
router.post('/:id/due-diligence', authorize('ADMIN', 'MANAGER'), createDueDiligence);

// 投后管理
router.post('/:id/post-investment', authorize('ADMIN', 'MANAGER'), createPostInvestment);

// 退出记录
router.post('/:id/exit', authorize('ADMIN', 'MANAGER'), createExitRecord);

export default router;
