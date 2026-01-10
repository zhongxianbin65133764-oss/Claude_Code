# API 文档

基础URL: `http://localhost:3000/api`

## 认证

除了登录和注册接口外，所有 API 都需要在请求头中携带 JWT Token：

```
Authorization: Bearer <token>
```

## 用户认证

### 注册

```
POST /auth/register
```

**请求体：**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "张三",
  "role": "USER"  // ADMIN | MANAGER | USER
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "name": "张三",
      "role": "USER"
    },
    "token": "jwt_token"
  }
}
```

### 登录

```
POST /auth/login
```

**请求体：**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "name": "张三",
      "role": "USER"
    },
    "token": "jwt_token"
  }
}
```

### 获取当前用户信息

```
GET /auth/me
```

**响应：**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "张三",
    "role": "USER",
    "createdAt": "2024-01-01T00:00:00.000Z"
  }
}
```

## 基金管理

### 创建基金

```
POST /funds
```

**权限：** ADMIN, MANAGER

**请求体：**
```json
{
  "name": "XX成长基金",
  "code": "FUND001",
  "type": "GROWTH",  // VC | PE | GROWTH | BUYOUT
  "totalSize": 100000,
  "currency": "CNY",
  "establishDate": "2024-01-01",
  "duration": 84,
  "managementFee": 0.02,
  "carriedInterest": 0.20,
  "description": "专注于科技领域的成长期投资"
}
```

### 获取基金列表

```
GET /funds?page=1&limit=10&status=INVESTING&type=PE
```

**查询参数：**
- `page`: 页码（默认 1）
- `limit`: 每页数量（默认 10）
- `status`: 基金状态（可选）
- `type`: 基金类型（可选）

### 获取基金详情

```
GET /funds/:id
```

### 更新基金

```
PUT /funds/:id
```

**权限：** ADMIN, MANAGER

### 删除基金

```
DELETE /funds/:id
```

**权限：** ADMIN

### 获取基金统计数据

```
GET /funds/statistics
```

**响应：**
```json
{
  "success": true,
  "data": {
    "totalFunds": 10,
    "fundsByStatus": [
      { "status": "FUNDRAISING", "_count": 2 },
      { "status": "INVESTING", "_count": 5 }
    ],
    "totalSize": 1000000,
    "raisedAmount": 800000,
    "totalInvestors": 50,
    "totalProjects": 30
  }
}
```

## 投资者管理

### 创建投资者

```
POST /investors
```

**权限：** ADMIN, MANAGER

**请求体：**
```json
{
  "name": "XX投资公司",
  "type": "INSTITUTION",  // INDIVIDUAL | INSTITUTION | GOVERNMENT
  "idNumber": "91110000XXXXXXXXXX",
  "contactName": "李四",
  "contactPhone": "13800138000",
  "contactEmail": "lisi@example.com",
  "commitment": 10000,
  "fundId": "fund_uuid",
  "joinDate": "2024-01-01"
}
```

### 获取基金的投资者列表

```
GET /investors/fund/:fundId
```

### 更新投资者

```
PUT /investors/:id
```

**权限：** ADMIN, MANAGER

### 删除投资者

```
DELETE /investors/:id
```

**权限：** ADMIN

## 项目管理

### 创建项目

```
POST /projects
```

**权限：** ADMIN, MANAGER

**请求体：**
```json
{
  "name": "XX科技公司",
  "code": "PROJ001",
  "industry": "人工智能",
  "stage": "B_ROUND",  // SEED | ANGEL | A_ROUND | B_ROUND | C_ROUND | PRE_IPO | GROWTH | MATURE
  "region": "北京",
  "description": "专注于AI技术研发",
  "fundId": "fund_uuid",
  "investmentAmount": 5000,
  "valuation": 50000,
  "shareholding": 0.10,
  "investmentDate": "2024-01-01"
}
```

### 获取项目列表

```
GET /projects?page=1&limit=10&status=INVESTED&stage=B_ROUND&fundId=fund_uuid
```

### 获取项目详情

```
GET /projects/:id
```

### 更新项目

```
PUT /projects/:id
```

**权限：** ADMIN, MANAGER

### 删除项目

```
DELETE /projects/:id
```

**权限：** ADMIN

### 创建尽职调查

```
POST /projects/:id/due-diligence
```

**权限：** ADMIN, MANAGER

**请求体：**
```json
{
  "financial": "财务状况良好，近三年营收持续增长...",
  "legal": "法律结构清晰，无重大法律纠纷...",
  "business": "商业模式可行，市场前景广阔...",
  "technical": "技术领先，拥有核心专利...",
  "riskAssessment": "主要风险包括市场竞争、政策变化...",
  "conclusion": "建议投资"
}
```

### 创建投后管理记录

```
POST /projects/:id/post-investment
```

**权限：** ADMIN, MANAGER

**请求体：**
```json
{
  "reportDate": "2024-03-31",
  "revenue": 10000,
  "profit": 2000,
  "keyMetrics": "{\"用户数\": 100000, \"月活\": 50000}",
  "issues": "需要加强市场推广",
  "actions": "计划投入更多营销资源"
}
```

### 创建退出记录

```
POST /projects/:id/exit
```

**权限：** ADMIN, MANAGER

**请求体：**
```json
{
  "exitType": "IPO",  // IPO | TRADE_SALE | SECONDARY | BUYBACK | WRITE_OFF
  "exitDate": "2024-12-31",
  "exitAmount": 20000,
  "returnMultiple": 4.0,
  "irr": 0.35,
  "description": "成功上市退出"
}
```

## 流程审批

### 创建工作流

```
POST /workflows
```

**权限：** ADMIN, MANAGER

**请求体：**
```json
{
  "projectId": "project_uuid",
  "type": "INVESTMENT_DECISION",  // PROJECT_INITIATION | INVESTMENT_DECISION | POST_INVESTMENT | EXIT_APPROVAL
  "totalSteps": 3,
  "description": "投资决策委员会审批"
}
```

### 获取项目的工作流列表

```
GET /workflows/project/:projectId
```

### 获取待审批列表

```
GET /workflows/my-approvals
```

### 审批通过

```
POST /workflows/:id/approve
```

**权限：** ADMIN, MANAGER

**请求体：**
```json
{
  "comments": "同意投资，建议增加投后监管"
}
```

### 审批拒绝

```
POST /workflows/:id/reject
```

**权限：** ADMIN, MANAGER

**请求体：**
```json
{
  "comments": "项目风险较大，暂不建议投资"
}
```

## 响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... }
}
```

### 错误响应

```json
{
  "success": false,
  "message": "错误信息"
}
```

## HTTP 状态码

- `200` - 成功
- `201` - 创建成功
- `400` - 请求参数错误
- `401` - 未认证
- `403` - 无权限
- `404` - 资源不存在
- `500` - 服务器错误

## 枚举值说明

### 用户角色 (UserRole)
- `ADMIN` - 管理员
- `MANAGER` - 经理
- `USER` - 普通用户

### 基金类型 (FundType)
- `VC` - 风险投资
- `PE` - 私募股权
- `GROWTH` - 成长基金
- `BUYOUT` - 并购基金

### 基金状态 (FundStatus)
- `FUNDRAISING` - 募集中
- `INVESTING` - 投资期
- `MANAGEMENT` - 管理期
- `EXIT` - 退出期
- `LIQUIDATED` - 已清算

### 投资者类型 (InvestorType)
- `INDIVIDUAL` - 个人
- `INSTITUTION` - 机构
- `GOVERNMENT` - 政府

### 项目阶段 (ProjectStage)
- `SEED` - 种子期
- `ANGEL` - 天使轮
- `A_ROUND` - A轮
- `B_ROUND` - B轮
- `C_ROUND` - C轮
- `PRE_IPO` - Pre-IPO
- `GROWTH` - 成长期
- `MATURE` - 成熟期

### 项目状态 (ProjectStatus)
- `SOURCING` - 项目寻源
- `SCREENING` - 初步筛选
- `DUE_DILIGENCE` - 尽职调查
- `DECISION` - 投资决策
- `INVESTED` - 已投资
- `POST_INVESTMENT` - 投后管理
- `EXITING` - 退出中
- `EXITED` - 已退出
- `REJECTED` - 已拒绝

### 退出类型 (ExitType)
- `IPO` - 上市
- `TRADE_SALE` - 并购
- `SECONDARY` - 二级市场出售
- `BUYBACK` - 回购
- `WRITE_OFF` - 减记

### 工作流类型 (WorkflowType)
- `PROJECT_INITIATION` - 项目立项
- `INVESTMENT_DECISION` - 投资决策
- `POST_INVESTMENT` - 投后管理
- `EXIT_APPROVAL` - 退出审批

### 工作流状态 (WorkflowStatus)
- `PENDING` - 待审批
- `APPROVED` - 已通过
- `REJECTED` - 已拒绝
- `CANCELLED` - 已取消
