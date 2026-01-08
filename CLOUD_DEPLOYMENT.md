# 云端部署指南

本指南将帮助你将私募股权基金管理系统部署到云端，实现通过网页直接访问。

## 部署架构

- **后端 + 数据库**: Railway 或 Render（免费）
- **前端**: Vercel 或 Netlify（免费）
- **总成本**: 完全免费（有使用限制）

部署完成后，你将获得：
- 前端网站地址：`https://your-project.vercel.app`
- 后端 API 地址：`https://your-backend.railway.app`

---

## 方案一：Railway + Vercel（推荐）

### 第一步：部署后端到 Railway

#### 1. 创建 Railway 账户

访问 [railway.app](https://railway.app) 并使用 GitHub 账号登录。

#### 2. 创建新项目

1. 点击 "New Project"
2. 选择 "Deploy from GitHub repo"
3. 授权 Railway 访问你的 GitHub 仓库
4. 选择 `Claude_Code` 仓库

#### 3. 添加 PostgreSQL 数据库

1. 在项目中点击 "New"
2. 选择 "Database" → "Add PostgreSQL"
3. Railway 会自动创建数据库并生成连接字符串

#### 4. 配置后端服务

1. 点击后端服务（如果没有自动创建，点击 "New" → "GitHub Repo"）
2. 设置 "Root Directory" 为 `backend`
3. 配置环境变量：
   - 点击 "Variables"
   - 添加以下变量：

```bash
NODE_ENV=production
JWT_SECRET=你的超级安全密钥（随机生成32位字符串）
JWT_EXPIRES_IN=7d
PORT=3000
```

4. `DATABASE_URL` 会自动从 PostgreSQL 服务中引用
   - 点击 "New Variable" → "Reference" → 选择 PostgreSQL 的 DATABASE_URL

#### 5. 部署

1. Railway 会自动检测到 `Dockerfile` 并开始构建
2. 等待部署完成（约 3-5 分钟）
3. 部署成功后，点击 "Settings" → "Generate Domain" 生成公网域名
4. 记录下生成的域名，例如：`https://your-backend.railway.app`

#### 6. 初始化数据库

部署成功后，数据库会自动执行迁移（在 Dockerfile 中配置了）。

---

### 第二步：部署前端到 Vercel

#### 1. 创建 Vercel 账户

访问 [vercel.com](https://vercel.com) 并使用 GitHub 账号登录。

#### 2. 导入项目

1. 点击 "Add New..." → "Project"
2. 选择 `Claude_Code` 仓库
3. 点击 "Import"

#### 3. 配置项目

1. **Framework Preset**: Vite
2. **Root Directory**: 点击 "Edit" → 选择 `frontend`
3. **Build Command**: `npm run build`
4. **Output Directory**: `dist`
5. **Install Command**: `npm install`

#### 4. 配置环境变量

在 "Environment Variables" 部分添加：

```bash
VITE_API_URL=https://your-backend.railway.app/api
```

> ⚠️ 重要：将 `your-backend.railway.app` 替换为你在 Railway 第一步中生成的实际域名

#### 5. 部署

1. 点击 "Deploy"
2. 等待构建完成（约 1-2 分钟）
3. 部署成功后，Vercel 会显示你的网站地址，例如：
   - `https://your-project.vercel.app`

#### 6. 访问网站

打开 Vercel 提供的域名，你应该能看到登录页面。

---

### 第三步：配置 CORS（重要）

后端需要允许前端域名的跨域请求。

#### 1. 回到 Railway 后端服务

在环境变量中添加：

```bash
FRONTEND_URL=https://your-project.vercel.app
```

#### 2. 修改后端 CORS 配置

Railway 会自动重新部署。如果需要手动修改代码：

编辑 `backend/src/index.ts`，将 CORS 配置修改为：

```typescript
app.use(cors({
  origin: process.env.FRONTEND_URL || '*',
  credentials: true
}));
```

---

### 第四步：创建初始用户

由于这是全新的数据库，需要创建第一个管理员用户。

#### 方法 1：使用 Railway CLI

```bash
# 安装 Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 连接到项目
railway link

# 打开 Prisma Studio
railway run npx prisma studio
```

在浏览器中打开 Prisma Studio，手动创建第一个用户（记得密码要用 bcrypt 加密）。

#### 方法 2：通过 API 注册

直接访问：`https://your-backend.railway.app/api/auth/register`

使用 Postman 或 curl 发送 POST 请求：

```bash
curl -X POST https://your-backend.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Admin123456",
    "name": "系统管理员",
    "role": "ADMIN"
  }'
```

---

### 第五步：登录系统

1. 访问你的前端地址：`https://your-project.vercel.app`
2. 使用刚创建的账号登录
3. 开始使用系统！

---

## 方案二：Render + Netlify（备选）

### 部署后端到 Render

#### 1. 创建 Render 账户

访问 [render.com](https://render.com) 并注册。

#### 2. 创建新服务

1. 点击 "New +" → "Blueprint"
2. 连接 GitHub 仓库
3. Render 会自动检测 `render.yaml` 配置
4. 点击 "Apply" 创建服务

#### 3. 等待部署

Render 会自动创建 PostgreSQL 数据库和 Web 服务。

#### 4. 获取域名

部署完成后，记录 Web 服务的域名，例如：`https://your-backend.onrender.com`

### 部署前端到 Netlify

#### 1. 创建 Netlify 账户

访问 [netlify.com](https://www.netlify.com) 并注册。

#### 2. 导入项目

1. 点击 "Add new site" → "Import an existing project"
2. 选择 GitHub 仓库
3. Netlify 会自动检测 `netlify.toml` 配置

#### 3. 配置环境变量

在 "Site settings" → "Environment variables" 中添加：

```bash
VITE_API_URL=https://your-backend.onrender.com/api
```

#### 4. 部署

点击 "Deploy site"，等待构建完成。

---

## 常见问题排查

### 1. 前端无法连接后端

**症状**: 登录时提示网络错误

**解决方案**:
- 检查 Railway/Render 后端服务是否正常运行
- 确认 Vercel 环境变量 `VITE_API_URL` 设置正确
- 检查后端 CORS 配置是否包含前端域名
- 在浏览器开发者工具中查看网络请求详情

### 2. 数据库连接失败

**症状**: 后端日志显示数据库连接错误

**解决方案**:
- 确认 Railway/Render 的 PostgreSQL 服务正常运行
- 检查 `DATABASE_URL` 环境变量是否正确设置
- 查看数据库连接字符串格式是否正确

### 3. 登录后页面空白

**症状**: 登录成功但页面显示空白

**解决方案**:
- 打开浏览器控制台查看错误信息
- 检查 JWT Token 是否正确存储在 localStorage
- 确认后端 `/api/auth/me` 接口正常工作

### 4. Railway 免费额度用完

**症状**: 服务停止运行

**解决方案**:
- Railway 免费计划提供 $5/月 额度
- 可以升级到 Hobby 计划（$5/月）
- 或切换到 Render 免费计划

### 5. Vercel 构建失败

**症状**: 部署时构建错误

**解决方案**:
- 检查 Node.js 版本兼容性
- 查看构建日志中的具体错误
- 确保 `frontend` 目录下的依赖完整
- 尝试在本地运行 `npm run build` 测试

---

## 性能优化建议

### 1. 使用 CDN

Vercel 和 Netlify 都自动提供全球 CDN，无需额外配置。

### 2. 启用缓存

前端静态资源会自动缓存，API 响应可以通过添加 Cache-Control 头优化。

### 3. 数据库索引

确保数据库表有适当的索引（Prisma Schema 中已配置）。

### 4. 监控服务

- Railway Dashboard 提供基本的监控和日志
- Vercel Analytics 提供访问统计
- 考虑添加 Sentry 进行错误追踪

---

## 自定义域名（可选）

### Vercel 绑定域名

1. 在 Vercel 项目设置中选择 "Domains"
2. 添加你的域名（如 `fund.yourdomain.com`）
3. 按照提示在域名服务商处添加 DNS 记录
4. 等待 DNS 生效（通常几分钟到几小时）

### Railway 绑定域名

1. 在 Railway 服务设置中选择 "Settings"
2. 找到 "Domains" 部分
3. 添加自定义域名
4. 配置 DNS CNAME 记录指向 Railway 提供的地址

---

## 成本估算

### 免费方案
- **Railway**: $5/月 免费额度（约 500 小时运行时间）
- **Vercel**: 完全免费（个人项目）
- **总成本**: $0/月（小型项目足够使用）

### 付费方案（流量较大时）
- **Railway Hobby**: $5/月 起
- **Vercel Pro**: $20/月
- **Render**: $7/月 起

---

## 后续维护

### 更新代码

1. 推送代码到 GitHub
2. Railway 和 Vercel 会自动检测并重新部署
3. 无需手动操作

### 数据库备份

Railway 和 Render 的付费计划提供自动备份功能。免费计划建议定期手动导出数据：

```bash
# 使用 Railway CLI
railway run pg_dump $DATABASE_URL > backup.sql
```

### 查看日志

- **Railway**: 在 Dashboard 中点击服务 → "Deployments" → 查看日志
- **Vercel**: 在 Dashboard 中点击部署 → "Logs"

---

## 总结

完成以上步骤后，你的系统将完全运行在云端：

✅ 后端 API 部署在 Railway/Render
✅ PostgreSQL 数据库托管在云端
✅ 前端网站部署在 Vercel/Netlify
✅ 通过浏览器即可访问使用
✅ 支持多用户同时访问
✅ 自动 HTTPS 加密
✅ 全球 CDN 加速

---

## 技术支持

遇到问题？
1. 查看本文档的"常见问题排查"部分
2. 查看服务商的官方文档
3. 检查浏览器控制台和服务器日志
4. 提交 GitHub Issue
