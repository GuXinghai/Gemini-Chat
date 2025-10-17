@echo off
:: Gemini Chat 快速启动脚本 (Windows)

title Gemini Chat Launcher

echo.
echo ========================================
echo          Gemini Chat 启动器
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装或不在 PATH 中
    echo 请先安装 Python 3.10+ 并添加到系统路径
    pause
    exit /b 1
)

echo ✅ Python 环境检查通过

:: 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo 📦 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 虚拟环境创建失败
        pause
        exit /b 1
    )
)

:: 激活虚拟环境
echo 🔧 激活虚拟环境...
call venv\Scripts\activate.bat

:: 安装依赖
echo 📥 检查并安装依赖...
pip install -q -e .

:: 检查配置文件
if not exist ".env" (
    echo ⚠️  未找到 .env 配置文件
    echo 请复制 .env.example 为 .env 并配置 GEMINI_API_KEY
    echo.
    set /p create_env="是否自动创建 .env 文件？(y/N): "
    if /i "!create_env!"=="y" (
        copy .env.example .env
        echo ✅ 已创建 .env 文件，请编辑并添加您的 API Key
        notepad .env
    )
    pause
    exit /b 1
)

:: 启动应用
echo 🚀 启动 Gemini Chat...
python app.py

pause
