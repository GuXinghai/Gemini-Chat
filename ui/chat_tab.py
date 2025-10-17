"""
增强聊天标签页
集成多模态文件上传功能的完整聊天界面
"""
import sys
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QTextCursor

# 添加项目根目录到路径
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir))

from services.file_upload_service import ProcessedFile
from ui.chat_input import EnhancedChatInput
from ui.ui_config import Conversation, SimpleGeminiService


class MultimodalAsyncWorker(QThread):
    """支持多模态的异步工作线程"""
    
    stream_chunk = Signal(str)
    response_received = Signal(str)  
    error_occurred = Signal(str)
    
    def __init__(self, service, user_message: str, conversation, processed_files: Optional[List[ProcessedFile]] = None, streaming: bool = True, api_key: Optional[str] = None):
        super().__init__()
        self.service = service
        self.user_message = user_message
        self.conversation = conversation
        self.processed_files = processed_files or []
        self.streaming = streaming
        self.api_key = api_key
        
    def run(self):
        """执行任务"""
        try:
            if self.streaming:
                asyncio.run(self._stream_message_with_files())
            else:
                asyncio.run(self._send_message_with_files())
        except Exception as e:
            print(f"MultimodalAsyncWorker异常: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            self.error_occurred.emit(str(e))
        finally:
            print("MultimodalAsyncWorker完成")
                    
    async def _send_message_with_files(self):
        """发送非流式消息（带文件）"""
        try:
            print(f"开始发送非流式消息（带文件）: {self.user_message}")
            
            # 准备内容 - 支持文件
            content_parts = []
            
            # 添加文本内容
            if self.user_message:
                content_parts.append(self.user_message)
            
            # 添加文件引用 - 转换为Gemini格式（仅当有文件时）
            if self.processed_files:
                from services.file_upload_service import get_file_upload_service
                file_service = get_file_upload_service(self.api_key)
                gemini_parts = file_service.create_gemini_parts(self.processed_files)
                content_parts.extend(gemini_parts)
            
            # 发送消息
            assistant_message, updated_conversation = await self.service.send_message_async(
                content=content_parts if len(content_parts) > 1 else content_parts[0] if content_parts else "",
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
            
            # 添加文件引用 - 转换为Gemini格式（仅当有文件时）
            if self.processed_files:
                from services.file_upload_service import get_file_upload_service
                file_service = get_file_upload_service(self.api_key)
                gemini_parts = file_service.create_gemini_parts(self.processed_files)
                content_parts.extend(gemini_parts)
            
            chunk_count = 0
            async for chunk, updated_conversation in self.service.send_message_stream_async(
                content=content_parts if len(content_parts) > 1 else content_parts[0] if content_parts else "",
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


class EnhancedChatTab(QWidget):
    """增强聊天标签页，支持多模态输入"""
    
    def __init__(self, gemini_service, api_key: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.gemini_service = gemini_service
        self.api_key = api_key
        self.conversation = Conversation()
        
        # 当前处理状态
        self.current_worker = None
        self.current_response_parts = []
        
        # 加载用户设置
        from geminichat.domain.user_settings import UserSettings
        self.user_settings = UserSettings.load()
        
        self.setup_ui()
        self.connect_signals()
        
        print("增强聊天标签页初始化完成")
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建聊天显示区域
        self.create_chat_display(layout)
        
        # 创建聊天输入区域
        self.create_chat_input(layout)
    
    def create_chat_display(self, parent_layout: QVBoxLayout):
        """创建聊天显示区域"""
        # 聊天历史滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy(1))  # AlwaysOff
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy(0))  # AsNeeded
        
        # 聊天内容容器
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()  # 添加弹簧，让消息从底部开始
        
        self.scroll_area.setWidget(self.chat_content)
        parent_layout.addWidget(self.scroll_area, 1)  # 占据大部分空间
        
        # 添加欢迎消息
        self.add_welcome_message()
    
    def create_chat_input(self, parent_layout: QVBoxLayout):
        """创建聊天输入区域"""
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #ddd;")
        parent_layout.addWidget(separator)
        
        # 增强聊天输入
        self.chat_input = EnhancedChatInput(self.api_key, self)
        parent_layout.addWidget(self.chat_input, 0)  # 固定高度
    
    def connect_signals(self):
        """连接信号"""
        # 聊天输入信号
        self.chat_input.send_message.connect(self.send_message_with_files)
    
    def add_welcome_message(self):
        """添加欢迎消息"""
        welcome_text = (
            "👋 欢迎使用 Gemini Chat 多模态助手！\n\n"
            "✨ 支持的功能：\n"
            "📄 文档理解：PDF、TXT、Markdown、HTML\n"
            "🖼️ 图片分析：JPG、PNG、WebP、HEIC等\n"
            "🎥 视频理解：MP4、AVI、MOV、WebM等\n"
            "🎵 音频分析：MP3、WAV、AAC、FLAC等\n"
            "🔗 URL采集：支持网页、YouTube、直链文件\n\n"
            "💡 使用提示：\n"
            "• 点击「📎 文件/URL」按钮上传文件或输入URL\n"
            "• 支持拖拽文件到输入区域\n"
            "• 可同时上传多个文件进行对比分析\n"
            "• 使用 Ctrl+Enter 快速发送消息"
        )
        
        self.add_message("assistant", welcome_text, show_files=False)
    
    def send_message_with_files(self, message_text: str, processed_files: List[ProcessedFile]):
        """发送带文件的消息"""
        if not message_text.strip() and not processed_files:
            return
        
        # 禁用输入
        self.chat_input.set_enabled(False)
        
        # 显示用户消息
        self.add_user_message(message_text, processed_files)
        
        # 准备发送消息
        print(f"准备发送消息: '{message_text}', 文件数量: {len(processed_files)}")
        
        # 根据用户设置决定是否使用流式回复
        use_streaming = self.user_settings.enable_streaming
        print(f"使用流式回复: {use_streaming}")
        
        # 添加小延迟以确保服务完全初始化（特别是对新会话）
        QTimer.singleShot(100, lambda: self._send_message_delayed(message_text, processed_files, use_streaming))
        
    def _send_message_delayed(self, message_text: str, processed_files: List[ProcessedFile], use_streaming: bool):
        """延迟发送消息，确保服务初始化完成"""
        # 创建并启动异步工作线程
        self.current_worker = MultimodalAsyncWorker(
            self.gemini_service,
            message_text,
            self.conversation,
            processed_files,
            streaming=use_streaming,
            api_key=self.api_key
        )
        
        # 连接信号
        if use_streaming:
            self.current_worker.stream_chunk.connect(self.on_stream_chunk)
        else:
            self.current_worker.response_received.connect(self.on_response_received)
        self.current_worker.error_occurred.connect(self.on_error_occurred)
        self.current_worker.finished.connect(self.on_worker_finished)  # 添加finished信号连接
        
        # 准备接收响应
        if use_streaming:
            self.current_response_parts = []
            self.current_assistant_widget = None
        
        self.current_worker.start()
    
    def add_user_message(self, message_text: str, processed_files: List[ProcessedFile]):
        """添加用户消息"""
        # 构建消息内容
        content_parts = []
        
        if message_text.strip():
            content_parts.append(message_text)
        
        if processed_files:
            files_info = []
            for f in processed_files:
                file_info = f"📎 {f.original_name}"
                if f.metadata and f.metadata.get('source_url'):
                    file_info += f" (来自URL)"
                files_info.append(file_info)
            content_parts.append("\n".join(files_info))
        
        full_content = "\n\n".join(content_parts) if len(content_parts) > 1 else (content_parts[0] if content_parts else "")
        
        self.add_message("user", full_content, show_files=len(processed_files) > 0)
    
    def add_message(self, sender: str, content: str, show_files: bool = False):
        """添加消息到聊天显示 - 改进版本，支持加载状态和优化渲染"""
        # 1. 创建消息widget（优化性能）
        message_widget = self.create_message_widget(sender, content, show_files)
        
        # 2. 使用批量插入避免频繁重绘
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message_widget)
        
        # 3. 延迟滚动到底部，避免频繁滚动
        self._schedule_scroll_to_bottom()
        
        return message_widget
    
    def _schedule_scroll_to_bottom(self):
        """调度滚动到底部 - 避免频繁滚动"""
        if not hasattr(self, '_scroll_timer'):
            from PySide6.QtCore import QTimer
            self._scroll_timer = QTimer()
            self._scroll_timer.timeout.connect(self.scroll_to_bottom)
            self._scroll_timer.setSingleShot(True)
        
        # 重启定时器
        self._scroll_timer.start(100)  # 100ms延迟
    
    def create_message_widget(self, sender: str, content: str, show_files: bool = False) -> QWidget:
        """创建消息widget"""
        container = QFrame()
        
        if sender == "user":
            container.setStyleSheet("""
                QFrame {
                    background-color: #007ACC;
                    color: white;
                    border-radius: 10px;
                    padding: 10px;
                    margin-left: 50px;
                    margin-right: 10px;
                    margin-bottom: 5px;
                }
            """)
        else:  # assistant
            container.setStyleSheet("""
                QFrame {
                    background-color: #f0f0f0;
                    color: black;
                    border-radius: 10px;
                    padding: 10px;
                    margin-left: 10px;
                    margin-right: 50px;
                    margin-bottom: 5px;
                }
            """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 发送者标签
        sender_label = QLabel("👤 您" if sender == "user" else "🤖 Gemini")
        sender_font = QFont()
        sender_font.setBold(True)
        sender_font.setPointSize(10)
        sender_label.setFont(sender_font)
        
        if sender == "user":
            sender_label.setStyleSheet("color: #cce6ff;")
        else:
            sender_label.setStyleSheet("color: #666;")
        
        layout.addWidget(sender_label)
        
        # 消息内容
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        content_font = QFont()
        content_font.setPointSize(11)
        content_label.setFont(content_font)
        
        layout.addWidget(content_label)
        
        # 时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_label = QLabel(timestamp)
        time_label.setStyleSheet("font-size: 10px; color: #888; margin-top: 5px;")
        layout.addWidget(time_label)
        
        return container
    
    def on_stream_chunk(self, chunk: str):
        """处理流式响应块"""
        self.current_response_parts.append(chunk)
        
        # 如果还没有助手消息widget，创建一个
        if self.current_assistant_widget is None:
            self.current_assistant_widget = self.add_message("assistant", "", show_files=False)
        
        # 更新消息内容
        full_content = "".join(self.current_response_parts)
        self.update_message_content(self.current_assistant_widget, full_content)
        
        # 滚动到底部
        self.scroll_to_bottom()
    
    def update_message_content(self, message_widget: QWidget, content: str):
        """更新消息内容"""
        # 找到内容标签并更新
        layout = message_widget.layout()
        if layout and layout.count() >= 2:
            item = layout.itemAt(1)
            if item:
                content_label = item.widget()
                if isinstance(content_label, QLabel):
                    content_label.setText(content)
    
    def on_response_received(self, response: str):
        """处理完整响应（非流式模式）"""
        print(f"收到完整响应: {len(response)} 字符")
        
        # 直接显示完整回复
        self.add_message("assistant", response)
        
        # 重新启用输入
        self.chat_input.set_enabled(True)
        
        # 清理工作线程
        self.current_worker = None
    
    def on_error_occurred(self, error: str):
        """处理错误"""
        print(f"发生错误: {error}")
        
        # 显示错误消息
        error_message = f"❌ 抱歉，发生了错误：\n{error}\n\n请检查网络连接或API配置。"
        self.add_message("assistant", error_message)
        
        # 重新启用输入
        self.chat_input.set_enabled(True)
        
        # 清理工作线程
        self.current_worker = None
        self.current_response_parts = []
        self.current_assistant_widget = None
    
    def on_worker_finished(self):
        """处理工作线程完成"""
        print("工作线程已完成")
        
        # 重新启用输入组件
        self.chat_input.set_enabled(True)
        
        # 清理工作线程和状态
        self.current_worker = None
        if hasattr(self, 'current_response_parts'):
            self.current_response_parts = []
        if hasattr(self, 'current_assistant_widget'):
            self.current_assistant_widget = None
    
    def scroll_to_bottom(self):
        """滚动到底部"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def get_conversation(self) -> Conversation:
        """获取当前对话"""
        return self.conversation
    
    def clear_conversation(self):
        """清空对话内容 - 优化版本，支持加载状态"""
        # 1. 显示清理状态（可选）
        self._show_clearing_state()
        
        # 2. 清空对话历史
        self.conversation = Conversation()
        
        # 3. 批量删除，避免逐个删除造成的性能问题
        self._clear_messages_batch()
        
        # 4. 重置状态
        self._reset_conversation_state()
        
        # 5. 隐藏清理状态
        self._hide_clearing_state()
    
    def _show_clearing_state(self):
        """显示清理状态"""
        # 可以在这里显示loading状态
        pass
        
    def _hide_clearing_state(self):
        """隐藏清理状态"""
        # 隐藏loading状态
        pass
        
    def _clear_messages_batch(self):
        """批量清理消息"""
        # 批量删除所有消息widget（保留弹簧）
        widgets_to_remove = []
        while self.chat_layout.count() > 1:  # 保留弹簧
            child = self.chat_layout.takeAt(0)
            if child and child.widget():
                widgets_to_remove.append(child.widget())
                
        # 批量删除
        for widget in widgets_to_remove:
            widget.deleteLater()
            
    def _reset_conversation_state(self):
        """重置对话状态"""
        # 重置流式消息状态
        if hasattr(self, 'current_assistant_widget'):
            self.current_assistant_widget = None
        if hasattr(self, 'is_streaming'):
            self.is_streaming = False
        if hasattr(self, 'current_response_parts'):
            self.current_response_parts = []
            
        # 重置滚动定时器
        if hasattr(self, '_scroll_timer'):
            self._scroll_timer.stop()
        
        # 添加欢迎消息
        self.add_welcome_message()
        
        # 清空输入区域的文件
        self.chat_input.clear_files()


if __name__ == "__main__":
    pass
