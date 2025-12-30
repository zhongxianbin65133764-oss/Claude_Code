# 快速使用指南 🚀

## 一键启动（推荐）

### Linux/Mac 用户
```bash
chmod +x start.sh
./start.sh
```

### Windows 用户
双击运行 `start.bat` 文件

---

## 手动启动

### 1. 安装依赖（首次使用）
```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端
```bash
cd backend
python app.py
```
**保持此窗口打开！** 看到 "Running on http://0.0.0.0:5000" 表示成功

### 3. 打开前端
直接双击打开 `frontend/index.html` 文件

---

## 使用步骤

### 📤 上传文件
1. 点击"选择文件"或直接拖拽文件到上传区域
2. 支持的格式：PDF、Word (.doc/.docx)、Excel (.xls/.xlsx)
3. 可以一次选择多个文件

### ⚙️ 开始提取
1. 点击"开始提取"按钮
2. 等待进度条完成（通常几秒到几十秒）

### 💾 下载结果
1. 提取完成后，点击"下载Excel文件"
2. Excel 文件包含 4 个工作表：
   - **文档摘要**：文档概览
   - **关键信息**：合同编号、甲乙方、金额、日期等
   - **表格数据**：所有表格内容
   - **关键条款**：重要条款列表

### 📋 查看历史
- 页面底部显示所有历史文件
- 可以随时重新下载之前的结果

---

## 示例操作

```
1. 启动服务
   cd backend && python app.py

2. 打开浏览器
   双击 frontend/index.html

3. 上传文件
   拖拽你的合同文件到页面

4. 点击"开始提取"

5. 下载生成的 Excel 文件
```

---

## 验证服务是否正常

在浏览器中访问：http://localhost:5000/api/health

如果看到 `{"status":"ok","message":"服务运行正常"}` 表示后端正常运行

---

## 常见问题

**Q: 上传文件没反应？**
- 检查后端是否在运行（终端有输出）
- 按 F12 打开浏览器控制台，查看错误

**Q: 提取的数据不完整？**
- 确保文档格式规范
- PDF 建议使用文本型 PDF（非扫描版）
- 可以在 `backend/extractors/data_extractor.py` 中自定义提取规则

**Q: 无法安装依赖？**
```bash
# 使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

pip install -r backend/requirements.txt
```

---

## 停止服务

在运行 `python app.py` 的终端按 `Ctrl + C`
