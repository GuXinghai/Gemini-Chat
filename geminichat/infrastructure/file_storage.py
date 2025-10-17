"""
文件存储相关功能
"""
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from ..domain.attachment import Attachment, AttachmentType
from ..config.secrets import Config


class FileStorage:
    """文件存储管理器"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or os.path.join(Config.BASE_DIR, "attachments"))
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file_path: str, original_name: str) -> Optional[Attachment]:
        """保存文件并返回附件对象"""
        source_path = Path(file_path)
        if not source_path.exists():
            return None
        
        # 生成唯一ID和存储路径
        attachment_id = str(uuid.uuid4())
        file_extension = source_path.suffix
        stored_filename = f"{attachment_id}{file_extension}"
        stored_path = self.storage_dir / stored_filename
        
        try:
            # 复制文件
            shutil.copy2(source_path, stored_path)
            
            # 获取文件信息
            file_size = stored_path.stat().st_size
            mime_type = self._get_mime_type(file_extension)
            attachment_type = self._get_attachment_type(mime_type)
            
            return Attachment(
                id=attachment_id,
                file_path=str(stored_path),
                original_name=original_name,
                file_size=file_size,
                mime_type=mime_type,
                attachment_type=attachment_type,
                uploaded_at=datetime.now()
            )
        except (OSError, IOError):
            return None
    
    def delete_file(self, attachment: Attachment) -> bool:
        """删除文件"""
        try:
            file_path = Path(attachment.file_path)
            if file_path.exists():
                file_path.unlink()
            return True
        except OSError:
            return False
    
    def get_file_path(self, attachment_id: str) -> Optional[str]:
        """根据ID获取文件路径"""
        for file_path in self.storage_dir.glob(f"{attachment_id}.*"):
            return str(file_path)
        return None
    
    def cleanup_orphaned_files(self, valid_attachments: List[str]) -> int:
        """清理孤立文件"""
        cleaned_count = 0
        valid_ids = set(valid_attachments)
        
        for file_path in self.storage_dir.glob("*"):
            if file_path.is_file():
                attachment_id = file_path.stem
                if attachment_id not in valid_ids:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except OSError:
                        continue
        
        return cleaned_count
    
    def _get_mime_type(self, file_extension: str) -> str:
        """根据文件扩展名推断MIME类型"""
        mime_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.html': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.flac': 'audio/flac'
        }
        return mime_types.get(file_extension.lower(), 'application/octet-stream')
    
    def _get_attachment_type(self, mime_type: str) -> AttachmentType:
        """根据MIME类型推断附件类型"""
        if mime_type.startswith('image/'):
            return AttachmentType.IMAGE
        elif mime_type.startswith('video/'):
            return AttachmentType.VIDEO
        elif mime_type.startswith('audio/'):
            return AttachmentType.AUDIO
        elif mime_type in ['text/x-python', 'text/javascript', 'text/html', 'text/css']:
            return AttachmentType.CODE
        elif mime_type.startswith('text/') or mime_type in ['application/json', 'application/xml']:
            return AttachmentType.DOCUMENT
        else:
            return AttachmentType.OTHER
