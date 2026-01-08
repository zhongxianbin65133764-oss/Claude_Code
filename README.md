# 私募股权基金管理系统

一个功能完整的私募股权基金管理系统，包含基金管理、项目管理和流程审批功能。

## 功能特性

### 基金管理
- 基金基本信息管理
- 基金募集管理
- 投资者管理
- 资金管理（实缴、待缴、分配）
- 基金净值计算

### 项目管理
- 项目信息管理
- 项目评估与尽职调查
- 投资决策记录
- 投后管理跟踪
- 退出管理

### 流程管理
- 项目立项审批流程
- 投资决策审批流程
- 投后管理流程
- 退出审批流程

## 技术栈

### 后端
- Node.js + Express
- TypeScript
- Prisma ORM
- PostgreSQL
- JWT 认证

### 前端
- React 18
- TypeScript
- Vite
- Ant Design
- React Router
- Axios

## 项目结构

```
├── backend/          # 后端服务
│   ├── src/
│   │   ├── controllers/   # 控制器
│   │   ├── models/        # 数据模型
│   │   ├── routes/        # 路由
│   │   ├── services/      # 业务逻辑
│   │   ├── middleware/    # 中间件
│   │   └── utils/         # 工具函数
│   ├── prisma/            # Prisma schema
│   └── package.json
│
└── frontend/         # 前端应用
    ├── src/
    │   ├── components/    # 组件
    │   ├── pages/         # 页面
    │   ├── services/      # API 服务
    │   ├── store/         # 状态管理
    │   └── utils/         # 工具函数
    └── package.json
```

## 快速开始

### 后端启动

```bash
cd backend
npm install
npm run dev
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 环境要求

- Node.js >= 18
- PostgreSQL >= 14
- npm >= 9

## 默认端口

- 后端：http://localhost:3000
- 前端：http://localhost:5173

## License

MIT