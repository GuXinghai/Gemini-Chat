"""
增强聊天输入组件
集成多模态文件上传功能，支持拖拽/选择/URL采集
"""
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTextEdit, QLabel, QSplitter, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShortcut, QKeySequence, QKeyEvent

# 添加项目根目录到路径
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir))

from services.file_upload_service import ProcessedFile
from ui.file_upload_widget import EnhancedFileUploadWidget


class MessageTextEdit(QTextEdit):
    """自定义文本编辑器，支持Enter发送消息"""
    
    send_message_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def keyPressEvent(self, event: QKeyEvent):
        """处理按键事件"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # 检查是否按住了Shift键
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter：插入换行
                super().keyPressEvent(event)
            else:
                # Enter：发送消息
                self.send_message_requested.emit()
                event.accept()  # 阻止默认行为（插入换行）
        else:
            # 其他按键正常处理
            super().keyPressEvent(event)


class EnhancedChatInput(QWidget):
    """增强聊天输入组件，支持多模态文件上传"""
    
    send_message = Signal(str, list)  # 消息内容, ProcessedFile列表
    
    def __init__(self, api_key: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.processed_files: List[ProcessedFile] = []
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建可收缩的上传区域
        self.create_upload_section(layout)
        
        # 创建文本输入区域
        self.create_input_section(layout)
        
    def create_upload_section(self, parent_layout: QVBoxLayout):
        """创建文件上传区域"""
        # 文件上传切换按钮
        toggle_layout = QHBoxLayout()
        
        self.toggle_upload_btn = QPushButton("📎 文件/URL")
        self.toggle_upload_btn.setCheckable(True)
        self.toggle_upload_btn.setMaximumWidth(100)
        self.toggle_upload_btn.setToolTip("显示/隐藏文件上传区域")
        
        self.file_count_label = QLabel("无文件")
        self.file_count_label.setStyleSheet("color: #666; font-size: 12px;")
        
        toggle_layout.addWidget(self.toggle_upload_btn)
        toggle_layout.addWidget(self.file_count_label)
        toggle_layout.addStretch()
        
        parent_layout.addLayout(toggle_layout)
        
        # 文件上传组件（可收缩）
        self.upload_widget = EnhancedFileUploadWidget(self.api_key, self)
        self.upload_widget.setVisible(False)  # 初始隐藏
        self.upload_widget.setMaximumHeight(300)
        
        parent_layout.addWidget(self.upload_widget)
    
    def create_input_section(self, parent_layout: QVBoxLayout):
        """创建文本输入区域"""
        input_layout = QHBoxLayout()
        
        # 文本输入框
        self.text_edit = MessageTextEdit()
        self.text_edit.setPlaceholderText(
            "请输入消息...\n\n"
            "提示：\n"
            "• Enter 发送消息，Shift+Enter 换行\n" 
            "• 点击上方按钮上传文件或输入URL\n"
            "• 支持拖拽文件到此区域"
        )
        self.text_edit.setMaximumHeight(120)
        self.text_edit.setMinimumHeight(80)
        
        # 发送按钮
        self.send_btn = QPushButton("发送")
        self.send_btn.setMaximumWidth(80)
        self.send_btn.setMinimumHeight(40)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)
        
        input_layout.addWidget(self.text_edit, 1)
        input_layout.addWidget(self.send_btn, 0)
        
        parent_layout.addLayout(input_layout)
    
    def connect_signals(self):
        """连接信号"""
        # 文件上传切换
        self.toggle_upload_btn.clicked.connect(self.toggle_upload_area)
        
        # 文件上传完成
        self.upload_widget.files_processed.connect(self.on_files_processed)
        
        # 发送按钮和快捷键
        self.send_btn.clicked.connect(self.send_current_message)
        
        # Enter键发送消息
        self.text_edit.send_message_requested.connect(self.send_current_message)
        
        # Ctrl+Enter 快捷键（保留作为备选）
        send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.text_edit)
        send_shortcut.activated.connect(self.send_current_message)
        
        # 文本变化时更新发送按钮状态
        self.text_edit.textChanged.connect(self.update_send_button)
        
        # 支持拖拽到文本框
        self.text_edit.setAcceptDrops(True)
        self.text_edit.dragEnterEvent = self.drag_enter_event
        self.text_edit.dropEvent = self.drop_event
    
    def toggle_upload_area(self):
        """切换上传区域显示/隐藏"""
        is_visible = self.upload_widget.isVisible()
        self.upload_widget.setVisible(not is_visible)
        
        # 更新按钮状态
        self.toggle_upload_btn.setChecked(not is_visible)
        
        if not is_visible:
            # 显示时聚焦到上传区域
            self.toggle_upload_btn.setText("📎 收起")
        else:
            self.toggle_upload_btn.setText("📎 文件/URL")
    
    def on_files_processed(self, processed_files: List[ProcessedFile]):
        """文件处理完成"""
        self.processed_files = processed_files
        self.update_file_count_display()
    
    def update_file_count_display(self):
        """更新文件数量显示"""
        count = len(self.processed_files)
        if count == 0:
            self.file_count_label.setText("无文件")
            self.file_count_label.setStyleSheet("color: #666; font-size: 12px;")
        else:
            total_size = sum(f.file_size for f in self.processed_files)
            size_mb = total_size / 1024 / 1024
            
            # 统计类型
            type_counts = {}
            for f in self.processed_files:
                type_name = f.attachment_type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            # 构建显示文本
            type_text = []
            type_icons = {
                'DOCUMENT': '📄',
                'IMAGE': '🖼️', 
                'VIDEO': '🎥',
                'AUDIO': '🎵',
                'OTHER': '📎'
            }
            
            for type_name, type_count in type_counts.items():
                icon = type_icons.get(type_name, '📎')
                type_text.append(f"{icon}{type_count}")
            
            display_text = f"{count}个文件 ({size_mb:.1f}MB) - {' '.join(type_text)}"
            self.file_count_label.setText(display_text)
            self.file_count_label.setStyleSheet("color: #007ACC; font-size: 12px; font-weight: bold;")
    
    def update_send_button(self):
        """更新发送按钮状态"""
        has_text = bool(self.text_edit.toPlainText().strip())
        has_files = len(self.processed_files) > 0
        
        # 有文本或文件时才能发送
        self.send_btn.setEnabled(has_text or has_files)
        
        # 更新按钮文本
        if has_files and has_text:
            self.send_btn.setText("发送\n(含文件)")
        elif has_files:
            self.send_btn.setText("发送文件")
        else:
            self.send_btn.setText("发送")
    
    def drag_enter_event(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # 如果拖拽文件到文本框，自动显示上传区域
            if not self.upload_widget.isVisible():
                self.toggle_upload_area()
    
    def drop_event(self, event):
        """拖拽放下事件"""
        if event.mimeData().hasUrls():
            # 转发到上传组件处理
            if not self.upload_widget.isVisible():
                self.toggle_upload_area()
            
            # 模拟拖拽到上传区域
            self.upload_widget.dropEvent(event)
            
            # 阻止文本框处理该事件
            event.acceptProposedAction()
            return
        
        # 对于其他内容，让文本框正常处理
        super().dropEvent(event)
    
    def send_current_message(self):
        """发送当前消息"""
        message_text = self.text_edit.toPlainText().strip()
        
        # 检查是否有内容可发送
        if not message_text and not self.processed_files:
            return
        
        # 发出信号
        self.send_message.emit(message_text, self.processed_files.copy())
        
        # 清空输入
        self.clear_input()
    
    def clear_input(self):
        """清空输入内容"""
        self.text_edit.clear()
        # 注意：不清空文件，让用户手动控制
    
    def clear_files(self):
        """清空文件"""
        self.upload_widget.clear_all_files()
        self.processed_files.clear()
        self.update_file_count_display()
        self.update_send_button()
    
    def set_enabled(self, enabled: bool):
        """设置启用状态"""
        self.text_edit.setEnabled(enabled)
        
        if enabled:
            has_content = bool(self.text_edit.toPlainText().strip() or self.processed_files)
            self.send_btn.setEnabled(has_content)
        else:
            self.send_btn.setEnabled(False)
            
        self.toggle_upload_btn.setEnabled(enabled)
        self.upload_widget.setEnabled(enabled)
    
    def get_processed_files(self) -> List[ProcessedFile]:
        """获取已处理的文件列表"""
        return self.processed_files.copy()
    
    def get_gemini_parts(self) -> List:
        """获取用于Gemini API的内容部分"""
        return self.upload_widget.get_gemini_parts()
