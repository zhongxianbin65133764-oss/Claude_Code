---
name: doc-generator
description: |
  为代码、函数、类或项目生成清晰完整的文档。
  当用户说"生成文档"、"写文档"、"添加注释"、"document this"、
  "add documentation"或需要为代码创建文档时使用。
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
model: claude-sonnet-4-5
---

# 文档生成器

## 目的
自动为代码、API、函数或整个项目生成清晰、完整、有用的文档。

## 支持的文档类型

### 1. 代码注释文档
为函数、类、方法添加注释：
- Python：docstring (Google/NumPy/Sphinx 风格)
- JavaScript/TypeScript：JSDoc
- Java：JavaDoc
- Go：Go doc 注释
- Rust：Rustdoc
- 其他语言的标准文档格式

### 2. API 文档
为 REST API 或 GraphQL API 生成文档：
- OpenAPI/Swagger 规范
- API 端点列表
- 请求/响应示例
- 认证说明

### 3. README 文档
为项目生成或更新 README.md：
- 项目简介
- 安装说明
- 使用示例
- 配置指南
- 贡献指南

### 4. 架构文档
生成系统架构文档：
- 系统概览
- 模块说明
- 数据流图
- 技术栈

## 工作流程

### 第 1 步：理解上下文
根据用户请求，确定需要生成的文档类型：
- 单个函数/类的文档？
- 整个模块的文档？
- API 文档？
- 项目 README？

### 第 2 步：读取和分析代码
```bash
# 读取相关文件
# 理解代码结构、参数、返回值、功能
```

### 第 3 步：生成文档
根据代码语言和类型，生成相应格式的文档。

### 第 4 步：验证和优化
确保文档：
- 准确描述代码功能
- 包含所有重要信息
- 格式正确
- 清晰易懂

## 文档生成规范

### Python Docstring（Google 风格）

```python
def calculate_total(items: list[dict], tax_rate: float = 0.1) -> float:
    """Calculate the total price including tax for a list of items.

    This function sums up the prices of all items and applies the specified
    tax rate to calculate the final total.

    Args:
        items: A list of dictionaries, each containing 'name' and 'price' keys.
            Example: [{'name': 'Apple', 'price': 1.5}]
        tax_rate: The tax rate to apply as a decimal. Defaults to 0.1 (10%).

    Returns:
        The total price including tax, rounded to 2 decimal places.

    Raises:
        ValueError: If any item is missing 'price' key or price is negative.
        TypeError: If items is not a list or tax_rate is not a number.

    Example:
        >>> items = [{'name': 'Apple', 'price': 1.5}, {'name': 'Orange', 'price': 2.0}]
        >>> calculate_total(items, tax_rate=0.08)
        3.78

    Note:
        Prices are assumed to be in the same currency.
    """
    if not isinstance(items, list):
        raise TypeError("items must be a list")

    subtotal = sum(item['price'] for item in items)
    total = subtotal * (1 + tax_rate)
    return round(total, 2)
```

### JavaScript/TypeScript JSDoc

```javascript
/**
 * Calculate the total price including tax for a list of items.
 *
 * This function sums up the prices of all items and applies the specified
 * tax rate to calculate the final total.
 *
 * @param {Array<{name: string, price: number}>} items - Array of items with name and price
 * @param {number} [taxRate=0.1] - Tax rate as decimal (default: 0.1 for 10%)
 * @returns {number} Total price including tax, rounded to 2 decimal places
 * @throws {TypeError} If items is not an array or taxRate is not a number
 * @throws {Error} If any item is missing price or price is negative
 *
 * @example
 * const items = [{name: 'Apple', price: 1.5}, {name: 'Orange', price: 2.0}];
 * const total = calculateTotal(items, 0.08);
 * console.log(total); // 3.78
 */
function calculateTotal(items, taxRate = 0.1) {
    if (!Array.isArray(items)) {
        throw new TypeError('items must be an array');
    }

    const subtotal = items.reduce((sum, item) => sum + item.price, 0);
    const total = subtotal * (1 + taxRate);
    return Math.round(total * 100) / 100;
}
```

### Go Doc 注释

```go
// CalculateTotal calculates the total price including tax for a list of items.
//
// This function sums up the prices of all items and applies the specified
// tax rate to calculate the final total.
//
// Parameters:
//   - items: A slice of Item structs containing Name and Price
//   - taxRate: The tax rate to apply as a decimal (e.g., 0.1 for 10%)
//
// Returns:
//   - float64: The total price including tax, rounded to 2 decimal places
//   - error: An error if any item has a negative price
//
// Example:
//
//	items := []Item{
//	    {Name: "Apple", Price: 1.5},
//	    {Name: "Orange", Price: 2.0},
//	}
//	total, err := CalculateTotal(items, 0.08)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	fmt.Printf("Total: %.2f\n", total) // Total: 3.78
func CalculateTotal(items []Item, taxRate float64) (float64, error) {
    var subtotal float64
    for _, item := range items {
        if item.Price < 0 {
            return 0, fmt.Errorf("negative price for item: %s", item.Name)
        }
        subtotal += item.Price
    }
    total := subtotal * (1 + taxRate)
    return math.Round(total*100) / 100, nil
}
```

## README 模板

生成 README.md 时，包含以下部分：

```markdown
# 项目名称

> 简短的项目描述（一句话说明项目是什么）

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](package.json)

## 目录

- [特性](#特性)
- [快速开始](#快速开始)
- [安装](#安装)
- [使用](#使用)
- [配置](#配置)
- [API 文档](#api-文档)
- [开发](#开发)
- [测试](#测试)
- [贡献](#贡献)
- [许可证](#许可证)

## 特性

- ✨ 特性 1：描述
- 🚀 特性 2：描述
- 🎯 特性 3：描述

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/username/project.git

# 进入目录
cd project

# 安装依赖
npm install

# 运行项目
npm start
```

## 安装

### 前置要求

- Node.js >= 16.0.0
- npm >= 8.0.0

### 从源码安装

```bash
npm install
npm run build
```

### 使用包管理器

```bash
npm install package-name
```

## 使用

### 基本用法

```javascript
import { Calculator } from 'package-name';

const calc = new Calculator();
const result = calc.add(2, 3);
console.log(result); // 5
```

### 高级用法

```javascript
// 更复杂的示例
```

## 配置

配置文件：`.config.json`

```json
{
  "option1": "value1",
  "option2": "value2"
}
```

## API 文档

### `functionName(param1, param2)`

描述函数功能

**参数：**
- `param1` (类型): 描述
- `param2` (类型): 描述

**返回值：**
- 类型: 描述

**示例：**
```javascript
const result = functionName('arg1', 'arg2');
```

## 开发

### 设置开发环境

```bash
npm install
npm run dev
```

### 项目结构

```
project/
├── src/           # 源代码
├── tests/         # 测试文件
├── docs/          # 文档
└── package.json
```

## 测试

```bash
# 运行所有测试
npm test

# 运行特定测试
npm test -- --grep "pattern"

# 生成覆盖率报告
npm run coverage
```

## 贡献

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)。

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 作者

- 作者名 - [@username](https://github.com/username)

## 致谢

- 感谢的人或项目
```

## API 文档模板

为 REST API 生成文档：

```markdown
# API 文档

## 基础信息

- **Base URL**: `https://api.example.com/v1`
- **认证方式**: Bearer Token
- **数据格式**: JSON

## 认证

所有 API 请求需要在 Header 中包含认证令牌：

```
Authorization: Bearer YOUR_TOKEN_HERE
```

## 端点列表

### 获取用户列表

```http
GET /users
```

**请求参数：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| page | integer | 否 | 页码（默认：1） |
| limit | integer | 否 | 每页数量（默认：10） |

**响应示例：**

```json
{
  "data": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 10,
    "total": 100
  }
}
```

**状态码：**
- `200 OK`: 请求成功
- `401 Unauthorized`: 未认证
- `500 Internal Server Error`: 服务器错误

### 创建用户

```http
POST /users
```

**请求体：**

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "secure_password"
}
```

**响应示例：**

```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2024-01-08T10:00:00Z"
}
```

**状态码：**
- `201 Created`: 创建成功
- `400 Bad Request`: 请求参数错误
- `409 Conflict`: 用户已存在
```

## 文档质量标准

生成的文档应该：

### 完整性
- [ ] 包含所有必要信息
- [ ] 参数、返回值、异常都有说明
- [ ] 提供实际可运行的示例

### 准确性
- [ ] 与代码实际行为一致
- [ ] 类型标注正确
- [ ] 示例代码经过验证

### 清晰性
- [ ] 使用简单明了的语言
- [ ] 避免技术黑话（或加以解释）
- [ ] 逻辑结构清晰

### 有用性
- [ ] 解释"为什么"而不只是"是什么"
- [ ] 提供使用场景和最佳实践
- [ ] 包含常见问题和注意事项

## 输出格式

根据请求类型输出：

1. **代码注释**：直接输出可以插入的注释代码
2. **README**：完整的 Markdown 文档
3. **API 文档**：格式化的 API 说明

然后询问用户："文档生成完成，需要调整吗？"

## 注意事项

- **遵循项目规范**：检查项目是否有文档风格指南
- **保持一致性**：与现有文档风格保持一致
- **实用性优先**：文档应该帮助读者理解和使用代码
- **定期更新**：提醒用户在代码变更时更新文档
- **适度详细**：既不过于简略也不过于啰嗦
- **考虑受众**：根据读者（新手/专家）调整详细程度
