import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import fundRoutes from './routes/fund.routes';
import projectRoutes from './routes/project.routes';
import workflowRoutes from './routes/workflow.routes';
import authRoutes from './routes/auth.routes';
import investorRoutes from './routes/investor.routes';
import { errorHandler } from './middleware/errorHandler';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 路由
app.use('/api/auth', authRoutes);
app.use('/api/funds', fundRoutes);
app.use('/api/projects', projectRoutes);
app.use('/api/workflows', workflowRoutes);
app.use('/api/investors', investorRoutes);

// 健康检查
app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'PE Fund Management System API is running' });
});

// 错误处理
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`🚀 Server is running on http://localhost:${PORT}`);
});
