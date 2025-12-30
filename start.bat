@echo off
chcp 65001 >nul
echo =========================================
echo   文档数据提取工具 - 启动脚本
echo =========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)

echo ✅ 检测到 Python
python --version
echo.

REM 安装依赖
if not exist "backend\__pycache__" (
    echo 📦 首次运行，正在安装依赖...
    cd backend
    pip install -r requirements.txt
    cd ..
    echo.
)

REM 启动后端服务
echo 🚀 正在启动后端服务...
cd backend
start /B python app.py
cd ..

echo ✅ 后端服务已启动
echo 📡 API 地址: http://localhost:5000
echo.

REM 等待后端启动
timeout /t 2 /nobreak >nul

REM 打开前端页面
echo 🌐 正在打开前端页面...
start "" "%CD%\frontend\index.html"

echo.
echo =========================================
echo ✅ 应用已启动！
echo =========================================
echo.
echo 📝 使用说明:
echo   1. 在打开的网页中上传文件
echo   2. 点击'开始提取'按钮
echo   3. 下载生成的 Excel 文件
echo.
echo ⚠️  关闭此窗口将停止服务
echo =========================================
echo.

pause
