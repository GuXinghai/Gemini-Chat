# domain/app_state.py
# 应用程序状态机定义

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Any
from pathlib import Path


class AppStateType(str, Enum):
    """应用状态类型"""
    WELCOME = "welcome"          # 欢迎页
    CHAT_VIEW = "chat_view"     # 会话视图
    NO_VIEW = "no_view"         # 过渡态，应立即转换


@dataclass
class Payload:
    """外部负载数据"""
    type: str  # "file", "url", "text", "command_arg"
    source: str  # 来源路径/URL/内容
    meta: Optional[dict] = None
    
    def __post_init__(self):
        if self.meta is None:
            self.meta = {}


@dataclass
class AppState:
    """应用程序状态"""
    type: AppStateType
    current_chat_id: Optional[str] = None
    payload: Optional[Payload] = None


class AppStateManager:
    """应用程序状态管理器"""
    
    def __init__(self):
        self.current_state: AppState = AppState(AppStateType.NO_VIEW)
        self.last_active_chat_id: Optional[str] = None
    
    def get_startup_state(self, incoming_payload: Optional[Payload] = None, 
                         last_active_chat_id: Optional[str] = None) -> AppState:
        """
        获取启动状态
        
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
        if incoming_payload:
            return AppState(AppStateType.CHAT_VIEW, payload=incoming_payload)
        elif last_active_chat_id:
            return AppState(AppStateType.CHAT_VIEW, current_chat_id=last_active_chat_id)
        else:
            return AppState(AppStateType.WELCOME)
    
    def should_create_new_chat_for_payload(self, current_state: AppState, 
                                         current_chat, payload: Payload) -> bool:
        """
        判断是否需要为外部负载创建新会话
        
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
        """
        if (current_state.type == AppStateType.CHAT_VIEW and 
            current_chat and 
            current_chat.is_empty_ephemeral()):
            return False  # 复用当前空会话
        return True  # 创建新会话
    
    def update_state(self, new_state: AppState):
        """更新状态"""
        self.current_state = new_state
        if new_state.current_chat_id:
            self.last_active_chat_id = new_state.current_chat_id


class PayloadParser:
    """负载解析器"""
    
    @staticmethod
    def parse_command_args(args: List[str]) -> Optional[Payload]:
        """解析命令行参数"""
        if len(args) <= 1:  # 只有脚本名
            return None
            
        for arg in args[1:]:  # 跳过脚本名
            if Path(arg).exists():
                return Payload(type="file", source=arg)
            elif arg.startswith(('http://', 'https://')):
                return Payload(type="url", source=arg)
            elif arg.strip():  # 非空文本
                return Payload(type="text", source=arg)
        
        return None
    
    @staticmethod
    def parse_file_drop(file_paths: List[str]) -> Optional[Payload]:
        """解析拖拽文件"""
        if not file_paths:
            return None
        
        valid_files = [f for f in file_paths if Path(f).exists()]
        if valid_files:
            return Payload(type="file", source=valid_files[0], 
                         meta={"all_files": valid_files})
        
        return None
    
    @staticmethod
    def create_text_payload(text: str) -> Payload:
        """创建文本负载"""
        return Payload(type="text", source=text)
