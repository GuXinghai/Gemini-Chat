"""
文件夹管理仓储实现
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from ..config.secrets import Config

class FolderRepository:
    """文件夹仓储"""
    
    def __init__(self, folder_config_path: Optional[str] = None):
        self.folder_config_path = Path(folder_config_path or Config.FOLDER_CONFIG_PATH)
        self._ensure_config_file()
        self._load_folders()
    
    def _ensure_config_file(self):
        """确保配置文件存在"""
        if not self.folder_config_path.exists():
            self.folder_config_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_folders({
                "starred": {
                    "name": "星标",
                    "chats": []
                }
            })
    
    def _load_folders(self) -> Dict:
        """加载文件夹配置"""
        try:
            with open(self.folder_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {
                "starred": {
                    "name": "星标",
                    "chats": []
                }
            }
    
    def _save_folders(self, folders: Dict):
        """保存文件夹配置"""
        with open(self.folder_config_path, 'w', encoding='utf-8') as f:
            json.dump(folders, f, ensure_ascii=False, indent=2)
    
    def list_folders(self) -> List[Dict]:
        """列出所有文件夹"""
        folders = self._load_folders()
        result = []
        
        # 确保星标文件夹始终在第一位
        if "starred" in folders:
            result.append({
                "id": "starred",
                "name": folders["starred"]["name"],
                "chats": folders["starred"]["chats"]
            })
        
        # 添加其他文件夹
        for folder_id, folder in folders.items():
            if folder_id != "starred":
                result.append({
                    "id": folder_id,
                    "name": folder["name"],
                    "chats": folder["chats"]
                })
        
        return result
    
    def create_folder(self, name: str) -> str:
        """创建新文件夹"""
        folders = self._load_folders()
        folder_id = str(len(folders))
        
        folders[folder_id] = {
            "name": name,
            "chats": []
        }
        
        self._save_folders(folders)
        return folder_id
    
    def rename_folder(self, folder_id: str, new_name: str) -> bool:
        """重命名文件夹"""
        folders = self._load_folders()
        if folder_id not in folders:
            return False
        
        folders[folder_id]["name"] = new_name
        self._save_folders(folders)
        return True
    
    def delete_folder(self, folder_id: str) -> bool:
        """删除文件夹"""
        if folder_id == "starred":
            return False
            
        folders = self._load_folders()
        if folder_id not in folders:
            return False
        
        del folders[folder_id]
        self._save_folders(folders)
        return True
    
    def add_chat_to_folder(self, folder_id: str, chat_id: str) -> bool:
        """添加聊天记录到文件夹"""
        folders = self._load_folders()
        if folder_id not in folders:
            return False
        
        if chat_id not in folders[folder_id]["chats"]:
            folders[folder_id]["chats"].append(chat_id)
            self._save_folders(folders)
        return True
    
    def remove_chat_from_folder(self, folder_id: str, chat_id: str) -> bool:
        """从文件夹中移除聊天记录"""
        folders = self._load_folders()
        if folder_id not in folders:
            return False
        
        if chat_id in folders[folder_id]["chats"]:
            folders[folder_id]["chats"].remove(chat_id)
            self._save_folders(folders)
        return True
    
    def get_chat_folders(self, chat_id: str) -> List[str]:
        """获取聊天记录所在的所有文件夹"""
        folders = self._load_folders()
        return [
            folder_id for folder_id, folder in folders.items()
            if chat_id in folder["chats"]
        ]
