# Gemini Chat

> 基于 Google Gemini API 与 PySide6 的跨平台 AI 聊天客户端

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 特性

### 🤖 AI 对话
- **多模型支持**: Gemini 2.0 Flash、Gemini 1.5 Pro 等
- **流式回复**: 实时显示 AI 回复内容
- **连续对话**: 支持上下文记忆的多轮对话
- **会话管理**: 临时会话和持久化会话

### 📁 多模态文件支持
- **文档**: PDF, TXT, MD, HTML, XML
- **图片**: PNG, JPEG, WebP, HEIC, GIF
- **视频**: MP4, MPEG, MOV, AVI, FLV  
- **音频**: 多种音频格式
- **URL采集**: 自动获取网页内容
- **拖拽上传**: 便捷的文件上传体验

### 🎨 现代化界面
- **响应式设计**: 可收缩侧边栏，多标签页
- **主题系统**: 深色/浅色模式，自定义主题
- **主题编辑器**: 可视化主题创建和编辑
- **欢迎页面**: 快速访问最近会话

### 💾 数据管理
- **智能存储**: 会话历史自动保存
- **文件夹组织**: 会话分类管理
- **配置管理**: 灵活的设置系统
- **自动清理**: 定期清理临时文件

## 🛠️ 技术栈

- **界面框架**: PySide6 (Qt 6)
- **AI 引擎**: Google Gemini API
- **配置管理**: TOML
- **异步支持**: asyncio, aiofiles
- **网络请求**: httpx
- **架构模式**: 分层架构 + 领域驱动设计

## 📦 安装

### 环境要求
- Python 3.10+
- Google Gemini API Key

### 快速开始

1. **克隆项目**
```bash
git clone https://github.com/yourusername/gemini-chat.git
cd gemini-chat
```

2. **安装依赖**
```bash
pip install -e .
```

3. **配置 API Key**
```bash
# 创建 .env 文件
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

4. **运行应用**
```bash
python app.py
```

## 🚀 使用指南

### 基本使用
1. 启动应用后，在欢迎页面选择"新建对话"
2. 选择 AI 模型（推荐 Gemini 2.0 Flash）
3. 输入消息开始对话
4. 支持拖拽文件到对话框进行多模态交互

### 高级功能
- **主题定制**: 设置 → 外观 → 主题管理
- **文件上传**: 支持批量上传和 URL 采集
- **会话管理**: 左侧边栏管理所有对话历史
- **设置调整**: 模型参数、界面偏好等

## 🏗️ 项目结构

```
gemini-chat/
├── app.py                 # 应用程序入口
├── pyproject.toml         # 项目配置
├── geminichat/            # 核心包
│   ├── config/            # 配置管理
│   ├── domain/            # 领域模型
│   └── infrastructure/    # 基础设施层
├── services/              # 业务服务层
│   ├── gemini_service_enhanced.py
│   ├── file_upload_service.py
│   ├── history_service.py
│   └── settings_service.py
├── ui/                    # 用户界面层
│   ├── main_window_enhanced.py
│   ├── theming/           # 主题系统
│   └── dialogs/           # 对话框
└── assets/                # 资源文件
```

## 🔧 开发

### 安装开发依赖
```bash
pip install -e ".[dev]"
```

### 代码格式化
```bash
black .
flake8 .
```

### 运行测试
```bash
pytest
```

### 构建可执行文件
```bash
pip install -e ".[build]"
python scripts/build_exe.sh
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Google Gemini API](https://ai.google.dev/)
- [PySide6](https://wiki.qt.io/Qt_for_Python)
- [Qt Framework](https://www.qt.io/)

## 📞 支持

如遇问题，请：
1. 查看 [Issues](https://github.com/yourusername/gemini-chat/issues)
2. 提交新的 Issue
3. 联系开发团队

---

⭐ 如果这个项目对您有帮助，请给我们一个星星！
