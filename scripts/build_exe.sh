#!/bin/bash

# 退出时如果出错就报错
set -e

# 1. 检查是否安装了 pyinstaller
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller 未安装，正在尝试安装..."
    pip install pyinstaller
fi

# 2. 打包项目
pyinstaller --clean --onefile --noconsole app.py

# 3. 打包结果说明
echo "打包完成，生成的 exe 文件在 dist/ 目录下。"

# 4. 可选：自动打开 dist 文件夹
# explorer dist   # Windows 下可用
