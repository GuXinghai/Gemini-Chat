# domain/attachment.py
# 表示用户拖拽或上传的文件/图片

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum
import os


class AttachmentType(str, Enum):
    """附件类型枚举"""
    IMAGE = "image"
    DOCUMENT = "document" 
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    OTHER = "other"


@dataclass
class Attachment:
    """附件实体"""
    id: str
    file_path: str
    original_name: str
    file_size: int  # bytes
    mime_type: str
    attachment_type: AttachmentType
    uploaded_at: datetime
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def exists(self) -> bool:
        """检查文件是否存在"""
        return os.path.exists(self.file_path)
    
    @property
    def file_extension(self) -> str:
        """获取文件扩展名"""
        return os.path.splitext(self.original_name)[1].lower()
    
    @property
    def size_human_readable(self) -> str:
        """人类可读的文件大小"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "original_name": self.original_name,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "attachment_type": self.attachment_type.value,
            "uploaded_at": self.uploaded_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Attachment":
        """从字典创建附件实例"""
        return cls(
            id=data["id"],
            file_path=data["file_path"],
            original_name=data["original_name"],
            file_size=data["file_size"],
            mime_type=data["mime_type"],
            attachment_type=AttachmentType(data["attachment_type"]),
            uploaded_at=datetime.fromisoformat(data["uploaded_at"]),
            metadata=data.get("metadata", {})
        )
