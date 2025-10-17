"""
历史记录仓储实现
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from ..domain.conversation import Conversation
from ..config.secrets import Config


class HistoryRepository:
    """历史记录仓储"""
    
    # 需要跳过的特殊文件
    SKIP_FILES = {'folders.json'}
    
    def __init__(self, history_dir: Optional[str] = None):
        self.history_dir = Path(history_dir or Config.CHAT_HISTORY_DIR)
        self._ensure_history_dir()
    
    def _ensure_history_dir(self):
        """确保历史记录目录存在"""
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def _is_conversation_file(self, file_path: Path) -> bool:
        """判断是否为有效的对话文件"""
        return file_path.suffix == '.json' and file_path.name not in self.SKIP_FILES
    
    def save_conversation(self, conversation: Conversation) -> bool:
        """保存会话"""
        try:
            file_path = self.history_dir / f"{conversation.id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False
    
    def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """加载会话"""
        file_path = self.history_dir / f"{conversation_id}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Conversation.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return None
    
    def list_conversations(self) -> List[Conversation]:
        """列出所有会话"""
        conversations = []
        for file_path in self.history_dir.glob("*.json"):
            # 使用通用过滤函数跳过特殊文件
            if not self._is_conversation_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                conversations.append(Conversation.from_dict(data))
            except (json.JSONDecodeError, IOError, KeyError, ValueError) as e:
                print(f"跳过无效的历史文件 {file_path}: {e}")
                continue
        
        # 按更新时间排序
        return sorted(conversations, key=lambda c: c.updated_at, reverse=True)
    
    def rename_conversation(self, conversation_id: str, new_title: str) -> bool:
        """重命名会话"""
        file_path = self.history_dir / f"{conversation_id}.json"
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['title'] = new_title
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except (json.JSONDecodeError, IOError):
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        file_path = self.history_dir / f"{conversation_id}.json"
        try:
            if file_path.exists():
                file_path.unlink()
            return True
        except OSError:
            return False
    
    def search_conversations(self, query: str) -> List[Conversation]:
        """搜索会话"""
        query_lower = query.lower()
        conversations = []
        
        for file_path in self.history_dir.glob("*.json"):
            # 使用通用过滤函数跳过特殊文件
            if not self._is_conversation_file(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 搜索标题和消息内容
                if query_lower in data.get("title", "").lower():
                    conversations.append(Conversation.from_dict(data))
                else:
                    # 搜索消息内容
                    for msg in data.get("messages", []):
                        if query_lower in msg.get("content", "").lower():
                            conversations.append(Conversation.from_dict(data))
                            break
            except (json.JSONDecodeError, IOError):
                continue
        
        return sorted(conversations, key=lambda c: c.updated_at, reverse=True)
