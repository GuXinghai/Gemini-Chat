"""
文件夹服务层
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from geminichat.infrastructure.folder_repo import FolderRepository

class FolderService:
    """文件夹服务"""
    
    def __init__(self):
        """初始化文件夹服务"""
        self.repository = FolderRepository()
    
    def list_folders(self) -> List[Dict]:
        """列出所有文件夹"""
        return self.repository.list_folders()
    
    def create_folder(self, name: str) -> str:
        """创建新文件夹"""
        return self.repository.create_folder(name)
    
    def rename_folder(self, folder_id: str, new_name: str) -> bool:
        """重命名文件夹"""
        return self.repository.rename_folder(folder_id, new_name)
    
    def delete_folder(self, folder_id: str) -> bool:
        """删除文件夹"""
        return self.repository.delete_folder(folder_id)
    
    def add_chat_to_folder(self, folder_id: str, chat_id: str) -> bool:
        """添加聊天记录到文件夹"""
        return self.repository.add_chat_to_folder(folder_id, chat_id)
    
    def remove_chat_from_folder(self, folder_id: str, chat_id: str) -> bool:
        """从文件夹中移除聊天记录"""
        return self.repository.remove_chat_from_folder(folder_id, chat_id)
    
    def get_chat_folders(self, chat_id: str) -> List[str]:
        """获取聊天记录所在的所有文件夹"""
        return self.repository.get_chat_folders(chat_id)
