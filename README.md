# 文档数据提取工具 📄

一个智能的文档数据提取工具，可以自动从 PDF、Word 和 Excel 文件中提取核心数据和条款，并整理输出为结构化的 Excel 文件。

## 功能特点 ✨

- 📄 **多格式支持**: 支持 PDF、Word (.doc/.docx)、Excel (.xls/.xlsx) 格式
- 🔍 **智能提取**: 自动识别和提取关键信息（合同编号、甲乙方、金额、日期等）
- 📊 **表格解析**: 自动提取文档中的所有表格数据
- 📝 **条款识别**: 智能提取重要条款和章节
- 💾 **结构化输出**: 将提取的数据整理为格式化的 Excel 文件
- 🎨 **友好界面**: 简洁美观的 Web 界面，支持拖拽上传
- 📦 **批量处理**: 支持同时上传多个文件批量处理
- 📜 **历史记录**: 自动保存处理历史，方便随时下载

## 项目结构 📁

```
Claude_Code/
├── backend/                # 后端代码
│   ├── app.py             # Flask 主应用
│   ├── requirements.txt   # Python 依赖
│   ├── parsers/           # 文档解析器
│   │   ├── pdf_parser.py      # PDF 解析
│   │   ├── word_parser.py     # Word 解析
│   │   └── excel_parser.py    # Excel 解析
│   ├── extractors/        # 数据提取器
│   │   └── data_extractor.py  # 核心数据提取逻辑
│   └── output/            # 输出处理
│       └── excel_writer.py    # Excel 生成器
├── frontend/              # 前端代码
│   ├── index.html         # 主页面
│   ├── style.css          # 样式文件
│   └── script.js          # 交互逻辑
├── uploads/               # 上传文件临时目录
├── output_files/          # 生成的 Excel 文件存储目录
├── start.sh               # Linux/Mac 启动脚本
├── start.bat              # Windows 启动脚本
└── README.md              # 项目说明
```

## 快速开始 🚀

### 环境要求

- Python 3.8 或更高版本
- pip (Python 包管理器)
- 现代浏览器（Chrome、Firefox、Safari、Edge 等）

### 安装步骤

1. **克隆或下载项目**
   ```bash
   git clone <repository-url>
   cd Claude_Code
   ```

2. **安装 Python 依赖**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **启动应用**

   **方式一：使用启动脚本（推荐）**

   Linux/Mac:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

   Windows:
   ```bash
   start.bat
   ```

   **方式二：手动启动**
   ```bash
   cd backend
   python app.py
   ```

4. **访问应用**

   在浏览器中打开：
   - 主应用: `frontend/index.html` (直接双击打开)
   - 或访问: `http://localhost:5000` (如果配置了静态文件服务)

## 使用方法 📖

### 基本操作

1. **上传文件**
   - 点击"选择文件"按钮或直接拖拽文件到上传区域
   - 可以同时选择多个文件

2. **开始提取**
   - 点击"开始提取"按钮
   - 等待处理完成（会显示进度条）

3. **下载结果**
   - 处理完成后，点击"下载Excel文件"按钮
   - Excel 文件包含多个工作表：
     - **文档摘要**: 所有处理文档的概览
     - **关键信息**: 提取的关键字段（合同编号、甲乙方、金额等）
     - **表格数据**: 所有文档中的表格内容
     - **关键条款**: 识别的重要条款

4. **查看历史**
   - 页面底部可以查看所有历史生成的文件
   - 点击"下载"按钮可以重新下载之前的结果

### 高级配置

#### 自定义提取规则

可以在 `backend/extractors/data_extractor.py` 中修改或添加提取模式：

```python
self.patterns = {
    '字段名称': [r'正则表达式模式1', r'正则表达式模式2'],
    # 添加更多字段...
}
```

#### 调整 Excel 输出格式

可以在 `backend/output/excel_writer.py` 中修改样式和格式。

## API 接口 🔌

### 健康检查
```
GET /api/health
```

### 上传和处理文件
```
POST /api/upload
Content-Type: multipart/form-data
Body: files[] (多个文件)
```

### 下载生成的文件
```
GET /api/download/<filename>
```

### 获取历史文件列表
```
GET /api/files
```

## 技术栈 🛠

### 后端
- **Flask**: Web 框架
- **python-docx**: Word 文档解析
- **pdfplumber**: PDF 解析
- **openpyxl**: Excel 读写
- **Flask-CORS**: 跨域支持

### 前端
- HTML5
- CSS3
- 原生 JavaScript (ES6+)

## 常见问题 ❓

### 1. 上传文件后没有响应？
- 检查后端服务是否正常运行
- 查看浏览器控制台是否有错误信息
- 确认文件大小不超过 16MB

### 2. 提取的数据不准确？
- 检查文档格式是否规范
- 可以自定义提取规则来适应特定格式
- PDF 文件建议使用文本型 PDF（非扫描版）

### 3. 无法安装依赖？
- 确保 Python 版本 >= 3.8
- 尝试使用虚拟环境：
  ```bash
  python -m venv venv
  source venv/bin/activate  # Linux/Mac
  venv\Scripts\activate     # Windows
  pip install -r backend/requirements.txt
  ```

### 4. Excel 文件样式问题？
- 可以在 `excel_writer.py` 中调整样式
- 确保 openpyxl 版本正确

## 贡献指南 🤝

欢迎提交 Issue 和 Pull Request！

## 许可证 📜

MIT License

## 联系方式 📧

如有问题或建议，请提交 Issue。

---

**享受使用！** 🎉
