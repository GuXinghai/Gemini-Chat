# services/startup_manager.py
# 启动管理器 - 协调应用启动流程

import sys
import logging
from typing import Optional, List
from pathlib import Path

from geminichat.domain.app_state import AppStateManager, PayloadParser, Payload, AppState, AppStateType
from geminichat.domain.conversation import Conversation
from services.persistency_manager import PersistencyManager

logger = logging.getLogger(__name__)


class StartupManager:
    """启动管理器"""
    
    def __init__(self, history_service, settings_service=None):
        self.history_service = history_service
        self.settings_service = settings_service
        self.state_manager = AppStateManager()
        self.persistency_manager = PersistencyManager(history_service)
    
    def determine_startup_state(self) -> AppState:
        """
        确定应用启动状态
        
        实现伪逻辑中的启动流程：
        Event: AppStart
        Inputs:
          incoming_payload: Optional[Payload] // 文件、URL、命令行参数等
          last_active_chat_id: Optional[UUID] // 上次活动会话

        Guard & Transition:
          IF incoming_payload exists:
               -> Action A1: create_new_chat(ephemeral=true, prefill=incoming_payload)
               -> Action A2: ensure_persistency_if_content()   // 若预填即持久
               -> Next: ChatView(new_chat_id)
          ELSE IF last_active_chat_id exists:
               -> Action A3: open_chat(last_active_chat_id)
               -> Next: ChatView(last_active_chat_id)
          ELSE
               -> Next: Welcome
        """
        # 解析命令行参数
        incoming_payload = self._parse_command_line_args()
        
        # 获取最近活动的会话ID
        last_active_chat_id = self._get_last_active_chat_id()
        
        # 生成启动状态
        startup_state = self.state_manager.get_startup_state(
            incoming_payload=incoming_payload,
            last_active_chat_id=last_active_chat_id
        )
        
        logger.info(f"启动状态: {startup_state.type}")
        if startup_state.payload:
            logger.info(f"检测到外部负载: {startup_state.payload.type} - {startup_state.payload.source}")
        if startup_state.current_chat_id:
            logger.info(f"恢复会话: {startup_state.current_chat_id}")
        
        return startup_state
    
    def create_chat_with_payload(self, payload: Payload) -> Conversation:
        """
        使用负载创建新会话
        
        Action A1: create_new_chat(ephemeral=true, prefill=incoming_payload)
        Action A2: ensure_persistency_if_content()   // 若预填即持久
        """
        # 创建新的临时会话
        conversation = Conversation(
            title="",  # 初始空标题
            is_ephemeral=True
        )
        
        # 预填充内容
        self._prefill_conversation(conversation, payload)
        
        # 如果有内容，立即转为持久化
        if self.persistency_manager.ensure_persistency_if_content(conversation):
            logger.info(f"会话 {conversation.id} 因预填充内容而转为持久状态")
        
        return conversation
    
    def load_existing_chat(self, chat_id: str) -> Optional[Conversation]:
        """
        加载现有会话
        
        Action A3: open_chat(last_active_chat_id)
        """
        try:
            if hasattr(self.history_service, 'load'):
                return self.history_service.load(chat_id)
            elif hasattr(self.history_service, 'get_conversation'):
                return self.history_service.get_conversation(chat_id)
            else:
                # 直接从文件加载
                return self._load_chat_from_file(chat_id)
        except Exception as e:
            logger.error(f"加载会话失败 {chat_id}: {e}")
            return None
    
    def handle_external_payload_during_runtime(self, payload: Payload, 
                                             current_state: AppState, 
                                             current_chat: Optional[Conversation]) -> tuple[bool, Optional[Conversation]]:
        """
        运行时处理外部负载
        
        Event: ExternalPayload(payload)
        CurrentState:
          - ChatView(current_chat) OR Welcome

        Guard & Transition:
          IF CurrentState == ChatView AND current_chat.is_ephemeral==true AND current_chat is empty:
               -> Action C1: prefill(current_chat, payload)
               -> Action C2: ensure_persistency_if_content(current_chat) // 预填即落盘
               -> Stay: ChatView(current_chat)
          ELSE:
               -> Action C3: create_new_chat(ephemeral=true, prefill=payload)
               -> Action C4: ensure_persistency_if_content(new_chat)
               -> Next: ChatView(new_chat_id)
               
        返回: (是否需要新建会话, 要使用的会话对象)
        """
        should_create_new = self.state_manager.should_create_new_chat_for_payload(
            current_state, current_chat, payload
        )
        
        if not should_create_new and current_chat:
            # 复用当前空会话
            self._prefill_conversation(current_chat, payload)
            if self.persistency_manager.ensure_persistency_if_content(current_chat):
                logger.info(f"会话 {current_chat.id} 因外部负载而转为持久状态")
            return False, current_chat
        else:
            # 创建新会话
            new_chat = self.create_chat_with_payload(payload)
            return True, new_chat
    
    def _parse_command_line_args(self) -> Optional[Payload]:
        """解析命令行参数"""
        return PayloadParser.parse_command_args(sys.argv)
    
    def _get_last_active_chat_id(self) -> Optional[str]:
        """获取最近活跃的会话ID"""
        try:
            if self.settings_service and hasattr(self.settings_service, 'get_last_active_chat'):
                return self.settings_service.get_last_active_chat()
            else:
                # 从历史记录中获取最近的会话
                return self._get_most_recent_chat_id()
        except Exception as e:
            logger.error(f"获取最近活跃会话失败: {e}")
            return None
    
    def _get_most_recent_chat_id(self) -> Optional[str]:
        """从历史记录中获取最近的会话ID"""
        try:
            # 尝试多种方式获取最近会话
            if hasattr(self.history_service, 'get_recent_conversations'):
                recent = self.history_service.get_recent_conversations(1)
                if recent:
                    return recent[0].get('id')
            elif hasattr(self.history_service, 'get_all_conversations'):
                all_convs = self.history_service.get_all_conversations()
                if all_convs:
                    # 按更新时间排序
                    sorted_convs = sorted(all_convs, key=lambda x: x.get('updated_at', ''), reverse=True)
                    return sorted_convs[0].get('id')
            
            # 直接从文件系统获取
            return self._get_most_recent_from_filesystem()
        except Exception as e:
            logger.error(f"获取最近会话ID失败: {e}")
            return None
    
    def _get_most_recent_from_filesystem(self) -> Optional[str]:
        """从文件系统获取最近的会话ID"""
        try:
            from geminichat.config.secrets import Config
            import json
            
            history_dir = Path(Config.CHAT_HISTORY_DIR)
            if not history_dir.exists():
                return None
            
            chat_files = []
            for file_path in history_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        chat_data = json.load(f)
                        # 只考虑持久化的非空会话
                        if (not chat_data.get('is_ephemeral', False) and 
                            chat_data.get('messages', [])):
                            chat_files.append((file_path.stat().st_mtime, chat_data.get('id')))
                except Exception:
                    continue
            
            if chat_files:
                # 按修改时间排序，返回最新的
                chat_files.sort(reverse=True)
                return chat_files[0][1]
        except Exception as e:
            logger.error(f"从文件系统获取最近会话失败: {e}")
        
        return None
    
    def _load_chat_from_file(self, chat_id: str) -> Optional[Conversation]:
        """直接从文件加载会话"""
        try:
            from geminichat.config.secrets import Config
            import json
            
            file_path = Path(Config.CHAT_HISTORY_DIR) / f"{chat_id}.json"
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
                return Conversation.from_dict(chat_data)
        except Exception as e:
            logger.error(f"从文件加载会话失败 {chat_id}: {e}")
            return None
    
    def _prefill_conversation(self, conversation: Conversation, payload: Payload):
        """预填充会话内容"""
        try:
            if payload.type == "file":
                self._prefill_file_content(conversation, payload)
            elif payload.type == "url":
                self._prefill_url_content(conversation, payload)
            elif payload.type == "text":
                self._prefill_text_content(conversation, payload)
            else:
                logger.warning(f"不支持的负载类型: {payload.type}")
        except Exception as e:
            logger.error(f"预填充会话内容失败: {e}")
    
    def _prefill_file_content(self, conversation: Conversation, payload: Payload):
        """预填充文件内容"""
        from geminichat.domain.message import Message, MessageRole
        from geminichat.domain.attachment import Attachment, AttachmentType
        from datetime import datetime
        import os
        import uuid
        
        file_path = payload.source
        if not Path(file_path).exists():
            logger.warning(f"文件不存在: {file_path}")
            return
        
        # 创建附件
        try:
            file_stat = os.stat(file_path)
            attachment = Attachment(
                id=f"attach_{uuid.uuid4()}",
                file_path=file_path,
                original_name=Path(file_path).name,
                file_size=file_stat.st_size,
                mime_type=self._guess_mime_type(file_path),
                attachment_type=self._guess_attachment_type(file_path),
                uploaded_at=datetime.now()
            )
            conversation.add_attachment(attachment)
            
            # 添加用户消息
            message_content = f"请帮我分析这个文件: {Path(file_path).name}"
            message = Message(
                id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content=message_content,
                timestamp=datetime.now()
            )
            conversation.add_message(message)
            
            # 设置标题
            if not conversation.title:
                conversation.title = f"分析文件: {Path(file_path).name}"
                
        except Exception as e:
            logger.error(f"处理文件附件失败: {e}")
    
    def _prefill_url_content(self, conversation: Conversation, payload: Payload):
        """预填充URL内容"""
        from geminichat.domain.message import Message, MessageRole
        from datetime import datetime
        import uuid
        
        url = payload.source
        message_content = f"请帮我分析这个网页: {url}"
        
        message = Message(
            id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content=message_content,
            timestamp=datetime.now()
        )
        conversation.add_message(message)
        
        # 设置标题
        if not conversation.title:
            conversation.title = f"分析网页: {url[:50]}..."
    
    def _prefill_text_content(self, conversation: Conversation, payload: Payload):
        """预填充文本内容"""
        from geminichat.domain.message import Message, MessageRole
        from datetime import datetime
        import uuid
        
        text = payload.source
        message = Message(
            id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content=text,
            timestamp=datetime.now()
        )
        conversation.add_message(message)
        
        # 设置标题
        if not conversation.title:
            conversation.title = text[:50] + "..." if len(text) > 50 else text
    
    def _guess_mime_type(self, file_path: str) -> str:
        """猜测文件MIME类型"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"
    
    def _guess_attachment_type(self, file_path: str):
        """猜测附件类型"""
        from geminichat.domain.attachment import AttachmentType
        
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            return AttachmentType.IMAGE
        elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
            return AttachmentType.VIDEO
        elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
            return AttachmentType.AUDIO
        elif ext in ['.py', '.js', '.html', '.css', '.cpp', '.java', '.go', '.rs']:
            return AttachmentType.CODE
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.md', '.rtf']:
            return AttachmentType.DOCUMENT
        else:
            return AttachmentType.OTHER
