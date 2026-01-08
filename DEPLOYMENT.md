# 部署说明

## 环境准备

### 1. 安装依赖软件

- Node.js 18 或更高版本
- PostgreSQL 14 或更高版本
- npm 9 或更高版本

### 2. 配置数据库

```bash
# 登录 PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE pe_fund_db;

# 创建用户（可选）
CREATE USER pe_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE pe_fund_db TO pe_user;
```

## 后端部署

### 1. 安装依赖

```bash
cd backend
npm install
```

### 2. 配置环境变量

复制 `.env.example` 并创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下变量：

```env
PORT=3000
DATABASE_URL="postgresql://pe_user:your_password@localhost:5432/pe_fund_db"
JWT_SECRET=your-very-secure-random-secret-key
JWT_EXPIRES_IN=7d
NODE_ENV=production
```

### 3. 初始化数据库

```bash
# 生成 Prisma Client
npm run prisma:generate

# 执行数据库迁移
npm run prisma:migrate
```

### 4. 创建管理员账户

可以通过 API 或 Prisma Studio 创建初始管理员账户：

```bash
# 打开 Prisma Studio
npm run prisma:studio
```

在浏览器中访问 http://localhost:5555，手动创建第一个管理员用户。

### 5. 启动后端服务

```bash
# 开发环境
npm run dev

# 生产环境
npm run build
npm start
```

后端服务将在 http://localhost:3000 启动。

## 前端部署

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置 API 地址

如果后端部署在不同的服务器，需要修改 `vite.config.ts` 中的代理配置：

```typescript
proxy: {
  '/api': {
    target: 'http://your-backend-server:3000',
    changeOrigin: true,
  },
}
```

或者在生产环境中，修改 `src/services/api.ts` 的 `baseURL`：

```typescript
const api = axios.create({
  baseURL: 'http://your-backend-server:3000/api',
  timeout: 10000,
});
```

### 3. 构建生产版本

```bash
npm run build
```

构建完成后，`dist` 目录包含所有静态文件。

### 4. 部署静态文件

可以使用以下任一方式部署：

#### 方式 1：使用 Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

#### 方式 2：使用 serve

```bash
npm install -g serve
serve -s dist -l 5173
```

## Docker 部署（推荐）

### 1. 创建 Dockerfile（后端）

在 `backend` 目录创建 `Dockerfile`：

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
```

### 2. 创建 Dockerfile（前端）

在 `frontend` 目录创建 `Dockerfile`：

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

### 3. 创建 docker-compose.yml

在项目根目录创建：

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: pe_fund_db
      POSTGRES_USER: pe_user
      POSTGRES_PASSWORD: your_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://pe_user:your_password@postgres:5432/pe_fund_db
      JWT_SECRET: your-secret-key
      NODE_ENV: production
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

### 4. 启动服务

```bash
docker-compose up -d
```

## 生产环境注意事项

1. **安全性**
   - 更改默认的 JWT_SECRET
   - 使用 HTTPS
   - 配置 CORS 白名单
   - 定期更新依赖包

2. **性能优化**
   - 启用数据库连接池
   - 使用 Redis 缓存
   - 配置 CDN
   - 启用 Gzip 压缩

3. **监控与日志**
   - 配置应用监控（如 PM2）
   - 设置日志收集
   - 配置错误追踪

4. **备份**
   - 定期备份数据库
   - 配置自动备份脚本

## 故障排查

### 数据库连接失败
- 检查 DATABASE_URL 配置是否正确
- 确认 PostgreSQL 服务已启动
- 检查防火墙设置

### 前端无法连接后端
- 检查后端服务是否正常运行
- 确认 API 代理配置正确
- 检查 CORS 配置

### 登录失败
- 确认用户已在数据库中创建
- 检查密码是否正确（bcrypt 加密）
- 查看 JWT_SECRET 配置

## 技术支持

如有问题，请查看项目 README.md 或提交 Issue。
