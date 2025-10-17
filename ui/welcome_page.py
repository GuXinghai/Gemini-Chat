# ui/welcome_page.py
# 欢迎页面组件

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from pathlib import Path
from typing import List, Optional

from .ui_config import get_safe_font


class WelcomeCard(QFrame):
    """欢迎卡片组件"""
    
    clicked = Signal()
    
    def __init__(self, title: str, description: str, icon_path: Optional[str] = None):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            WelcomeCard {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: #f9f9f9;
                margin: 4px;
            }
            WelcomeCard:hover {
                border-color: #4285f4;
                background-color: #f0f7ff;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(280, 120)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        
        # 标题
        title_label = QLabel(title)
        title_label.setFont(get_safe_font(size=14, bold=True))
        title_label.setStyleSheet("color: #1a1a1a;")
        layout.addWidget(title_label)
        
        # 描述
        desc_label = QLabel(description)
        desc_label.setFont(get_safe_font(size=11))
        desc_label.setStyleSheet("color: #666666;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class RecentChatItem(QWidget):
    """最近聊天项目组件"""
    
    clicked = Signal(str)  # 发送chat_id
    
    def __init__(self, chat_id: str, title: str, preview: str, time: str):
        super().__init__()
        self.chat_id = chat_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            RecentChatItem {
                border-radius: 6px;
                padding: 8px;
                background-color: #fafafa;
            }
            RecentChatItem:hover {
                background-color: #e8f0fe;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title or "未命名会话")
        title_label.setFont(get_safe_font(size=12, bold=True))
        title_label.setStyleSheet("color: #1a1a1a;")
        title_layout.addWidget(title_label)
        
        time_label = QLabel(time)
        time_label.setFont(get_safe_font(size=10))
        time_label.setStyleSheet("color: #888888;")
        title_layout.addWidget(time_label)
        
        layout.addLayout(title_layout)
        
        # 预览文本
        if preview:
            preview_label = QLabel(preview)
            preview_label.setFont(get_safe_font(size=10))
            preview_label.setStyleSheet("color: #666666;")
            preview_label.setWordWrap(True)
            preview_label.setMaximumHeight(40)
            layout.addWidget(preview_label)
        
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.chat_id)
        super().mousePressEvent(event)


class WelcomePage(QWidget):
    """欢迎页面"""
    
    new_chat_requested = Signal()
    open_chat_requested = Signal(str)  # chat_id
    import_requested = Signal()
    settings_requested = Signal()
    
    def __init__(self, history_service=None):
        super().__init__()
        self.history_service = history_service
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # 顶部欢迎区域
        welcome_layout = QVBoxLayout()
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 标题
        title_label = QLabel("欢迎使用 Gemini Chat")
        title_label.setFont(get_safe_font(size=28, bold=True))
        title_label.setStyleSheet("color: #1a1a1a; margin-bottom: 8px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("开始新的对话，或继续之前的讨论")
        subtitle_label.setFont(get_safe_font(size=14))
        subtitle_label.setStyleSheet("color: #666666; margin-bottom: 20px;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(subtitle_label)
        
        layout.addLayout(welcome_layout)
        
        # 快速操作卡片
        cards_layout = QHBoxLayout()
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 新建聊天卡片
        new_chat_card = WelcomeCard(
            "新建聊天",
            "开始一个全新的AI对话"
        )
        new_chat_card.clicked.connect(self.new_chat_requested.emit)
        cards_layout.addWidget(new_chat_card)
        
        # 导入聊天卡片
        import_card = WelcomeCard(
            "导入聊天",
            "从文件导入之前的对话记录"
        )
        import_card.clicked.connect(self.import_requested.emit)
        cards_layout.addWidget(import_card)
        
        # 设置卡片
        settings_card = WelcomeCard(
            "设置",
            "配置AI模型和聊天偏好"
        )
        settings_card.clicked.connect(self.settings_requested.emit)
        cards_layout.addWidget(settings_card)
        
        layout.addLayout(cards_layout)
        
        # 最近聊天区域
        recent_frame = QFrame()
        recent_frame.setFrameStyle(QFrame.Shape.Box)
        recent_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                padding: 16px;
            }
        """)
        
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(16, 16, 16, 16)
        
        recent_title = QLabel("最近的对话")
        recent_title.setFont(get_safe_font(size=16, bold=True))
        recent_title.setStyleSheet("color: #1a1a1a; margin-bottom: 12px;")
        recent_layout.addWidget(recent_title)
        
        # 最近聊天列表
        self.recent_scroll = QScrollArea()
        self.recent_scroll.setWidgetResizable(True)
        self.recent_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.recent_widget = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_widget)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(6)
        
        self.recent_scroll.setWidget(self.recent_widget)
        recent_layout.addWidget(self.recent_scroll)
        
        layout.addWidget(recent_frame)
        
        self.setLayout(layout)
        
        # 加载最近聊天
        self.load_recent_chats()
    
    def load_recent_chats(self):
        """加载最近聊天记录"""
        # 清除现有项目
        while self.recent_layout.count():
            child = self.recent_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not self.history_service:
            no_chats_label = QLabel("暂无聊天记录")
            no_chats_label.setFont(get_safe_font(size=12))
            no_chats_label.setStyleSheet("color: #888888; text-align: center; padding: 20px;")
            no_chats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.recent_layout.addWidget(no_chats_label)
            return
        
        try:
            # 获取最近的聊天记录（限制数量）
            recent_chats = self.get_recent_chats(limit=8)
            
            if not recent_chats:
                no_chats_label = QLabel("暂无聊天记录，点击上方\"新建聊天\"开始使用")
                no_chats_label.setFont(get_safe_font(size=12))
                no_chats_label.setStyleSheet("color: #888888; text-align: center; padding: 20px;")
                no_chats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.recent_layout.addWidget(no_chats_label)
                return
            
            for chat_data in recent_chats:
                chat_id = chat_data.get('id', '')
                title = chat_data.get('title', '未命名会话')[:50]
                
                # 获取预览文本（第一条消息的开头）
                preview = ""
                messages = chat_data.get('messages', [])
                if messages:
                    first_msg = messages[0]
                    if isinstance(first_msg, dict) and 'content' in first_msg:
                        preview = first_msg['content'][:100] + "..." if len(first_msg['content']) > 100 else first_msg['content']
                
                # 格式化时间
                time_str = self.format_time(chat_data.get('updated_at', ''))
                
                # 创建项目
                item = RecentChatItem(chat_id, title, preview, time_str)
                item.clicked.connect(self.open_chat_requested.emit)
                self.recent_layout.addWidget(item)
            
            # 添加弹性空间
            self.recent_layout.addStretch()
            
        except Exception as e:
            print(f"加载最近聊天失败: {e}")
            error_label = QLabel("加载聊天记录失败")
            error_label.setFont(get_safe_font(size=12))
            error_label.setStyleSheet("color: #d32f2f; text-align: center; padding: 20px;")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.recent_layout.addWidget(error_label)
    
    def get_recent_chats(self, limit: int = 8) -> List[dict]:
        """获取最近聊天记录"""
        try:
            if self.history_service and hasattr(self.history_service, 'get_recent_conversations'):
                return self.history_service.get_recent_conversations(limit)
            elif self.history_service and hasattr(self.history_service, 'get_all_conversations'):
                all_chats = self.history_service.get_all_conversations()
                # 按更新时间排序并限制数量
                sorted_chats = sorted(all_chats, key=lambda x: x.get('updated_at', ''), reverse=True)
                return sorted_chats[:limit]
            else:
                # 尝试直接从历史目录读取
                return self._load_from_directory(limit)
        except Exception as e:
            print(f"获取最近聊天失败: {e}")
            return []
    
    def _load_from_directory(self, limit: int) -> List[dict]:
        """从目录直接加载聊天文件"""
        try:
            from pathlib import Path
            import json
            
            # 尝试从多个可能的位置获取历史目录
            history_dir = None
            try:
                from geminichat.config.secrets import Config
                if hasattr(Config, 'CHAT_HISTORY_DIR'):
                    history_dir = Path(Config.CHAT_HISTORY_DIR)
            except:
                pass
            
            if not history_dir:
                # 使用默认路径
                history_dir = Path.cwd() / "geminichat" / "chat_history"
            
            if not history_dir.exists():
                return []
            
            chat_files = []
            for file_path in history_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        chat_data = json.load(f)
                        # 只显示持久化的聊天（排除空的临时会话）
                        if not chat_data.get('is_ephemeral', False) or chat_data.get('messages', []):
                            chat_files.append(chat_data)
                except Exception as e:
                    print(f"加载聊天文件失败 {file_path}: {e}")
            
            # 按更新时间排序
            chat_files.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            return chat_files[:limit]
        except Exception as e:
            print(f"从目录加载聊天失败: {e}")
            return []
    
    def format_time(self, time_str: str) -> str:
        """格式化时间显示"""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            now = datetime.now(dt.tzinfo if dt.tzinfo else None)
            
            diff = now - dt
            
            if diff.days == 0:
                if diff.seconds < 3600:  # 1小时内
                    minutes = diff.seconds // 60
                    return f"{minutes}分钟前" if minutes > 0 else "刚刚"
                else:
                    hours = diff.seconds // 3600
                    return f"{hours}小时前"
            elif diff.days == 1:
                return "昨天"
            elif diff.days < 7:
                return f"{diff.days}天前"
            else:
                return dt.strftime("%m-%d")
        except Exception:
            return "未知时间"
    
    def refresh(self):
        """刷新页面内容"""
        self.load_recent_chats()
