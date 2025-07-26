# Gemini Chat

Gemini Chat 是基于 **Google Gemini API** 与 **PySide6** 桌面界面框架构建的跨平台 AI 聊天客户端，旨在为用户提供流畅、可扩展且易于定制的本地化应用体验。

---

## 技术核心

* **编程语言**：Python 3.10+
* **AI 模型**：Google Gemini（通过 `google-generativeai` 客户端库）
* **桌面框架**：PySide6（Qt for Python），实现现代化 UI 与跨平台兼容
* **异步交互**：利用 `QThread` 与信号槽机制，确保 API 调用与界面渲染并行，避免卡顿
* **配置管理**：`config.py` 管理全局常量，环境变量 `GEMINI_API_KEY` 用于安全存储 API 密钥
* **架构模式**：分层设计（Domain → Services → UI），高内聚、低耦合，便于后续扩展和维护

---

## 项目框架

```text
Gemini-Chat/
├── README.md              # 项目说明文档
├── main.py                # 应用入口，初始化 App 对象并启动主窗口
├── app.py                 # 启动逻辑：加载服务、注入依赖、创建主窗口
├── config.py              # 全局配置与常量（路径、API 端点等）
├── domain/                # 领域模型与枚举
│   ├── model_type.py      # 模型类型枚举（如 gemini-pro、gemini-1.5）
│   └── user_settings.py   # 持久化用户偏好设置接口
├── services/              # 核心服务层
│   ├── gemini_service.py  # 封装 Google Gemini API 调用逻辑
│   ├── settings_service.py# 本地配置读写，继承或组合 `user_settings.py`
│   └── history_service.py # 聊天记录存储与检索
├── ui/                    # 界面层
│   ├── main_window.py     # 主窗口布局与逻辑
│   └── chat_tab.py        # 聊天标签页组件，消息渲染与用户输入处理
└── resources/             # 资源文件（图标、QSS 样式、SVG 等）
```

---

## 适配平台

* **Windows**：Windows 10/11
* **macOS**：macOS Catalina 及以上
* **Linux**：主流发行版（Ubuntu、Fedora、Arch 等），需安装 Qt5/6 依赖

> **依赖环境**：
>
> * Python 3.10+
> * Qt6 (由 PySide6 安装包自动管理)
> * 网络环境：访问 Google Gemini API 所需的互联网连接

---

## 功能实现

* **多模型支持**：可在 `设置` 中切换不同 Gemini 模型版本（如 `gemini-pro`、`gemini-1.5` 等）
* **本地化界面**：支持中英文界面切换，样式可通过 QSS 自定义
* **历史记录管理**：本地保存聊天记录，支持导出和检索
* **快捷键交互**：`Ctrl+Enter` 发送消息，`Up/Down` 浏览历史输入
* **异步流式渲染**：消息分块渲染，实时展现模型回复进度
* **插件扩展**：封装 Monaco Editor、文件分享、代码高亮等扩展能力（可选）

---

## 安装与运行

1. 克隆代码仓库：

   ```bash
   git clone https://github.com/你的用户名/gemini-chat.git
   cd gemini-chat
   ```
2. 安装依赖：

   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. 配置 API 密钥：

   ```bash
   export GEMINI_API_KEY="YOUR_API_KEY"   # Windows PowerShell: $env:GEMINI_API_KEY="YOUR_API_KEY"
   ```
4. 启动应用：

   ```bash
   python main.py
   ```

---

## 许可证

本项目采用 MIT 许可证，详情请见 [LICENSE](LICENSE)。  欢迎 Fork、Issue 与 Pull Request！
