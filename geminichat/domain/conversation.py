# domain/conversation.py
# 定义 Conversation 实体，表示一次完整会话

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid
from .message import Message
from .attachment import Attachment


@dataclass
class Conversation:
    """会话实体"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    is_ephemeral: bool = True  # 默认为临时会话
    
    def add_message(self, message: Message) -> None:
        """添加消息到会话"""
        self.messages.append(message)
        self.updated_at = datetime.now()
        
        # 如果没有标题，用第一条用户消息的内容作为标题
        if not self.title and message.role.value == "user":
            self.title = message.content[:50] + "..." if len(message.content) > 50 else message.content
        
        # 有内容时自动转为持久化
        if self.is_ephemeral and self.has_content():
            self.is_ephemeral = False
    
    def add_attachment(self, attachment: Attachment) -> None:
        """添加附件到会话"""
        self.attachments.append(attachment)
        self.updated_at = datetime.now()
        
        # 有附件时自动转为持久化
        if self.is_ephemeral:
            self.is_ephemeral = False
    
    def has_content(self) -> bool:
        """判断会话是否有内容（消息或附件）"""
        return len(self.messages) > 0 or len(self.attachments) > 0
    
    def is_empty_ephemeral(self) -> bool:
        """判断是否为空的临时会话"""
        return self.is_ephemeral and not self.has_content()
    
    def ensure_persistency_if_content(self) -> bool:
        """如果有内容则确保持久化，返回是否发生了改变"""
        if self.is_ephemeral and self.has_content():
            self.is_ephemeral = False
            return True
        return False
    
    def get_messages_by_role(self, role: str) -> List[Message]:
        """根据角色获取消息"""
        return [msg for msg in self.messages if msg.role.value == role]
    
    def get_last_message(self) -> Optional[Message]:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages],
            "attachments": [att.to_dict() if hasattr(att, 'to_dict') else str(att) for att in self.attachments],
            "metadata": self.metadata,
            "is_ephemeral": self.is_ephemeral
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """从字典创建会话实例"""
        conversation = cls(
            id=data["id"],
            title=data.get("title", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
            is_ephemeral=data.get("is_ephemeral", False)  # 从持久化加载的默认为非临时
        )
        
        # 添加消息
        for msg_data in data.get("messages", []):
            conversation.messages.append(Message.from_dict(msg_data))
        
        # 添加附件（简化处理）
        for att_data in data.get("attachments", []):
            if isinstance(att_data, dict) and "id" in att_data:
                try:
                    conversation.attachments.append(Attachment.from_dict(att_data))
                except:
                    # 如果解析失败，暂时跳过
                    pass
        
        return conversation
