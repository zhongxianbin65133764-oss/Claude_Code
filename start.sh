#!/bin/bash

echo "========================================="
echo "  文档数据提取工具 - 启动脚本"
echo "========================================="
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3.8 或更高版本"
    exit 1
fi

echo "✅ 检测到 Python: $(python3 --version)"
echo ""

# 检查是否已安装依赖
if [ ! -d "backend/__pycache__" ]; then
    echo "📦 首次运行，正在安装依赖..."
    cd backend
    pip3 install -r requirements.txt
    cd ..
    echo ""
fi

# 启动后端服务
echo "🚀 正在启动后端服务..."
cd backend
python3 app.py &
BACKEND_PID=$!
cd ..

echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"
echo "📡 API 地址: http://localhost:5000"
echo ""

# 等待后端启动
sleep 2

# 打开前端页面
echo "🌐 正在打开前端页面..."
FRONTEND_PATH="$(pwd)/frontend/index.html"

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "$FRONTEND_PATH"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v xdg-open &> /dev/null; then
        xdg-open "$FRONTEND_PATH"
    else
        echo "请手动打开: $FRONTEND_PATH"
    fi
fi

echo ""
echo "========================================="
echo "✅ 应用已启动！"
echo "========================================="
echo ""
echo "📝 使用说明:"
echo "  1. 在打开的网页中上传文件"
echo "  2. 点击'开始提取'按钮"
echo "  3. 下载生成的 Excel 文件"
echo ""
echo "⚠️  按 Ctrl+C 停止服务"
echo "========================================="

# 等待用户中断
wait $BACKEND_PID
