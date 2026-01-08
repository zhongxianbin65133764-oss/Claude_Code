---
name: commit-msg-generator
description: |
  根据代码变更自动生成符合规范的 Git 提交信息。
  当用户说"生成提交信息"、"写 commit message"、"帮我写提交描述"、
  "create commit message"或需要创建 Git 提交时使用。
allowed-tools: Bash, Read, Grep
model: claude-sonnet-4-5
---

# Git 提交信息生成器

## 目的
基于代码变更自动生成清晰、规范、有意义的 Git 提交信息，遵循最佳实践。

## 工作流程

### 1. 分析代码变更
首先了解变更内容：
```bash
# 查看暂存的变更
git diff --cached

# 如果暂存区为空，查看工作区变更
git diff

# 查看变更的文件列表
git status --short

# 查看最近的提交历史（了解项目的提交风格）
git log --oneline -10
```

### 2. 识别变更类型
根据变更内容判断类型：

- **feat** (feature)：新功能
  - 添加新的 API 端点
  - 实现新的用户功能
  - 增加新的组件或模块

- **fix**：修复 bug
  - 修复崩溃
  - 解决错误的行为
  - 修正计算错误

- **docs**：文档更新
  - 更新 README
  - 添加代码注释
  - 更新 API 文档

- **style**：代码格式（不影响功能）
  - 格式化代码
  - 修正缩进
  - 添加/删除空行

- **refactor**：重构（不改变功能）
  - 重命名变量
  - 提取函数
  - 重组代码结构

- **perf**：性能优化
  - 优化算法
  - 减少数据库查询
  - 改进响应速度

- **test**：测试相关
  - 添加测试
  - 修复测试
  - 提高测试覆盖率

- **build**：构建系统
  - 修改构建配置
  - 更新构建脚本
  - 调整打包流程

- **ci**：CI/CD 配置
  - 更新 GitHub Actions
  - 修改 CI 配置
  - 调整部署流程

- **chore**：其他杂项
  - 更新依赖
  - 修改配置文件
  - 更新 .gitignore

### 3. 确定变更范围（scope）
识别受影响的模块或组件：
- `auth`：认证相关
- `api`：API 相关
- `ui`：用户界面
- `db`：数据库
- `config`：配置
- `deps`：依赖
- 或项目特定的模块名

### 4. 编写提交信息

#### 格式规范（遵循 Conventional Commits）
```
<type>(<scope>): <subject>

<body>

<footer>
```

#### 主题行（subject）规则
- 不超过 50 个字符（中文约 25 个字）
- 使用命令式、现在时（"add" 而不是 "added" 或 "adds"）
- 首字母小写（除非是专有名词）
- 结尾不加句号
- 清晰描述"做了什么"

#### 正文（body）规则（可选但推荐）
- 与主题行之间空一行
- 每行不超过 72 个字符
- 解释"为什么"而不是"怎么做"
- 说明变更的动机和与之前行为的对比

#### 页脚（footer）规则（可选）
- 关联 Issue：`Closes #123` 或 `Fixes #456`
- 破坏性变更：`BREAKING CHANGE: 描述不兼容的变更`
- 其他引用：`Refs #789`

## 生成策略

### 单一变更
如果只有一个文件或一处修改，生成简洁的单行提交信息：
```
fix(auth): correct token expiration check
```

### 多个相关变更
如果多个变更属于同一个功能或修复，使用带正文的提交信息：
```
feat(api): add user profile endpoints

- Add GET /api/users/:id endpoint
- Add PUT /api/users/:id endpoint
- Add DELETE /api/users/:id endpoint
- Implement authentication middleware
- Add input validation

Closes #234
```

### 多个不相关变更
如果变更不相关，建议用户分开提交：
```
建议将以下变更分为多个提交：
1. feat(auth): add JWT support
2. fix(ui): correct button alignment
3. docs: update API documentation
```

## 示例

### 示例 1：新功能
**变更**：添加了用户注册功能
```
feat(auth): implement user registration

- Create registration API endpoint
- Add email validation
- Implement password hashing with bcrypt
- Add user model and database migration
- Create registration form component

Closes #123
```

### 示例 2：Bug 修复
**变更**：修复了购物车计算错误
```
fix(cart): correct total price calculation

Fix incorrect total when applying multiple discount codes.
Previously, discounts were applied sequentially instead of
being calculated against the original price.

Fixes #456
```

### 示例 3：重构
**变更**：重构了认证逻辑
```
refactor(auth): extract token validation to middleware

- Extract JWT validation logic from controllers
- Create reusable auth middleware
- Improve error handling for expired tokens
- Add unit tests for middleware

No functional changes, improves code maintainability.
```

### 示例 4：性能优化
**变更**：优化数据库查询
```
perf(db): optimize user query with eager loading

Replace N+1 query pattern with single query using JOIN.
Reduces database calls from O(n) to O(1) for user list page.

Before: ~500ms for 100 users
After: ~50ms for 100 users
```

### 示例 5：文档更新
**变更**：更新了 README
```
docs: add installation instructions for Windows

Add step-by-step guide for Windows users including
prerequisites and common troubleshooting tips.
```

### 示例 6：依赖更新
**变更**：更新了 npm 包
```
chore(deps): update dependencies

- Update react from 18.2.0 to 18.3.0
- Update typescript from 5.0.0 to 5.1.0
- Update testing-library/react to latest
```

### 示例 7：破坏性变更
**变更**：修改了 API 接口
```
feat(api): redesign authentication endpoints

BREAKING CHANGE: Authentication endpoints have been redesigned.
- `/login` is now `/auth/login`
- `/logout` is now `/auth/logout`
- Response format changed from `{token}` to `{accessToken, refreshToken}`

Migration guide: https://docs.example.com/migration-v2
```

## 质量检查清单

生成提交信息后，验证：
- [ ] 类型是否准确（feat/fix/docs 等）
- [ ] 主题行是否清晰简洁（≤50 字符）
- [ ] 是否使用命令式现在时
- [ ] 正文是否解释了"为什么"
- [ ] 是否关联了相关 Issue
- [ ] 多个不相关变更是否建议拆分
- [ ] 破坏性变更是否明确标注

## 输出格式

直接输出可以使用的提交信息，用代码块包裹：

```
type(scope): subject

body

footer
```

然后询问用户："这个提交信息可以吗？需要修改吗？"

## 注意事项

- **遵循项目规范**：如果项目有特定的提交信息规范，优先遵循项目规范
- **保持一致性**：查看历史提交，保持风格一致
- **中英文混用**：如果项目历史提交使用中文，则生成中文提交信息；否则使用英文
- **具体而非泛泛**："add user authentication" 优于 "update code"
- **避免废话**："fix bug" 不如 "fix null pointer exception in user service"
- **尊重用户意愿**：如果用户有特定要求，按用户要求生成
