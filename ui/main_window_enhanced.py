# ui/main_window_enhanced.py
# 简化版增强主窗口，包含可收缩侧边栏、标签页、设置选项栏、主题选项栏等功能

import sys
import asyncio
from pathlib import Path
from uuid import uuid4
from typing import List, Dict, Optional, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QListWidget, QListWidgetItem, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QLineEdit, QLabel, QComboBox,
    QToolBar, QMenuBar, QMenu, QFrame, QScrollArea,
    QCheckBox, QSpinBox, QSlider, QGroupBox, QRadioButton,
    QButtonGroup, QTextEdit, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QIcon, QFont, QPalette, QColor, QAction

from .ui_config import (
    Conversation, SimpleHistoryService, 
    SimpleSettingsService, SimpleGeminiService, HISTORY_DIR, BASE_DIR
)

# 导入主题系统
try:
    from .theming import ThemeManager as NewThemeManager, ThemeMode, RegionNames
    from .theming.theme_switcher import ThemeSwitcherWidget, CompactThemeSwitcher
    THEME_SYSTEM_AVAILABLE = True
    print("✅ 主题系统模块可用")
except ImportError as e:
    print(f"❌ 主题系统不可用: {e}")
    THEME_SYSTEM_AVAILABLE = False
    NewThemeManager = None
    ThemeMode = None
    RegionNames = None
    ThemeSwitcherWidget = None
    CompactThemeSwitcher = None

# 尝试导入增强聊天标签页
try:
    from ui.chat_tab import EnhancedChatTab
    from ui.chat_history_manager import ChatHistoryManager
    ENHANCED_CHAT_AVAILABLE = True
    print("增强聊天标签页可用")
except ImportError as e:
    print(f"增强聊天标签页不可用: {e}")
    ENHANCED_CHAT_AVAILABLE = False
    EnhancedChatTab = None
    ChatHistoryManager = None

# 字体配置工具函数
def get_safe_font(size=10, bold=False):
    """获取安全的字体配置，优先使用系统字体"""
    import platform
    
    # 根据操作系统选择合适的字体
    if platform.system() == "Windows":
        # Windows 优先字体顺序
        font_families = ["Microsoft YaHei", "SimHei", "Arial", "Segoe UI"]
    elif platform.system() == "Darwin":  # macOS
        font_families = ["PingFang SC", "Arial", "Helvetica"]
    else:  # Linux
        font_families = ["Noto Sans CJK SC", "DejaVu Sans", "Arial"]
    
    # 尝试创建字体，找到第一个可用的
    for family in font_families:
        font = QFont(family, size)
        if bold:
            font.setBold(True)
        
        # 检查字体是否可用
        if font.family() == family or QFont(family).family() == family:
            return font
    
    # 如果所有指定字体都不可用，使用默认字体
    font = QFont()
    font.setPointSize(size)
    if bold:
        font.setBold(True)
    return font
from geminichat.domain.user_settings import UserSettings
from geminichat.domain.model_type import ModelType


class AsyncWorkerWithFiles(QThread):
    """支持文件的异步工作线程"""
    
    stream_chunk = Signal(str)
    response_received = Signal(str)  
    error_occurred = Signal(str)
    
    def __init__(self, service, user_message: str, conversation, file_references=None, streaming: bool = True):
        super().__init__()
        self.service = service
        self.user_message = user_message
        self.conversation = conversation
        self.file_references = file_references or []
        self.streaming = streaming
        
    def run(self):
        """执行任务"""
        try:
            if self.streaming:
                asyncio.run(self._stream_message_with_files())
            else:
                asyncio.run(self._send_message_with_files())
        except Exception as e:
            print(f"AsyncWorkerWithFiles异常: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            self.error_occurred.emit(str(e))
        finally:
            print("AsyncWorkerWithFiles完成")
                    
    async def _send_message_with_files(self):
        """发送非流式消息（带文件）"""
        try:
            print(f"开始发送非流式消息（带文件）: {self.user_message}")
            
            # 准备内容 - 支持文件
            content_parts = []
            
            # 添加文本内容
            if self.user_message:
                content_parts.append(self.user_message)
            
            # 添加文件引用
            for file_ref in self.file_references:
                # 添加文件对象
                content_parts.append(file_ref)
            
            # 发送消息 - 修复边界条件
            if not content_parts:
                content_parts.append("(空消息)")  # 防止空列表导致IndexError
                
            assistant_message, updated_conversation = await self.service.send_message_async(
                content=content_parts if len(content_parts) > 1 else content_parts[0],
                conversation=self.conversation,
                streaming=False
            )
            print(f"收到助手回复: {assistant_message.content[:100]}...")
            self.response_received.emit(assistant_message.content)
        except Exception as e:
            print(f"_send_message_with_files异常: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            self.error_occurred.emit(str(e))
            
    async def _stream_message_with_files(self):
        """发送流式消息（带文件）"""
        try:
            print(f"开始发送流式消息（带文件）: {self.user_message}")
            
            # 准备内容 - 支持文件
            content_parts = []
            
            # 添加文本内容
            if self.user_message:
                content_parts.append(self.user_message)
            
            # 添加文件引用
            for file_ref in self.file_references:
                # 添加文件对象
                content_parts.append(file_ref)
            
            # 修复边界条件
            if not content_parts:
                content_parts.append("(空消息)")  # 防止空列表导致IndexError
            
            chunk_count = 0
            async for chunk, updated_conversation in self.service.send_message_stream_async(
                content=content_parts if len(content_parts) > 1 else content_parts[0],
                conversation=self.conversation
            ):
                chunk_count += 1
                print(f"收到流式块 {chunk_count}: {chunk[:50]}...")
                self.stream_chunk.emit(chunk)
            print(f"流式消息完成，共收到 {chunk_count} 个块")
        except Exception as e:
            print(f"_stream_message_with_files异常: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            self.error_occurred.emit(str(e))


class AsyncWorker(QThread):
    """异步工作线程，用于处理Gemini API调用"""
    
    # 定义信号
    response_received = Signal(str)  # 收到完整回复
    stream_chunk = Signal(str)      # 流式回复块
    error_occurred = Signal(str)    # 错误信息
    
    def __init__(self, service, user_message: str, conversation, model_name: Optional[str] = None, streaming: bool = False):
        super().__init__()
        self.service = service
        self.user_message = user_message
        self.conversation = conversation
        self.model_name = model_name
        self.streaming = streaming
        
    def run(self):
        """在后台线程中运行异步任务"""
        loop = None
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 根据是否流式调用不同的方法
            if self.streaming:
                loop.run_until_complete(self._stream_message())
            else:
                loop.run_until_complete(self._send_message())
                
        except Exception as e:
            print(f"AsyncWorker异常: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            self.error_occurred.emit(f"API调用失败: {str(e)}")
        finally:
            if loop:
                try:
                    loop.close()
                except:
                    pass
            print("AsyncWorker完成")
            
    async def _send_message(self):
        """发送非流式消息"""
        try:
            print(f"开始发送非流式消息: {self.user_message}")
            assistant_message, updated_conversation = await self.service.send_message_async(
                content=self.user_message,
                conversation=self.conversation,
                model_name=self.model_name,
                streaming=False
            )
            print(f"收到助手回复: {assistant_message.content[:100]}...")
            self.response_received.emit(assistant_message.content)
        except Exception as e:
            print(f"_send_message异常: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            self.error_occurred.emit(str(e))
            
    async def _stream_message(self):
        """发送流式消息"""
        try:
            print(f"开始发送流式消息: {self.user_message}")
            chunk_count = 0
            async for chunk, updated_conversation in self.service.send_message_stream_async(
                content=self.user_message,
                conversation=self.conversation,
                model_name=self.model_name
            ):
                chunk_count += 1
                print(f"收到流式块 {chunk_count}: {chunk[:50]}...")
                self.stream_chunk.emit(chunk)
            print(f"流式消息完成，共收到 {chunk_count} 个块")
        except Exception as e:
            print(f"_stream_message异常: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            self.error_occurred.emit(str(e))


class SimpleChatTab(QWidget):
    """简单的聊天标签页实现 - 支持真实API调用"""
    def __init__(self, service, history_service, conversation, settings_service=None, file_upload_service=None):
        super().__init__()
        self.service = service
        self.history_service = history_service
        self.conversation = conversation
        self.settings_service = settings_service
        self.file_upload_service = file_upload_service
        self.current_worker = None  # 当前异步工作线程
        
        # 获取设置 - 始终使用真正的UserSettings类
        self.settings = UserSettings.load()
        
        layout = QVBoxLayout(self)
        
        # 聊天显示区域
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        # 设置为富文本模式以支持HTML
        self.chat_display.setHtml(f"""
        <div style='text-align: center; color: #666; margin: 20px;'>
            <h3>欢迎使用 {conversation.title}！</h3>
            <p>开始您的对话吧</p>
        </div>
        """)
        layout.addWidget(self.chat_display)
        
        # 输入区域 - 使用支持文件上传的聊天输入组件
        try:
            from ui.chat_input import EnhancedChatInput
            self.chat_input = EnhancedChatInput(
                api_key=getattr(service, 'api_key', None) if service else None,
                parent=self
            )
            self.chat_input.send_message.connect(self.send_message_with_files)
            layout.addWidget(self.chat_input)
        except ImportError as e:
            print(f"使用基础输入组件: {e}")
            # 回退到基础输入
            input_layout = QHBoxLayout()
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText("在此输入您的消息...")
            
            # 发送按钮和选项
            self.send_btn = QPushButton("发送")
            self.stream_checkbox = QCheckBox("流式回复")
            self.stream_checkbox.setChecked(True)  # 默认启用流式回复
            
            input_layout.addWidget(self.input_field)
            input_layout.addWidget(self.stream_checkbox)
            input_layout.addWidget(self.send_btn)
            layout.addLayout(input_layout)
            
            # 连接信号
            self.send_btn.clicked.connect(self.send_message)
            self.input_field.returnPressed.connect(self.send_message)
    
    def send_message_with_files(self, text: str, file_references: list):
        """发送带文件的消息"""
        if not text and not file_references:
            return
            
        # 禁用输入
        if hasattr(self, 'chat_input'):
            self.chat_input.setEnabled(False)
        else:
            self.input_field.setEnabled(False)
            self.send_btn.setEnabled(False)
            self.send_btn.setText("发送中...")
        
        # 准备消息内容
        message_content = text
        
        # 如果有文件，添加文件信息到显示
        if file_references:
            file_info = []
            for file_ref in file_references:
                # 添加文件对象描述
                file_info.append(f"📎 {getattr(file_ref, 'display_name', 'File')}")
            
            if file_info:
                display_text = text + "\n\n" + "\n".join(file_info) if text else "\n".join(file_info)
            else:
                display_text = text
        else:
            display_text = text
        
        # 添加用户消息到显示区域
        self.add_message_to_display("用户", display_text)
        
        # 创建异步工作线程 - 传递文件引用，使用用户设置决定是否流式
        streaming = self.settings.enable_streaming
        
        # 添加延迟以确保服务初始化完成
        QTimer.singleShot(100, lambda: self._start_async_worker(message_content, file_references, streaming))
    
    def _start_async_worker(self, message_content: str, file_references: list, streaming: bool):
        """延迟启动异步工作线程"""
        self.current_worker = AsyncWorkerWithFiles(
            service=self.service,
            user_message=message_content,
            conversation=self.conversation,
            file_references=file_references,
            streaming=bool(streaming)
        )
        
        # 连接信号
        if streaming:
            self.current_worker.stream_chunk.connect(self.on_stream_chunk)
            self.assistant_response = ""  # 用于累积流式回复
        else:
            self.current_worker.response_received.connect(self.on_response_received)
            
        self.current_worker.error_occurred.connect(self.on_error_occurred)
        self.current_worker.finished.connect(self.on_request_finished)
        
        # 启动线程
        self.current_worker.start()
        
    def send_message(self):
        """发送消息到Gemini API（基础版本，用于回退）"""
        if hasattr(self, 'input_field'):
            text = self.input_field.text().strip()
            if not text:
                return
                
            # 禁用输入
            self.input_field.setEnabled(False)
            self.send_btn.setEnabled(False)
            self.send_btn.setText("发送中...")
            
            # 添加用户消息到显示区域
            self.add_message_to_display("用户", text)
            
            # 清空输入框
            self.input_field.clear()
            
            # 创建异步工作线程 - 使用用户设置决定是否流式
            streaming = self.settings.enable_streaming
            
            # 添加延迟以确保服务初始化完成
            QTimer.singleShot(100, lambda: self._start_basic_async_worker(text, streaming))
    
    def _start_basic_async_worker(self, text: str, streaming: bool):
        """延迟启动基础异步工作线程"""
        self.current_worker = AsyncWorker(
            service=self.service,
            user_message=text,
            conversation=self.conversation,
            streaming=streaming
        )
        
        # 连接信号
        if streaming:
            self.current_worker.stream_chunk.connect(self.on_stream_chunk)
            self.assistant_response = ""  # 用于累积流式回复
        else:
            self.current_worker.response_received.connect(self.on_response_received)
            
        self.current_worker.error_occurred.connect(self.on_error_occurred)
        self.current_worker.finished.connect(self.on_request_finished)
        
        # 启动线程
        self.current_worker.start()
        
    def add_message_to_display(self, role: str, content: str):
        """添加消息到显示区域 - 使用HTML格式优化显示"""
        print(f"添加消息到显示区域 - 角色: {role}, 内容: {content[:100]}...")
        
        current_html = self.chat_display.toHtml()
        
        # 根据角色确定显示名称和样式
        if role.lower() in ["user", "用户"]:
            display_name = self.settings.user_name
            # 用户消息显示在右边，蓝色背景
            message_html = f"""
            <div style='margin: 10px 0; text-align: right;'>
                <div style='display: inline-block; max-width: 70%; background-color: #e3f2fd; padding: 10px; border-radius: 15px 15px 5px 15px; margin-left: 30%;'>
                    <div style='font-weight: bold; color: #1976d2; margin-bottom: 5px;'>{display_name}</div>
                    <div style='color: #333;'>{content}</div>
                </div>
            </div>
            """
        elif role.lower() in ["ai", "assistant", "gemini"]:
            # 获取当前模型名称
            model_name = self.settings.preferred_model.value if hasattr(self.settings, 'preferred_model') else "AI"
            # AI消息显示在左边，灰色背景
            message_html = f"""
            <div style='margin: 10px 0; text-align: left;'>
                <div style='display: inline-block; max-width: 70%; background-color: #f5f5f5; padding: 10px; border-radius: 15px 15px 15px 5px; margin-right: 30%;'>
                    <div style='font-weight: bold; color: #666; margin-bottom: 5px;'>{model_name}</div>
                    <div style='color: #333;'>{content}</div>
                </div>
            </div>
            """
        else:
            # 系统消息等其他消息，居中显示
            message_html = f"""
            <div style='margin: 10px 0; text-align: center;'>
                <div style='display: inline-block; background-color: #fff3e0; padding: 8px 12px; border-radius: 10px; color: #666;'>
                    {role}: {content}
                </div>
            </div>
            """
        
        print(f"生成的HTML消息片段长度: {len(message_html)}")
        
        # 插入消息到body标签内
        if '</body>' in current_html:
            new_html = current_html.replace('</body>', message_html + '</body>')
        else:
            new_html = current_html + message_html
            
        print(f"设置新的HTML内容，总长度: {len(new_html)}")
        self.chat_display.setHtml(new_html)
        
        # 滚动到底部
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        print("消息已添加并滚动到底部")
        
    def on_stream_chunk(self, chunk: str):
        """处理流式回复块 - 简化版本"""
        print(f"UI收到流式块: {chunk[:50]}...")
        
        if not hasattr(self, 'assistant_response'):
            self.assistant_response = ""
            
        self.assistant_response += chunk
        print(f"累积响应长度: {len(self.assistant_response)}")
        
        # 简单方法：每次都重新显示完整的助手回复
        # 首先移除之前的流式消息（如果存在）
        if hasattr(self, '_stream_message_added'):
            # 这里我们可以选择更新现有消息或添加新消息
            pass
        else:
            # 第一次收到流式内容，标记已添加消息
            self._stream_message_added = True
        
        # 每次都显示完整的累积内容
        self.add_message_to_display("AI", self.assistant_response)
        
        print("流式内容已更新")
        
    def on_response_received(self, response: str):
        """处理完整回复"""
        print(f"UI收到完整回复: {response[:100]}...")
        self.add_message_to_display("AI", response)
        
    def on_error_occurred(self, error: str):
        """处理错误"""
        print(f"UI收到错误: {error}")
        self.add_message_to_display("系统", f"错误: {error}")
        
    def on_request_finished(self):
        """请求完成，重新启用输入"""
        print("请求完成，清理流式状态")
        
        # 清理流式状态
        if hasattr(self, 'assistant_response'):
            delattr(self, 'assistant_response')
        if hasattr(self, '_stream_message_added'):
            delattr(self, '_stream_message_added')
            
        # 重新启用输入组件
        if hasattr(self, 'chat_input'):
            self.chat_input.set_enabled(True)  # 使用正确的方法名
        elif hasattr(self, 'input_field'):
            self.input_field.setEnabled(True)
            if hasattr(self, 'send_btn'):
                self.send_btn.setEnabled(True)
                self.send_btn.setText("发送")
        
        self.current_worker = None
        
        print("UI状态已重置")


class CollapsibleSidebar(QWidget):
    """可收缩的侧边栏"""
    
    def __init__(self, history_service=None, on_chat_selected=None):
        super().__init__()
        self.is_collapsed = False
        self.normal_width = 280
        self.collapsed_width = 50
        
        # 存储服务和回调
        self.history_service = history_service
        self.on_chat_selected = on_chat_selected
        
        self.setFixedWidth(self.normal_width)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 顶部折叠按钮
        self.collapse_btn = QPushButton("◀")
        self.collapse_btn.setFixedHeight(30)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        layout.addWidget(self.collapse_btn)
        
        # 侧边栏内容容器
        self.content_widget = QStackedWidget()
        layout.addWidget(self.content_widget)
        
        # 添加各个功能页面
        self.setup_pages()
        
    def setup_pages(self):
        """设置侧边栏的各个功能页面"""
        # 1. 聊天历史页面
        self.chat_history_page = self.create_chat_history_page()
        self.content_widget.addWidget(self.chat_history_page)
        
        # 2. 文件夹/收藏夹页面
        self.folders_page = self.create_folders_page()
        self.content_widget.addWidget(self.folders_page)
        
        # 3. 星标页面
        self.starred_page = self.create_starred_page()
        self.content_widget.addWidget(self.starred_page)
        
        # 4. 搜索页面
        self.search_page = self.create_search_page()
        self.content_widget.addWidget(self.search_page)
        
        # 设置默认页面
        self.content_widget.setCurrentIndex(0)
        
    def create_chat_history_page(self):
        """创建聊天历史页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 页面标题和按钮
        header_layout = QHBoxLayout()
        title_label = QLabel("聊天历史")
        title_label.setFont(get_safe_font(size=12, bold=True))
        new_chat_btn = QPushButton("+")
        new_chat_btn.setFixedSize(25, 25)
        new_chat_btn.setToolTip("新建聊天")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(new_chat_btn)
        layout.addLayout(header_layout)
        
        # 使用完整的历史记录管理器
        if ChatHistoryManager and hasattr(self, 'history_service') and self.history_service:
            print("✅ 使用完整的ChatHistoryManager组件")
            self.history_manager = ChatHistoryManager(
                parent=widget,
                history_service=self.history_service,
                on_chat_selected=self.on_chat_selected
            )
            layout.addWidget(self.history_manager)
            
            # 保持引用以便其他方法访问
            self.history_tree = self.history_manager.tree
        else:
            print("⚠️ 使用简单的历史树实现（后备方案）")
            print(f"ChatHistoryManager可用: {ChatHistoryManager is not None}")
            print(f"有history_service: {hasattr(self, 'history_service')}")
            print(f"history_service有效: {getattr(self, 'history_service', None) is not None}")
            # 后备简单实现
            self.history_tree = QTreeWidget()
            self.history_tree.setHeaderHidden(True)
            self.history_tree.setRootIsDecorated(False)
            layout.addWidget(self.history_tree)
        
        # 存储按钮引用以便连接信号
        self.new_chat_btn = new_chat_btn
        
        return widget
        
    def create_folders_page(self):
        """创建文件夹页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title_label = QLabel("文件夹")
        title_label.setFont(get_safe_font(size=12, bold=True))
        layout.addWidget(title_label)
        
        # 文件夹树
        self.folders_tree = QTreeWidget()
        self.folders_tree.setHeaderHidden(True)
        
        # 添加默认文件夹
        recent_item = QTreeWidgetItem(["最近聊天"])
        today_item = QTreeWidgetItem(["今天"])
        yesterday_item = QTreeWidgetItem(["昨天"])
        week_item = QTreeWidgetItem(["本周"])
        month_item = QTreeWidgetItem(["本月"])
        
        self.folders_tree.addTopLevelItem(recent_item)
        self.folders_tree.addTopLevelItem(today_item)
        self.folders_tree.addTopLevelItem(yesterday_item)
        self.folders_tree.addTopLevelItem(week_item)
        self.folders_tree.addTopLevelItem(month_item)
        
        layout.addWidget(self.folders_tree)
        
        return widget
        
    def create_starred_page(self):
        """创建星标页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title_label = QLabel("星标聊天")
        title_label.setFont(get_safe_font(size=12, bold=True))
        layout.addWidget(title_label)
        
        # 星标列表
        self.starred_list = QListWidget()
        layout.addWidget(self.starred_list)
        
        return widget
        
    def create_search_page(self):
        """创建搜索页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title_label = QLabel("搜索")
        title_label.setFont(get_safe_font(size=12, bold=True))
        layout.addWidget(title_label)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索聊天内容...")
        layout.addWidget(self.search_input)
        
        # 搜索结果列表
        self.search_results = QListWidget()
        layout.addWidget(self.search_results)
        
        return widget
        
    def toggle_collapse(self):
        """切换折叠状态"""
        if self.is_collapsed:
            self.expand()
        else:
            self.collapse()
            
    def collapse(self):
        """折叠侧边栏"""
        self.is_collapsed = True
        self.collapse_btn.setText("▶")
        self.setFixedWidth(self.collapsed_width)
        self.content_widget.hide()
        
    def expand(self):
        """展开侧边栏"""
        self.is_collapsed = False
        self.collapse_btn.setText("◀")
        self.setFixedWidth(self.normal_width)
        self.content_widget.show()
        
    def switch_to_page(self, page_index):
        """切换到指定页面"""
        if not self.is_collapsed:
            self.content_widget.setCurrentIndex(page_index)


class SidebarNavigator(QWidget):
    """侧边栏导航按钮"""
    page_changed = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.current_page = 0
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # 导航按钮
        self.nav_buttons = []
        
        # 聊天历史按钮
        history_btn = QPushButton("💬")
        history_btn.setToolTip("聊天历史")
        history_btn.setCheckable(True)
        history_btn.setChecked(True)
        history_btn.clicked.connect(lambda: self.switch_page(0))
        
        # 文件夹按钮
        folder_btn = QPushButton("📁")
        folder_btn.setToolTip("文件夹")
        folder_btn.setCheckable(True)
        folder_btn.clicked.connect(lambda: self.switch_page(1))
        
        # 星标按钮
        star_btn = QPushButton("⭐")
        star_btn.setToolTip("星标")
        star_btn.setCheckable(True)
        star_btn.clicked.connect(lambda: self.switch_page(2))
        
        # 搜索按钮
        search_btn = QPushButton("🔍")
        search_btn.setToolTip("搜索")
        search_btn.setCheckable(True)
        search_btn.clicked.connect(lambda: self.switch_page(3))
        
        self.nav_buttons = [history_btn, folder_btn, star_btn, search_btn]
        
        for btn in self.nav_buttons:
            btn.setFixedSize(40, 40)
            layout.addWidget(btn)
            
        layout.addStretch()
        
    def switch_page(self, page_index):
        """切换页面"""
        if page_index == self.current_page:
            return
            
        # 更新按钮状态
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == page_index)
            
        self.current_page = page_index
        self.page_changed.emit(page_index)


class SettingsPanel(QWidget):
    """设置面板"""
    
    def __init__(self, settings_service):
        super().__init__()
        self.settings_service = settings_service
        # 使用真正的UserSettings类
        self.settings = UserSettings.load()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # 通用设置组
        general_group = QGroupBox("通用设置")
        general_layout = QVBoxLayout(general_group)
        
        # 模型选择
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("默认模型:"))
        self.model_combo = QComboBox()
        for model in ModelType:
            self.model_combo.addItem(model.value)
        self.model_combo.setCurrentText(self.settings.preferred_model.value)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_layout.addWidget(self.model_combo)
        general_layout.addLayout(model_layout)
        
        # 历史记录限制
        history_layout = QHBoxLayout()
        history_layout.addWidget(QLabel("历史记录数量:"))
        self.history_spin = QSpinBox()
        self.history_spin.setRange(10, 1000)
        self.history_spin.setValue(self.settings.history_limit)
        self.history_spin.valueChanged.connect(self.on_history_limit_changed)
        history_layout.addWidget(self.history_spin)
        general_layout.addLayout(history_layout)
        
        # 用户名称设置
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("用户名称:"))
        self.username_edit = QLineEdit()
        self.username_edit.setText(self.settings.user_name)
        self.username_edit.textChanged.connect(self.on_username_changed)
        username_layout.addWidget(self.username_edit)
        general_layout.addLayout(username_layout)

        # 流式回复设置
        self.streaming_check = QCheckBox("启用流式回复")
        self.streaming_check.setChecked(self.settings.enable_streaming)
        self.streaming_check.toggled.connect(self.on_streaming_changed)
        self.streaming_check.setToolTip("开启后，AI回复将逐字显示，提供更好的交互体验")
        general_layout.addWidget(self.streaming_check)
        
        scroll_layout.addWidget(general_group)
        
        # 界面设置组
        ui_group = QGroupBox("界面设置")
        ui_layout = QVBoxLayout(ui_group)
        
        # 深色模式
        self.dark_mode_check = QCheckBox("深色模式")
        self.dark_mode_check.setChecked(self.settings.dark_mode)
        self.dark_mode_check.toggled.connect(self.on_dark_mode_changed)
        ui_layout.addWidget(self.dark_mode_check)
        
        scroll_layout.addWidget(ui_group)
        
        # 高级设置组
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QVBoxLayout(advanced_group)
        
        # API密钥设置（占位符）
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("API密钥:"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("请输入Gemini API密钥")
        api_layout.addWidget(self.api_key_edit)
        advanced_layout.addLayout(api_layout)
        
        scroll_layout.addWidget(advanced_group)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        reset_btn = QPushButton("重置默认")
        reset_btn.clicked.connect(self.reset_settings)
        
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
    def on_model_changed(self, model_text):
        """模型改变回调"""
        try:
            self.settings.preferred_model = ModelType(model_text)
        except ValueError:
            pass
            
    def on_history_limit_changed(self, value):
        """历史记录限制改变回调"""
        self.settings.history_limit = value
        
    def on_username_changed(self, text):
        """用户名称改变回调"""
        self.settings.user_name = text
        
    def on_dark_mode_changed(self, checked):
        """深色模式改变回调"""
        self.settings.dark_mode = checked

    def on_streaming_changed(self, checked):
        """流式回复改变回调"""
        self.settings.enable_streaming = checked
        
    def save_settings(self):
        """保存设置"""
        try:
            self.settings.save()
            # TODO: 显示保存成功消息
        except Exception as e:
            # TODO: 显示错误消息
            pass
            
    def reset_settings(self):
        """重置设置为默认值"""
        self.settings = UserSettings()
        self.refresh_ui()
        
    def refresh_ui(self):
        """刷新UI显示"""
        self.model_combo.setCurrentText(self.settings.preferred_model.value)
        self.history_spin.setValue(self.settings.history_limit)
        self.username_edit.setText(self.settings.user_name)
        self.dark_mode_check.setChecked(self.settings.dark_mode)
        self.streaming_check.setChecked(self.settings.enable_streaming)


class EnhancedMainWindow(QMainWindow):
    """增强版主窗口 - 集成主题系统"""
    
    def __init__(self, service, settings_service, file_upload_service=None):
        super().__init__()
        self.service = service
        self.settings_service = settings_service
        self.history_service = SimpleHistoryService(HISTORY_DIR)
        self.file_upload_service = file_upload_service
        
        # 主题系统
        self.theme_manager = None
        
        # 防重复点击的时间戳
        self._last_history_click_time = 0
        self._history_click_delay = 500  # 500ms防抖动
        
        # 状态管理
        self.current_app_state = None
        self.startup_manager = None
        self.persistency_manager = None
        
        # 欢迎页面
        self.welcome_page = None
        
        self.setWindowTitle("Gemini Chat - Enhanced")
        self.resize(1400, 800)
        
        # 启用拖放支持
        self.setAcceptDrops(True)
        
        # 初始化主题系统（优先）
        self.initialize_theme_system()
        
        # 初始化组件
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_toolbar()
        self.setup_status_bar()
        
        # 设置主题系统集成（在UI创建后）
        if hasattr(self, 'new_theme_manager') and self.new_theme_manager:
            self.setup_theme_regions()
            self.add_theme_menu()
            self.add_theme_status_widget()
        
        # 连接信号
        self.connect_signals()
        
        # 加载数据
        self.load_history()
        
        # 初始化启动管理器和状态管理
        self.init_startup_system()
        
        # 使用智能启动逻辑，而不是直接创建新聊天
        QTimer.singleShot(500, self.smart_startup)  # 500ms延迟
        
    def setup_ui(self):
        """设置UI"""
        # 中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 侧边栏导航
        self.sidebar_nav = SidebarNavigator()
        self.sidebar_nav.setFixedWidth(50)
        main_layout.addWidget(self.sidebar_nav)
        
        # 可收缩侧边栏
        self.sidebar = CollapsibleSidebar(
            history_service=self.history_service,
            on_chat_selected=self.on_history_item_double_clicked_wrapper
        )
        main_layout.addWidget(self.sidebar)
        
        # 主内容区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(content_splitter)
        
        # 聊天区域（标签页）
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        content_splitter.addWidget(self.tab_widget)
        
        # 右侧面板（设置和主题）
        self.right_panel = QStackedWidget()
        self.right_panel.setMaximumWidth(350)
        self.right_panel.hide()  # 默认隐藏
        
        # 设置面板
        self.settings_panel = SettingsPanel(self.settings_service)
        self.right_panel.addWidget(self.settings_panel)
        
        # 主题面板（使用新主题系统）- 如果主题系统可用
        if THEME_SYSTEM_AVAILABLE and hasattr(self, 'new_theme_manager') and self.new_theme_manager:
            # 使用新主题系统时，创建简化的主题面板
            theme_panel_widget = QWidget()
            theme_panel_layout = QVBoxLayout(theme_panel_widget)
            theme_panel_layout.addWidget(QLabel("主题设置已集成到菜单栏"))
            try:
                theme_switcher = ThemeSwitcherWidget(self.new_theme_manager)
                theme_panel_layout.addWidget(theme_switcher)
            except Exception as e:
                print(f"创建主题切换控件失败: {e}")
            self.right_panel.addWidget(theme_panel_widget)
        else:
            # 主题系统不可用时的占位符
            placeholder_widget = QWidget()
            placeholder_layout = QVBoxLayout(placeholder_widget)
            placeholder_layout.addWidget(QLabel("主题系统不可用"))
            self.right_panel.addWidget(placeholder_widget)
        
        content_splitter.addWidget(self.right_panel)
        
        # 设置分割器比例
        content_splitter.setSizes([800, 350])
        
    def setup_menu_bar(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        new_chat_action = QAction("新建聊天", self)
        new_chat_action.setShortcut("Ctrl+N")
        new_chat_action.triggered.connect(self.new_chat)
        file_menu.addAction(new_chat_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("导入聊天", self)
        import_action.triggered.connect(self.import_chat)
        file_menu.addAction(import_action)
        
        export_action = QAction("导出聊天", self)
        export_action.triggered.connect(self.export_chat)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        
        self.toggle_sidebar_action = QAction("显示/隐藏侧边栏", self)
        self.toggle_sidebar_action.setShortcut("Ctrl+B")
        self.toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(self.toggle_sidebar_action)
        
        self.toggle_settings_action = QAction("显示/隐藏设置面板", self)
        self.toggle_settings_action.setShortcut("Ctrl+,")
        self.toggle_settings_action.triggered.connect(self.toggle_settings_panel)
        view_menu.addAction(self.toggle_settings_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")
        
        preferences_action = QAction("首选项", self)
        preferences_action.triggered.connect(self.show_settings_panel)
        settings_menu.addAction(preferences_action)
        
        theme_action = QAction("主题设置", self)
        theme_action.triggered.connect(self.show_theme_panel)
        settings_menu.addAction(theme_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_toolbar(self):
        """设置工具栏"""
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)
        
        # 新建聊天按钮
        new_chat_action = QAction("新建聊天", self)
        new_chat_action.triggered.connect(self.new_chat)
        toolbar.addAction(new_chat_action)
        
        toolbar.addSeparator()
        
        # 模型选择
        toolbar.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        for model in ModelType:
            self.model_combo.addItem(model.value)
        
        # 设置当前模型
        if hasattr(self.settings_service, 'settings'):
            current_model = self.settings_service.settings.preferred_model.value
        else:
            current_model = UserSettings().preferred_model.value
        
        idx = self.model_combo.findText(current_model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
            
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        toolbar.addWidget(self.model_combo)
        
        toolbar.addSeparator()
        
        # 设置按钮
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.toggle_settings_panel)
        toolbar.addAction(settings_action)
        
    def setup_status_bar(self):
        """设置状态栏"""
        self.statusBar().showMessage("准备就绪")
        
    def connect_signals(self):
        """连接信号"""
        # 侧边栏导航信号
        self.sidebar_nav.page_changed.connect(self.sidebar.switch_to_page)
        
        # 新建聊天按钮
        self.sidebar.new_chat_btn.clicked.connect(self.new_chat)
        
        # 历史聊天双击 - 只在使用简单history_tree时连接，ChatHistoryManager有自己的处理
        if hasattr(self.sidebar, 'history_manager') and self.sidebar.history_manager:
            # 使用ChatHistoryManager时，不需要额外连接信号，它有自己的回调处理
            print("✅ 使用ChatHistoryManager的内置事件处理")
        else:
            # 只在简单模式下连接双击事件
            self.sidebar.history_tree.itemDoubleClicked.connect(self.on_history_item_double_clicked)
            print("⚠️ 使用简单历史树的双击事件处理")
        
        # 搜索输入
        if hasattr(self.sidebar, 'search_input'):
            self.sidebar.search_input.textChanged.connect(self.on_search_text_changed)
        
        # 旧版主题管理器信号（如果存在）
        # if hasattr(self, 'theme_panel') and hasattr(self.theme_panel, 'theme_changed'):
        #     self.theme_panel.theme_changed.connect(self.on_old_theme_changed)
        
    def new_chat(self):
        """创建新聊天（创建临时会话）"""
        self.new_ephemeral_chat()
        
    def add_tab(self, conv: Conversation):
        """添加聊天标签页"""
        # 检查是否已经有相同ID的标签页打开
        for i in range(self.tab_widget.count()):
            tab_widget = self.tab_widget.widget(i)
            if hasattr(tab_widget, 'conversation'):
                tab_conv = getattr(tab_widget, 'conversation', None)
                if tab_conv and hasattr(tab_conv, 'id') and tab_conv.id == conv.id:
                    # 标签页已存在，直接切换到该标签页
                    self.tab_widget.setCurrentIndex(i)
                    print(f"标签页已存在，切换到现有标签页: {conv.title}")
                    return
        
        # 优先使用增强聊天标签页
        if ENHANCED_CHAT_AVAILABLE and EnhancedChatTab:
            chat_tab = EnhancedChatTab(
                gemini_service=self.service,
                api_key=getattr(self.service, 'api_key', None) or 
                       (getattr(self.service, 'real_service', None) and getattr(self.service.real_service, 'api_key', None)),
                parent=self
            )
            print("使用增强聊天标签页")
        else:
            # 回退到简单聊天标签页
            chat_tab = SimpleChatTab(
                service=self.service, 
                history_service=self.history_service, 
                conversation=conv, 
                settings_service=self.settings_service,
                file_upload_service=self.file_upload_service
            )
            print("使用简单聊天标签页")
        
        index = self.tab_widget.addTab(chat_tab, conv.title)
        self.tab_widget.setCurrentIndex(index)
        
        # 如果是增强标签页，设置对话信息并加载历史消息
        if ENHANCED_CHAT_AVAILABLE and EnhancedChatTab and isinstance(chat_tab, EnhancedChatTab):
            # 设置会话对象
            chat_tab.conversation = conv
            
            # 如果会话有历史消息，尝试异步加载并显示
            try:
                if hasattr(conv, 'id') and conv.id:
                    # 异步加载历史消息，避免界面卡顿
                    self._load_history_messages_async(chat_tab, conv.id)
            except Exception as e:
                print(f"加载历史消息失败: {e}")
    
    def _load_history_messages_async(self, chat_tab, conv_id):
        """异步加载历史消息，避免界面卡顿"""
        from PySide6.QtCore import QTimer
        
        def load_messages():
            try:
                # 从历史记录仓储加载完整的会话数据
                full_conv = None
                if hasattr(self.history_service, 'repo') and self.history_service.repo:
                    full_conv = self.history_service.repo.load_conversation(conv_id)
                
                if full_conv and hasattr(full_conv, 'messages') and full_conv.messages:
                    # 限制一次加载的消息数量，避免卡顿
                    max_messages = 50  # 最多加载50条消息
                    messages_to_load = full_conv.messages[-max_messages:] if len(full_conv.messages) > max_messages else full_conv.messages
                    
                    # 清空欢迎消息
                    if hasattr(chat_tab, 'clear_conversation'):
                        chat_tab.clear_conversation()
                    
                    # 分批显示历史消息
                    for i, msg in enumerate(messages_to_load):
                        if hasattr(msg, 'role') and hasattr(msg, 'content'):
                            sender = "user" if msg.role.value == "user" else "assistant"
                            if hasattr(chat_tab, 'add_message'):
                                chat_tab.add_message(sender, msg.content, show_files=False)
                        
                        # 每10条消息处理一次事件，保持界面响应
                        if i % 10 == 0:
                            QApplication.processEvents()
                    
                    print(f"异步加载了 {len(messages_to_load)} 条历史消息")
                    
                    # 更新会话对象
                    chat_tab.conversation = self._convert_to_ui_conversation(full_conv)
            except Exception as e:
                print(f"异步加载历史消息失败: {e}")
        
        # 使用QTimer延迟执行，让界面先响应
        QTimer.singleShot(50, load_messages)
    
    def _convert_to_ui_conversation(self, domain_conv):
        """将域模型会话转换为UI会话"""
        try:
            from ui.ui_config import Conversation as UIConversation
            return UIConversation(
                id=domain_conv.id,
                title=domain_conv.title,
                messages=[],  # UI层不直接存储消息
                is_ephemeral=domain_conv.is_ephemeral
            )
        except:
            return domain_conv
        
    def close_tab(self, index):
        """关闭标签页"""
        # 获取要关闭的标签页对应的会话
        tab_widget = self.tab_widget.widget(index)
        conversation = None
        
        if hasattr(tab_widget, 'conversation'):
            conversation = getattr(tab_widget, 'conversation', None)
        
        # 如果有持久化管理器，处理会话关闭的持久化策略
        if self.persistency_manager and conversation:
            self.persistency_manager.handle_chat_close(conversation)
        
        # 执行标签页关闭逻辑
        if self.tab_widget.count() > 1:  # 至少保留一个标签页
            self.tab_widget.removeTab(index)
            # 如果关闭后没有聊天标签页，显示欢迎页
            if self.tab_widget.count() == 0 and self.startup_manager:
                self.show_welcome_page()
        else:
            # 如果只有一个标签页，创建新的或显示欢迎页
            if self.startup_manager:
                self.show_welcome_page()
            else:
                self.new_chat()
            self.tab_widget.removeTab(index)
            
    def load_history(self):
        """加载聊天历史"""
        self.refresh_history()
        
    def refresh_history(self):
        """刷新历史聊天列表"""
        # 如果使用完整的历史管理器，直接调用其refresh方法
        if hasattr(self.sidebar, 'history_manager') and self.sidebar.history_manager:
            self.sidebar.history_manager.refresh_history()
            return
            
        # 否则使用简单的历史树实现（后备方案）
        self.sidebar.history_tree.clear()
        
        try:
            # 加载真实的聊天历史
            conversations = self.history_service.list_conversations()
            
            if conversations:
                print(f"加载了 {len(conversations)} 个历史会话")
                for conv in conversations:
                    item = QTreeWidgetItem([conv.title])
                    item.setData(0, Qt.ItemDataRole.UserRole, conv.id)
                    self.sidebar.history_tree.addTopLevelItem(item)
            else:
                # 如果没有历史记录，显示提示
                item = QTreeWidgetItem(["暂无聊天历史"])
                item.setData(0, Qt.ItemDataRole.UserRole, None)
                self.sidebar.history_tree.addTopLevelItem(item)
                print("没有找到历史会话")
        except Exception as e:
            print(f"加载历史记录失败: {e}")
            # 回退到示例数据（这些示例应该是持久化的）
            for i in range(3):
                conv = Conversation(id=str(uuid4()), title=f"示例聊天 {i+1}", is_ephemeral=False)
                item = QTreeWidgetItem([conv.title])
                item.setData(0, Qt.ItemDataRole.UserRole, conv.id)
                self.sidebar.history_tree.addTopLevelItem(item)
                
    def on_history_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """历史聊天双击事件"""
        conv_id = item.data(0, Qt.ItemDataRole.UserRole)
        if conv_id:
            try:
                loaded_conv = self.history_service.load(conv_id)
                if loaded_conv:
                    # 统一转换为UI对象，从持久化加载的应该不是临时的
                    ui_conv = Conversation(
                        id=getattr(loaded_conv, 'id', conv_id),
                        title=getattr(loaded_conv, 'title', f"会话 {conv_id[:8]}"),
                        messages=[],
                        is_ephemeral=loaded_conv.is_ephemeral
                    )
                    
                    self.add_tab(ui_conv)
                    print(f"打开历史会话: {ui_conv.title}")
                else:
                    print(f"无法加载会话: {conv_id}")
            except Exception as e:
                print(f"打开历史会话失败: {e}")

    def on_history_item_double_clicked_wrapper(self, conv_id: str):
        """历史聊天选择事件包装方法 - 改进为行业标准的加载模式"""
        import time
        
        # 1. 防抖动检查
        current_time = int(time.time() * 1000)
        if current_time - self._last_history_click_time < self._history_click_delay:
            print("忽略过于频繁的历史记录点击")
            return False
        
        self._last_history_click_time = current_time
        
        # 2. 显示全局加载状态
        self._show_global_loading_state("正在加载聊天记录...")
        
        # 3. 异步加载聊天记录
        self._load_conversation_async(conv_id)
        
        return True  # 返回True表示开始处理
    
    def _show_global_loading_state(self, message: str):
        """显示全局加载状态"""
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(message)
        # 可以在这里添加加载动画或进度条
        
    def _hide_global_loading_state(self):
        """隐藏全局加载状态"""
        if hasattr(self, 'statusBar'):
            self.statusBar().clearMessage()
            
    def _load_conversation_async(self, conv_id: str):
        """异步加载会话 - 行业标准的分阶段加载"""
        from PySide6.QtCore import QTimer
        
        def load_conversation():
            try:
                # 4. 第一阶段：加载会话基本信息
                print(f"开始加载会话: {conv_id}")
                loaded_conv = self.history_service.load(conv_id)
                
                if not loaded_conv:
                    self._handle_load_error(f"无法找到会话: {conv_id}")
                    return
                
                # 5. 统一转换为UI对象
                ui_conv = Conversation(
                    id=getattr(loaded_conv, 'id', conv_id),
                    title=getattr(loaded_conv, 'title', f"会话 {conv_id[:8]}"),
                    messages=[]
                )
                
                # 6. 第二阶段：创建标签页（快速响应）
                self._create_tab_with_placeholder(ui_conv)
                
                # 7. 第三阶段：异步加载历史消息（避免阻塞）
                self._load_messages_progressive(ui_conv, loaded_conv)
                
            except Exception as e:
                print(f"加载会话失败: {e}")
                import traceback
                print(f"错误堆栈: {traceback.format_exc()}")
                self._handle_load_error(f"加载会话时发生错误: {str(e)}")
        
        # 使用QTimer实现真正的异步
        QTimer.singleShot(10, load_conversation)
    
    def _create_tab_with_placeholder(self, ui_conv: Conversation):
        """创建带占位符的标签页 - 快速响应用户操作"""
        # 检查是否已经有相同ID的标签页打开
        existing_tab_index = self._find_existing_tab(ui_conv.id)
        if existing_tab_index >= 0:
            self.tab_widget.setCurrentIndex(existing_tab_index)
            print(f"标签页已存在，切换到现有标签页: {ui_conv.title}")
            self._hide_global_loading_state()
            return existing_tab_index
        
        # 创建新标签页
        chat_tab = self._create_chat_tab(ui_conv)
        
        index = self.tab_widget.addTab(chat_tab, ui_conv.title)
        self.tab_widget.setCurrentIndex(index)
        
        print(f"创建新标签页: {ui_conv.title}")
        return index
        
    def _find_existing_tab(self, conv_id: str) -> int:
        """查找已存在的标签页"""
        for i in range(self.tab_widget.count()):
            tab_widget = self.tab_widget.widget(i)
            if hasattr(tab_widget, 'conversation'):
                tab_conv = getattr(tab_widget, 'conversation', None)
                if tab_conv and hasattr(tab_conv, 'id') and tab_conv.id == conv_id:
                    return i
        return -1
    
    def _create_chat_tab(self, ui_conv: Conversation):
        """创建聊天标签页"""
        if ENHANCED_CHAT_AVAILABLE and EnhancedChatTab:
            chat_tab = EnhancedChatTab(
                gemini_service=self.service,
                api_key=getattr(self.service, 'api_key', None) or 
                       (getattr(self.service, 'real_service', None) and getattr(self.service.real_service, 'api_key', None)),
                parent=self
            )
            print("使用增强聊天标签页")
        else:
            chat_tab = SimpleChatTab(
                service=self.service, 
                history_service=self.history_service, 
                conversation=ui_conv, 
                settings_service=self.settings_service,
                file_upload_service=self.file_upload_service
            )
            print("使用简单聊天标签页")
        
        chat_tab.conversation = ui_conv
        return chat_tab
    
    def _load_messages_progressive(self, ui_conv: Conversation, loaded_conv):
        """渐进式加载消息 - 分批次加载避免卡顿"""
        from PySide6.QtCore import QTimer
        
        def load_messages_batch():
            try:
                # 获取当前标签页
                current_tab = self.tab_widget.currentWidget()
                if not current_tab or not hasattr(current_tab, 'conversation'):
                    self._hide_global_loading_state()
                    return
                
                # 确认是正确的标签页
                current_conv = getattr(current_tab, 'conversation', None)
                if not current_conv or getattr(current_conv, 'id', None) != ui_conv.id:
                    self._hide_global_loading_state()
                    return
                
                # 从历史记录加载完整消息
                full_conv = None
                if hasattr(self.history_service, 'repo') and self.history_service.repo:
                    full_conv = self.history_service.repo.load_conversation(ui_conv.id)
                
                if full_conv and hasattr(full_conv, 'messages') and full_conv.messages:
                    print(f"开始加载 {len(full_conv.messages)} 条历史消息")
                    
                    # 清空占位符内容
                    clear_method = getattr(current_tab, 'clear_conversation', None)
                    if clear_method and callable(clear_method):
                        clear_method()
                    
                    # 分批加载消息，避免界面卡顿
                    self._load_messages_in_batches(current_tab, full_conv.messages)
                    
                    # 更新会话对象
                    if hasattr(current_tab, 'conversation'):
                        setattr(current_tab, 'conversation', self._convert_to_ui_conversation(full_conv))
                else:
                    print("没有找到历史消息")
                
                self._hide_global_loading_state()
                
            except Exception as e:
                print(f"加载历史消息失败: {e}")
                self._handle_load_error(f"加载历史消息时发生错误: {str(e)}")
        
        # 延迟加载，让标签页先显示
        QTimer.singleShot(100, load_messages_batch)
    
    def _load_messages_in_batches(self, chat_tab, messages, batch_size: int = 10):
        """分批次加载消息"""
        from PySide6.QtCore import QTimer
        
        def load_next_batch(start_index: int = 0):
            try:
                end_index = min(start_index + batch_size, len(messages))
                batch = messages[start_index:end_index]
                
                # 加载当前批次
                for msg in batch:
                    if hasattr(msg, 'role') and hasattr(msg, 'content'):
                        sender = "user" if msg.role.value == "user" else "assistant"
                        if hasattr(chat_tab, 'add_message'):
                            chat_tab.add_message(sender, msg.content, show_files=False)
                
                print(f"加载了第 {start_index//batch_size + 1} 批消息 ({start_index+1}-{end_index})")
                
                # 处理事件保持界面响应
                QApplication.processEvents()
                
                # 如果还有更多消息，继续加载下一批
                if end_index < len(messages):
                    QTimer.singleShot(50, lambda: load_next_batch(end_index))
                else:
                    print(f"所有 {len(messages)} 条消息加载完成")
                    
            except Exception as e:
                print(f"批次加载失败: {e}")
        
        # 开始加载第一批
        if messages:
            load_next_batch(0)
    
    def _handle_load_error(self, error_msg: str):
        """统一的错误处理"""
        print(f"加载错误: {error_msg}")
        self._hide_global_loading_state()
        
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(
            self,
            "加载失败",
            error_msg,
            QMessageBox.StandardButton.Ok
        )
            
    def on_search_text_changed(self, text):
        """搜索文本变化事件"""
        # TODO: 实现搜索功能
        pass
        
    def on_model_changed(self, model_str: str):
        """模型变化事件"""
        try:
            # 直接传递字符串，不需要转换为ModelType枚举
            self.service.set_model(model_str)
            
            # 更新设置
            if hasattr(self.settings_service, 'settings'):
                # 找到对应的ModelType枚举值
                for model_type in ModelType:
                    if model_type.value == model_str:
                        self.settings_service.settings.preferred_model = model_type
                        self.settings_service.settings.save()
                        break
                
            self.statusBar().showMessage(f"已切换到模型: {model_str}", 2000)
        except Exception as e:
            print(f"模型切换失败: {e}")
            
    def on_old_theme_changed(self, theme_id):
        """旧版主题变化事件"""
        # 这个方法保留用于向后兼容，如果需要的话
        pass
        
    def toggle_sidebar(self):
        """切换侧边栏显示状态"""
        self.sidebar.toggle_collapse()
        
    def toggle_settings_panel(self):
        """切换设置面板显示状态"""
        if self.right_panel.isVisible():
            self.right_panel.hide()
        else:
            self.right_panel.setCurrentIndex(0)  # 显示设置面板
            self.right_panel.show()
            
    def show_settings_panel(self):
        """显示设置面板"""
        self.right_panel.setCurrentIndex(0)
        self.right_panel.show()
        
    def show_theme_panel(self):
        """显示主题面板"""
        self.right_panel.setCurrentIndex(1)
        self.right_panel.show()
        
    def import_chat(self):
        """导入聊天"""
        # TODO: 实现导入功能
        self.statusBar().showMessage("导入功能待实现", 2000)
        
    def export_chat(self):
        """导出聊天"""
        # TODO: 实现导出功能
        self.statusBar().showMessage("导出功能待实现", 2000)
        
    def show_about(self):
        """显示关于对话框"""
        # TODO: 实现关于对话框
        self.statusBar().showMessage("Gemini Chat Enhanced v1.0 - 功能齐全的AI聊天界面", 3000)

    def init_startup_system(self):
        """初始化启动系统"""
        try:
            from services.startup_manager import StartupManager
            from services.persistency_manager import PersistencyManager
            
            self.startup_manager = StartupManager(self.history_service, self.settings_service)
            self.persistency_manager = PersistencyManager(self.history_service)
        except Exception as e:
            print(f"启动系统初始化失败: {e}")
            self.startup_manager = None
            self.persistency_manager = None
    
    def smart_startup(self):
        """智能启动逻辑"""
        from geminichat.domain.app_state import AppStateType
        
        if not self.startup_manager:
            # 如果启动管理器不可用，创建新的临时会话
            self.new_ephemeral_chat()
            return
        # 获取启动状态
        startup_state = self.startup_manager.determine_startup_state()
        self.current_app_state = startup_state
        
        if startup_state.type == AppStateType.WELCOME:
            # 显示欢迎页
            self.show_welcome_page()
        elif startup_state.type == AppStateType.CHAT_VIEW:
            if startup_state.payload:
                # 有外部负载，创建新会话并预填充
                conversation = self.startup_manager.create_chat_with_payload(startup_state.payload)
                self.add_tab_with_conversation(conversation)
            elif startup_state.current_chat_id:
                # 恢复之前的会话
                conversation = self.startup_manager.load_existing_chat(startup_state.current_chat_id)
                if conversation:
                    self.add_tab_with_conversation(conversation)
                else:
                    print(f"无法加载会话 {startup_state.current_chat_id}，显示欢迎页")
                    self.show_welcome_page()
            else:
                # 创建新会话
                self.new_ephemeral_chat()
        else:
            # 默认创建新会话
            self.new_ephemeral_chat()
    
    def show_welcome_page(self):
        """显示欢迎页面"""
        from ui.welcome_page import WelcomePage
        from geminichat.domain.app_state import AppStateType, AppState
        
        if not self.welcome_page:
            self.welcome_page = WelcomePage(self.history_service)
            # 连接信号
            self.welcome_page.new_chat_requested.connect(self.new_ephemeral_chat)
            self.welcome_page.open_chat_requested.connect(self.open_chat_by_id)
            self.welcome_page.import_requested.connect(self.import_chat)
            self.welcome_page.settings_requested.connect(self.show_settings_panel)
        
        # 添加为标签页
        index = self.tab_widget.addTab(self.welcome_page, "欢迎")
        self.tab_widget.setCurrentIndex(index)
        
        # 更新状态
        self.current_app_state = AppState(AppStateType.WELCOME)
    
    def new_ephemeral_chat(self):
        """创建新的临时会话"""
        from geminichat.domain.conversation import Conversation
        from geminichat.domain.app_state import AppStateType, AppState
        from ui.ui_config import Conversation as UIConversation
        
        # 创建临时会话
        conv = UIConversation(title="", is_ephemeral=True)
        
        # 添加标签页
        self.add_tab_with_conversation(conv)
        
        # 更新状态
        self.current_app_state = AppState(AppStateType.CHAT_VIEW, current_chat_id=conv.id)
    
    def add_tab_with_conversation(self, conv):
        """使用给定的会话对象添加标签页"""
        from ui.ui_config import create_conversation_from_domain
        
        # 确保会话对象兼容UI层
        ui_conv = create_conversation_from_domain(conv)
        
        # 检查是否已经有相同ID的标签页打开
        for i in range(self.tab_widget.count()):
            tab_widget = self.tab_widget.widget(i)
            if hasattr(tab_widget, 'conversation'):
                tab_conv = getattr(tab_widget, 'conversation', None)
                if tab_conv and hasattr(tab_conv, 'id') and tab_conv.id == ui_conv.id:
                    # 标签页已存在，直接切换到该标签页
                    self.tab_widget.setCurrentIndex(i)
                    print(f"标签页已存在，切换到现有标签页: {ui_conv.title}")
                    return
        
        # 如果当前显示的是欢迎页，则关闭它
        self.close_welcome_page_if_active()
        
        # 优先使用增强聊天标签页
        if ENHANCED_CHAT_AVAILABLE and EnhancedChatTab:
            chat_tab = EnhancedChatTab(
                gemini_service=self.service,
                api_key=getattr(self.service, 'api_key', None) or 
                       (getattr(self.service, 'real_service', None) and getattr(self.service.real_service, 'api_key', None)),
                parent=self
            )
            print("使用增强聊天标签页")
        else:
            # 回退到简单聊天标签页
            chat_tab = SimpleChatTab(
                service=self.service, 
                history_service=self.history_service, 
                conversation=ui_conv, 
                settings_service=self.settings_service,
                file_upload_service=self.file_upload_service
            )
            print("使用简单聊天标签页")
        
        # 设置标签标题
        tab_title = ui_conv.title if ui_conv.title else ("新聊天" if not ui_conv.is_ephemeral else "临时聊天")
        index = self.tab_widget.addTab(chat_tab, tab_title)
        self.tab_widget.setCurrentIndex(index)
        
        # 如果是增强标签页，设置对话信息并加载历史消息
        if ENHANCED_CHAT_AVAILABLE and EnhancedChatTab and isinstance(chat_tab, EnhancedChatTab):
            # 设置会话对象
            chat_tab.conversation = ui_conv
            
            # 如果会话有历史消息，尝试异步加载并显示
            try:
                if hasattr(ui_conv, 'id') and ui_conv.id and ui_conv.messages:
                    # 异步加载历史消息，避免界面卡顿
                    QTimer.singleShot(100, lambda: self.load_conversation_messages(chat_tab, ui_conv))
            except Exception as e:
                print(f"加载历史消息失败: {e}")
    
    def close_welcome_page_if_active(self):
        """如果当前活跃的是欢迎页，则关闭它"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            current_widget = self.tab_widget.widget(current_index)
            if current_widget == self.welcome_page:
                self.tab_widget.removeTab(current_index)
    
    def open_chat_by_id(self, chat_id: str):
        """通过ID打开聊天"""
        if not self.startup_manager:
            print("启动管理器不可用")
            return
            
        # 处理会话切换的持久化策略
        current_chat = self.get_current_active_chat()
        if current_chat and self.persistency_manager:
            self.persistency_manager.handle_chat_switch(current_chat, chat_id)
        
        # 加载目标会话
        conversation = self.startup_manager.load_existing_chat(chat_id)
        if conversation:
            self.add_tab_with_conversation(conversation)
            # 更新状态
            from geminichat.domain.app_state import AppStateType, AppState
            self.current_app_state = AppState(AppStateType.CHAT_VIEW, current_chat_id=chat_id)
        else:
            print(f"无法加载会话: {chat_id}")
            self.statusBar().showMessage("无法加载该聊天记录", 2000)
    
    def get_current_active_chat(self):
        """获取当前活跃的聊天会话"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            current_widget = self.tab_widget.widget(current_index)
            if hasattr(current_widget, 'conversation'):
                return getattr(current_widget, 'conversation', None)
        return None
    
    def load_conversation_messages(self, chat_tab, conversation):
        """加载会话消息到聊天标签页"""
        try:
            # 检查conversation类型并进行处理
            if hasattr(conversation, 'is_ephemeral') and not hasattr(conversation, 'role'):
                # 如果是UI Conversation，转换处理
                if hasattr(chat_tab, 'load_conversation'):
                    chat_tab.load_conversation(conversation)
                elif hasattr(chat_tab, 'display_messages'):
                    for message in conversation.messages:
                        if isinstance(message, dict):
                            role = message.get('role', 'user')
                            content = message.get('content', '')
                            chat_tab.display_messages(role, content)
                        else:
                            # 如果message是对象，尝试获取属性
                            role = getattr(message, 'role', 'user')
                            if hasattr(role, 'value') and not isinstance(role, str):
                                role_str = role.value
                            else:
                                role_str = str(role)
                            content = getattr(message, 'content', '')
                            chat_tab.display_messages(role_str, content)
            else:
                # 如果是域模型Conversation，直接处理
                if hasattr(chat_tab, 'load_conversation'):
                    chat_tab.load_conversation(conversation)
                elif hasattr(chat_tab, 'display_messages'):
                    for message in conversation.messages:
                        if hasattr(message, 'role'):
                            role = message.role
                            if hasattr(role, 'value') and not isinstance(role, str):
                                role_str = role.value
                            else:
                                role_str = str(role)
                            chat_tab.display_messages(role_str, message.content)
        except Exception as e:
            print(f"加载会话消息失败: {e}")
    
    def closeEvent(self, event):
        """应用退出事件处理"""
        if self.persistency_manager:
            try:
                # 获取所有活跃会话并处理持久化
                active_chats = []
                for i in range(self.tab_widget.count()):
                    tab_widget = self.tab_widget.widget(i)
                    if hasattr(tab_widget, 'conversation'):
                        conv = getattr(tab_widget, 'conversation', None)
                        if conv:
                            active_chats.append(conv)
                
                # 执行退出时的持久化策略
                self.persistency_manager.handle_app_exit(active_chats)
            except Exception as e:
                print(f"退出时处理持久化失败: {e}")
        
        super().closeEvent(event)
    
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    
    def dropEvent(self, event):
        """拖放事件处理"""
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return
        
        try:
            from geminichat.domain.app_state import PayloadParser
            
            # 获取拖拽的文件路径
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_paths.append(url.toLocalFile())
            
            if not file_paths:
                return
            
            # 解析为负载
            payload = PayloadParser.parse_file_drop(file_paths)
            if not payload:
                self.statusBar().showMessage("无法处理拖拽的文件", 2000)
                return
            
            # 处理外部负载
            if self.startup_manager:
                current_chat = self.get_current_active_chat()
                current_state = self.current_app_state
                
                # 如果没有当前状态，创建一个默认状态
                if not current_state:
                    from geminichat.domain.app_state import AppState, AppStateType
                    current_state = AppState(AppStateType.WELCOME)
                
                should_create_new, conversation = self.startup_manager.handle_external_payload_during_runtime(
                    payload, current_state, current_chat
                )
                
                if should_create_new:
                    # 创建新会话
                    self.add_tab_with_conversation(conversation)
                    self.statusBar().showMessage(f"已创建新会话处理文件: {payload.source}", 3000)
                else:
                    # 使用现有会话
                    if current_chat:
                        # 刷新当前标签页以显示新增内容
                        self.refresh_current_tab()
                        self.statusBar().showMessage(f"已在当前会话中添加文件: {payload.source}", 3000)
            else:
                self.statusBar().showMessage("拖放功能需要启动管理器支持", 2000)
                
            event.acceptProposedAction()
            
        except Exception as e:
            print(f"处理拖放事件失败: {e}")
            self.statusBar().showMessage("处理拖拽文件时发生错误", 2000)
    
    def refresh_current_tab(self):
        """刷新当前标签页"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            current_widget = self.tab_widget.widget(current_index)
            if hasattr(current_widget, 'refresh') and callable(getattr(current_widget, 'refresh')):
                current_widget.refresh()  # type: ignore
            elif hasattr(current_widget, 'update_display') and callable(getattr(current_widget, 'update_display')):
                current_widget.update_display()  # type: ignore
    
    # ==================== 主题系统集成方法 ====================
    
    def initialize_theme_system(self):
        """初始化主题系统"""
        if not THEME_SYSTEM_AVAILABLE or not NewThemeManager:
            print("⚠️ 主题系统不可用，跳过初始化")
            return False
        
        try:
            # 确定应用数据目录
            app_data_dir = Path.home() / ".gemini_chat"
            app_data_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建新主题管理器（重命名为避免冲突）
            self.new_theme_manager = NewThemeManager(str(app_data_dir))
            
            # 连接主题变更信号
            self.new_theme_manager.theme_changed.connect(self.on_theme_changed)
            # self.new_theme_manager.theme_error.connect(self.on_theme_error)  # 方法不存在，暂时注释
            
            # 应用默认主题
            self.new_theme_manager.apply_theme_to_app()
            print("✅ 已应用默认主题")
            
            print("✅ 主题系统初始化成功")
            return True
            
        except Exception as e:
            print(f"❌ 主题系统初始化失败: {e}")
            self.new_theme_manager = None
            return False
    
    def setup_theme_regions(self):
        """设置主题区域控件映射"""
        if not hasattr(self, 'new_theme_manager') or not self.new_theme_manager:
            return
        
        # 定义区域控件映射
        regions_mapping = {}
        
        # 侧边栏区域
        if hasattr(self, 'sidebar') and self.sidebar:
            self.sidebar.setObjectName("Region::Sidebar")
            if RegionNames:
                regions_mapping[RegionNames.SIDEBAR] = self.sidebar
        
        # 标签栏区域
        if hasattr(self, 'tab_widget') and self.tab_widget:
            self.tab_widget.setObjectName("Region::TabBar") 
            if RegionNames:
                regions_mapping[RegionNames.TAB_BAR] = self.tab_widget
        
        # 工具栏区域（如果存在）
        toolbars = self.findChildren(QToolBar)
        if toolbars and RegionNames:
            toolbars[0].setObjectName("Region::Toolbar")
            regions_mapping[RegionNames.TOOLBAR] = toolbars[0]
        
        # 状态栏区域
        if self.statusBar() and RegionNames:
            self.statusBar().setObjectName("Region::StatusBar")
            regions_mapping[RegionNames.STATUS_BAR] = self.statusBar()
        
        # 设置面板区域（如果存在）
        if hasattr(self, 'settings_panel') and self.settings_panel and RegionNames:
            self.settings_panel.setObjectName("Region::SettingsDialog")
            regions_mapping[RegionNames.SETTINGS_DIALOG] = self.settings_panel
        
        # 应用区域映射
        # self.new_theme_manager.setup_region_widgets(regions_mapping)  # 方法不存在，暂时注释
        
        print(f"✅ 已设置 {len(regions_mapping)} 个主题区域")
    
    def add_theme_menu(self):
        """添加主题菜单"""
        if not hasattr(self, 'new_theme_manager') or not self.new_theme_manager:
            return
        
        menu_bar = self.menuBar()
        
        # 查找或创建主题菜单
        theme_menu = None
        for action in menu_bar.actions():
            if action.text() == "主题(&T)":
                menu_obj = action.menu()
                if menu_obj:
                    theme_menu = menu_obj
                break
        
        if not theme_menu:
            theme_menu = menu_bar.addMenu("主题(&T)")
        
        # 确保 theme_menu 不为 None 且为 QMenu 类型
        if theme_menu is None:
            return
        
        # 类型转换，确保类型检查器正确识别
        from PySide6.QtWidgets import QMenu
        if not isinstance(theme_menu, QMenu):
            return
        
        # 清空现有菜单项
        theme_menu.clear()
        
        # 主题设置
        settings_action = QAction("主题设置...", self)
        settings_action.setShortcut("Ctrl+T")
        settings_action.triggered.connect(self.open_theme_settings_dialog)
        theme_menu.addAction(settings_action)
        
        theme_menu.addSeparator()
        
        # 快速切换子菜单
        quick_menu = theme_menu.addMenu("快速切换")
        self.refresh_quick_theme_menu(quick_menu)
        
        theme_menu.addSeparator()
        
        # 主题管理
        import_action = QAction("导入主题...", self)
        import_action.triggered.connect(self.import_theme_file)
        theme_menu.addAction(import_action)
        
        export_action = QAction("导出当前主题...", self)
        export_action.triggered.connect(self.export_current_theme)
        theme_menu.addAction(export_action)
        
        theme_menu.addSeparator()
        
        # 主题编辑器
        editor_action = QAction("主题编辑器...", self)
        editor_action.triggered.connect(self.open_theme_editor)
        theme_menu.addAction(editor_action)
    
    def refresh_quick_theme_menu(self, menu: QMenu):
        """刷新快速切换主题菜单"""
        if not hasattr(self, 'new_theme_manager') or not self.new_theme_manager:
            return
        
        menu.clear()
        
        try:
            current_theme = self.new_theme_manager.get_current_theme_name()
            available_themes = self.new_theme_manager.get_available_themes()
            
            for theme_name in available_themes:
                action = QAction(theme_name, self)
                action.setCheckable(True)
                action.setChecked(theme_name == current_theme)
                action.triggered.connect(
                    lambda checked, name=theme_name: self.switch_to_theme(name)
                )
                menu.addAction(action)
        except Exception as e:
            print(f"刷新快速主题菜单失败: {e}")
    
    def add_theme_status_widget(self):
        """添加主题切换控件到状态栏"""
        if not hasattr(self, 'new_theme_manager') or not self.new_theme_manager or not THEME_SYSTEM_AVAILABLE or not CompactThemeSwitcher:
            return
        
        try:
            # 创建紧凑主题切换器
            theme_switcher = CompactThemeSwitcher(self.new_theme_manager)
            theme_switcher.theme_changed.connect(self.on_theme_switched_by_user)
            
            # 添加到状态栏
            self.statusBar().addPermanentWidget(theme_switcher)
            
            print("✅ 主题切换控件已添加到状态栏")
            
        except Exception as e:
            print(f"❌ 添加主题状态栏控件失败: {e}")
    
    def switch_to_theme(self, theme_name: str):
        """切换到指定主题"""
        if hasattr(self, 'new_theme_manager') and self.new_theme_manager:
            # success = self.new_theme_manager.switch_theme(theme_name)  # 方法不存在，使用替代方案
            self.new_theme_manager.set_theme(theme_name)
            self.statusBar().showMessage(f"已切换到主题: {theme_name}", 2000)
    
    def open_theme_settings_dialog(self):
        """打开主题设置对话框"""
        if not hasattr(self, 'new_theme_manager') or not self.new_theme_manager or not THEME_SYSTEM_AVAILABLE or not ThemeSwitcherWidget:
            return
        
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout
            
            dialog = QDialog(self)
            dialog.setWindowTitle("主题设置")
            dialog.setModal(True)
            dialog.resize(700, 600)
            
            layout = QVBoxLayout(dialog)
            
            # 主题切换器
            theme_switcher = ThemeSwitcherWidget(self.new_theme_manager)
            layout.addWidget(theme_switcher)
            
            # 关闭按钮
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            dialog.exec()
            
        except Exception as e:
            print(f"❌ 打开主题设置对话框失败: {e}")
    
    def open_theme_editor(self):
        """打开主题编辑器"""
        if not hasattr(self, 'new_theme_manager') or not self.new_theme_manager:
            return
        
        try:
            # editor = self.new_theme_manager.open_theme_editor(self)  # 方法不存在
            # if editor:
            #     editor.exec()
            print("主题编辑器功能暂未实现")
        except Exception as e:
            print(f"❌ 打开主题编辑器失败: {e}")
    
    def import_theme_file(self):
        """导入主题文件"""
        if not hasattr(self, 'new_theme_manager') or not self.new_theme_manager:
            return
        
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入主题", "", "主题文件 (*.json)"
        )
        
        if file_path:
            # success = self.new_theme_manager.import_theme_from_file(Path(file_path))  # 方法不存在
            # if success:
            #     QMessageBox.information(self, "成功", "主题导入成功！")
            #     self.refresh_quick_theme_menu_all()
            print("主题导入功能暂未实现")
    
    def export_current_theme(self):
        """导出当前主题"""
        if not hasattr(self, 'new_theme_manager') or not self.new_theme_manager:
            return
        
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        
        current_theme = self.new_theme_manager.get_current_theme_name()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出主题", f"{current_theme}.json", "主题文件 (*.json)"
        )
        
        if file_path:
            # success = self.new_theme_manager.export_theme_to_file(current_theme, Path(file_path))  # 方法不存在
            # if success:
            #     QMessageBox.information(self, "成功", "主题导出成功！")
            print("主题导出功能暂未实现")
    
    def refresh_quick_theme_menu_all(self):
        """刷新所有快速主题菜单"""
        # 查找主题菜单并刷新
        menu_bar = self.menuBar()
        for action in menu_bar.actions():
            if action.text() == "主题(&T)":
                theme_menu_obj = action.menu()
                if theme_menu_obj:
                    from PySide6.QtWidgets import QMenu
                    if isinstance(theme_menu_obj, QMenu):
                        for sub_action in theme_menu_obj.actions():
                            if sub_action.text() == "快速切换":
                                quick_menu_obj = sub_action.menu()
                                if quick_menu_obj and isinstance(quick_menu_obj, QMenu):
                                    self.refresh_quick_theme_menu(quick_menu_obj)
                break
    
    def on_theme_changed(self, theme_name: str):
        """主题变更事件处理"""
        print(f"✅ 主题已切换: {theme_name}")
        
        # 更新窗口标题
        base_title = "Gemini Chat - Enhanced"
        self.setWindowTitle(f"{base_title} ({theme_name})")
        
        # 刷新快速切换菜单
        self.refresh_quick_theme_menu_all()
        
        # 状态栏消息
        self.statusBar().showMessage(f"主题已切换: {theme_name}", 3000)
    
    def on_theme_error(self, error_message: str):
        """主题错误处理"""
        print(f"❌ 主题错误: {error_message}")
        
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "主题错误", error_message)
    
    def on_theme_switched_by_user(self, theme_name: str):
        """用户手动切换主题"""
        print(f"👤 用户切换主题: {theme_name}")
        # 应用主题到应用程序
        if hasattr(self, 'new_theme_manager') and self.new_theme_manager:
            self.new_theme_manager.apply_theme_to_app()
            print(f"✅ 已应用主题: {theme_name}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 初始化服务
    settings_service = SimpleSettingsService()
    service = SimpleGeminiService(ModelType.GEMINI_2_5_FLASH)
    
    # 初始化文件上传服务
    try:
        from services.file_upload_service import get_file_upload_service
        file_upload_service = get_file_upload_service(getattr(service, 'api_key', None))
    except ImportError as e:
        print(f"文件上传服务不可用: {e}")
        file_upload_service = None
    
    # 创建并显示窗口
    window = EnhancedMainWindow(service, settings_service, file_upload_service)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
