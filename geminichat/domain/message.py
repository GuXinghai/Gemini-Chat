# domain/message.py
# 表示一次会话中的单条消息

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum


class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    CODE = "code"


@dataclass
class Message:
    """消息实体"""
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    message_type: MessageType = MessageType.TEXT
    attachments: Optional[List[str]] = None  # 附件文件路径列表
    metadata: Optional[dict] = None  # 额外元数据
    
    def __post_init__(self):
        """初始化后处理"""
        if self.attachments is None:
            self.attachments = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type.value,
            "attachments": self.attachments,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """从字典创建消息实例"""
        return cls(
            id=data["id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_type=MessageType(data.get("message_type", "text")),
            attachments=data.get("attachments", []),
            metadata=data.get("metadata", {})
        )
