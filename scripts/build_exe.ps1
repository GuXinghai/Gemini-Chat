# PowerShell 构建脚本
# 用于在 Windows 环境下打包 Gemini Chat 应用

param(
    [switch]$Clean,
    [switch]$Debug
)

Write-Host "🔨 开始构建 Gemini Chat..." -ForegroundColor Green

# 1. 检查 Python 环境
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python 未安装或未添加到 PATH"
    exit 1
}

# 2. 检查 PyInstaller
try {
    pyinstaller --version | Out-Null
} catch {
    Write-Host "📦 安装 PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

# 3. 清理之前的构建
if ($Clean) {
    Write-Host "🧹 清理之前的构建..." -ForegroundColor Yellow
    Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "*.spec" -Force -ErrorAction SilentlyContinue
}

# 4. 构建参数
$args = @(
    "--clean",
    "--onefile",
    "--windowed",  # 不显示控制台
    "--icon=gemini_sparkle_aurora.ico",
    "--name=GeminiChat",
    "--add-data=assets;assets",
    "--add-data=ui/resources;ui/resources",
    "app.py"
)

if ($Debug) {
    $args = $args -replace "--windowed", "--console"
}

# 5. 开始打包
Write-Host "🏗️ 正在打包应用..." -ForegroundColor Blue
pyinstaller @args

# 6. 检查结果
if (Test-Path "dist/GeminiChat.exe") {
    Write-Host "✅ 构建成功！" -ForegroundColor Green
    Write-Host "📁 可执行文件位置: dist/GeminiChat.exe" -ForegroundColor Cyan
    
    # 显示文件大小
    $size = (Get-Item "dist/GeminiChat.exe").Length / 1MB
    Write-Host "📊 文件大小: $([math]::Round($size, 2)) MB" -ForegroundColor Cyan
    
    # 询问是否打开文件夹
    $openFolder = Read-Host "是否打开输出文件夹？(y/N)"
    if ($openFolder -eq "y" -or $openFolder -eq "Y") {
        explorer.exe "dist"
    }
} else {
    Write-Error "构建失败！"
    exit 1
}
