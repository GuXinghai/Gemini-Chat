"""
历史记录服务层
"""
import json
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from geminichat.domain.conversation import Conversation
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from geminichat.domain.conversation import Conversation
    from geminichat.infrastructure.history_repo import HistoryRepository
except ImportError as e:
    print(f"Import warning in history_service: {e}")
    Conversation = None
    HistoryRepository = None


class HistoryService:
    """历史记录服务"""
    
    def __init__(self, history_dir: Optional[Path] = None):
        try:
            if history_dir:
                self.history_dir = history_dir
                self.history_dir.mkdir(parents=True, exist_ok=True)
                if HistoryRepository:
                    self.repository = HistoryRepository(str(history_dir))
                else:
                    self.repository = None
            else:
                if HistoryRepository:
                    self.repository = HistoryRepository()
                else:
                    self.repository = None
        except Exception as e:
            print(f"Warning: HistoryService initialization failed: {e}")
            self.repository = None
    
    def save(self, conv: Any):
        """保存会话（兼容旧接口）"""
        if hasattr(self, 'history_dir') and self.history_dir:
            path = self.history_dir / f"{conv.id}.json"
            with open(path, "w", encoding="utf-8") as f:
                data = {"schema_version": 1, **conv.to_dict()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        elif self.repository:
            self.repository.save_conversation(conv)
    
    def save_conversation(self, conversation: Any) -> bool:
        """保存会话"""
        try:
            self.save(conversation)
            return True
        except Exception:
            return False
    
    def load_conversation(self, conversation_id: str) -> Optional[Any]:
        """加载会话"""
        if self.repository:
            return self.repository.load_conversation(conversation_id)
        return None
    
    def list_conversations(self) -> List[Any]:
        """获取所有会话列表"""
        if self.repository:
            return self.repository.list_conversations()
        return []
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        if self.repository:
            return self.repository.delete_conversation(conversation_id)
        return False
    
    def search_conversations(self, query: str) -> List[Any]:
        """搜索会话"""
        if self.repository:
            return self.repository.search_conversations(query)
        return []
    
    def rename_conversation(self, conversation_id: str, new_title: str) -> bool:
        """重命名会话"""
        if self.repository:
            return self.repository.rename_conversation(conversation_id, new_title)
        return False
