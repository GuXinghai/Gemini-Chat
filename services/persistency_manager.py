# services/persistency_manager.py
# 持久化策略管理器

from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from geminichat.domain.conversation import Conversation

logger = logging.getLogger(__name__)


class PersistencyManager:
    """持久化策略管理器"""
    
    def __init__(self, history_service):
        self.history_service = history_service
    
    def ensure_persistency_if_content(self, chat: 'Conversation') -> bool:
        """
        Action: ensure_persistency_if_content(chat)
        IF chat.is_ephemeral == true AND (chat.messages not empty OR chat.attachments not empty):
             chat.is_ephemeral = false
             save(chat)                       // 立即持久化
        ELSE:
             no-op
        
        返回是否发生了持久化操作
        """
        if chat.is_ephemeral and chat.has_content():
            chat.is_ephemeral = False
            self._save_chat(chat)
            logger.info(f"会话 {chat.id} 从临时状态转为持久状态")
            return True
        
        return False
    
    def autosave_on_mutation(self, chat: 'Conversation') -> bool:
        """
        Action: autosave_on_mutation(chat)
        // 文本输入、附件变更、标题变更均触发（节流/防抖属实现细节，非本规格）
        IF chat.is_ephemeral == true AND (chat.messages not empty OR chat.attachments not empty):
             chat.is_ephemeral = false
        save(chat)
        
        返回是否发生了从临时到持久的转换
        """
        was_ephemeral = chat.is_ephemeral
        
        if chat.is_ephemeral and chat.has_content():
            chat.is_ephemeral = False
        
        self._save_chat(chat)
        
        if was_ephemeral and not chat.is_ephemeral:
            logger.info(f"会话 {chat.id} 在数据变更时从临时状态转为持久状态")
            return True
        return False
    
    def should_discard_on_leave(self, chat: 'Conversation') -> bool:
        """
        判断离开会话时是否应该丢弃
        
        IF current_chat.is_ephemeral==true AND current_chat is empty:
             -> Action D1: discard(current_chat)   // 静默丢弃，不入历史
        """
        return chat.is_empty_ephemeral()
    
    def handle_chat_switch(self, current_chat: Optional['Conversation'], 
                          target_chat_id: str):
        """
        处理会话切换的持久化
        
        Event: UserAction.OpenChatFromHistory(target_chat_id)
        Pre-Action:
          IF current_chat exists:
               IF current_chat.is_ephemeral==true AND current_chat is empty:
                    -> Action D1: discard(current_chat)   // 静默丢弃，不入历史
               ELSE:
                    -> Action D2: save(current_chat)      // 保证不丢数据
        """
        if current_chat:
            if self.should_discard_on_leave(current_chat):
                self._discard_chat(current_chat)
                logger.info(f"切换时丢弃空的临时会话: {current_chat.id}")
            else:
                self._save_chat(current_chat)
                logger.info(f"切换时保存会话: {current_chat.id}")
    
    def handle_chat_close(self, chat: 'Conversation'):
        """
        处理会话关闭的持久化
        
        Event: UserAction.CloseCurrentChat
        Guard & Transition:
          IF current_chat.is_ephemeral==true AND current_chat is empty:
               -> Action E1: discard(current_chat)
          ELSE:
               -> Action E2: save(current_chat)
        """
        if self.should_discard_on_leave(chat):
            self._discard_chat(chat)
            logger.info(f"关闭时丢弃空的临时会话: {chat.id}")
        else:
            self._save_chat(chat)
            logger.info(f"关闭时保存会话: {chat.id}")
    
    def handle_app_exit(self, active_chats: list):
        """
        处理应用退出的持久化
        
        Event: AppExit
        For current_chat (if any):
          IF current_chat.is_ephemeral==true AND current_chat is empty:
               discard(current_chat)
          ELSE:
               save(current_chat)
        """
        for chat in active_chats:
            if chat:
                if self.should_discard_on_leave(chat):
                    self._discard_chat(chat)
                    logger.info(f"退出时丢弃空的临时会话: {getattr(chat, 'id', 'unknown')}")
                else:
                    self._save_chat(chat)
                    logger.info(f"退出时保存会话: {getattr(chat, 'id', 'unknown')}")
    
    def _save_chat(self, chat: 'Conversation'):
        """保存会话到存储"""
        try:
            if self.history_service:
                self.history_service.save(chat)
        except Exception as e:
            logger.error(f"保存会话失败 {chat.id}: {e}")
    
    def _discard_chat(self, chat: 'Conversation'):
        """丢弃会话（从存储中删除，如果已存在）"""
        try:
            chat_id = getattr(chat, 'id', None)
            if chat_id and self.history_service and hasattr(self.history_service, 'delete'):
                self.history_service.delete(chat_id)
            # 如果没有delete方法，空的临时会话本来就不会被保存，所以不需要额外操作
        except Exception as e:
            logger.error(f"丢弃会话失败 {getattr(chat, 'id', 'unknown')}: {e}")


class EphemeralChatTracker:
    """临时会话跟踪器"""
    
    def __init__(self):
        self.ephemeral_chats = set()
    
    def track_ephemeral(self, chat_id: str):
        """跟踪临时会话"""
        self.ephemeral_chats.add(chat_id)
    
    def untrack_ephemeral(self, chat_id: str):
        """取消跟踪临时会话"""
        self.ephemeral_chats.discard(chat_id)
    
    def is_ephemeral_tracked(self, chat_id: str) -> bool:
        """检查是否为被跟踪的临时会话"""
        return chat_id in self.ephemeral_chats
    
    def get_all_ephemeral(self) -> set:
        """获取所有临时会话ID"""
        return self.ephemeral_chats.copy()
