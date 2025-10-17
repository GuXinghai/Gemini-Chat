"""
Gemini 服务层 - 增强版，支持Chat会话连续对话
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncIterator, Tuple
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from geminichat.domain.message import Message, MessageRole, MessageType
    from geminichat.domain.conversation import Conversation
    from geminichat.infrastructure.network.gemini_client_enhanced import GeminiClientEnhanced
    from geminichat.infrastructure.history_repo import HistoryRepository
except ImportError as e:
    print(f"Import warning in gemini_service_enhanced: {e}")


class GeminiServiceEnhanced:
    """Gemini 聊天服务 - 增强版，支持Chat会话连续对话"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        try:
            self.client = GeminiClientEnhanced(api_key) if api_key else GeminiClientEnhanced()
            self.history_repo = HistoryRepository()
            print("✅ 增强版Gemini服务初始化成功")
        except Exception as e:
            print(f"Warning: GeminiServiceEnhanced initialization failed: {e}")
            self.client = None
            self.history_repo = None
    
    def _ensure_domain_conversation(self, conversation):
        """确保转换为域模型的Conversation对象"""
        if conversation is None:
            from geminichat.domain.conversation import Conversation
            return Conversation()
            
        # 如果已经是域模型对象，直接返回
        if hasattr(conversation, '__module__') and 'domain' in str(conversation.__module__):
            return conversation
            
        # 如果是简化对象，转换为域模型对象
        from geminichat.domain.conversation import Conversation
        domain_conversation = Conversation(
            id=getattr(conversation, 'id', str(uuid.uuid4())),
            title=getattr(conversation, 'title', '新聊天')
        )
        
        # 复制消息（如果有的话）
        if hasattr(conversation, 'messages') and conversation.messages:
            for msg in conversation.messages:
                if hasattr(msg, 'to_dict'):
                    # 如果是域模型消息，直接添加
                    domain_conversation.messages.append(msg)
                else:
                    # 如果是简化消息，创建域模型消息
                    from geminichat.domain.message import Message, MessageRole, MessageType
                    domain_msg = Message(
                        id=str(uuid.uuid4()),
                        role=MessageRole.USER if getattr(msg, 'role', 'user') == 'user' else MessageRole.ASSISTANT,
                        content=getattr(msg, 'content', ''),
                        timestamp=datetime.now(),
                        message_type=MessageType.TEXT
                    )
                    domain_conversation.messages.append(domain_msg)
        
        return domain_conversation

    async def send_message_with_context_async(
        self, 
        content: str, 
        conversation: Optional['Conversation'] = None,
        model_name: Optional[str] = None,
        streaming: Optional[bool] = None,
        system_instruction: Optional[str] = None
    ) -> Tuple['Message', 'Conversation']:
        """发送消息并获取回复（使用Chat会话维护上下文）"""
        
        if not self.client:
            raise RuntimeError("Gemini client not initialized")
        
        # 确保使用域模型的Conversation对象
        conversation = self._ensure_domain_conversation(conversation)
        
        # 如果没有指定流式设置，使用用户设置
        if streaming is None:
            try:
                from geminichat.domain.user_settings import UserSettings
                user_settings = UserSettings.load()
                streaming = user_settings.enable_streaming
            except:
                streaming = False
        
        # 使用会话ID作为Chat会话的标识
        session_id = conversation.id
        
        # 创建用户消息
        from geminichat.domain.message import Message, MessageRole, MessageType
        user_message = Message(
            id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content=content,
            timestamp=datetime.now(),
            message_type=MessageType.TEXT
        )
        
        # 添加到会话
        conversation.add_message(user_message)
        
        try:
            if streaming:
                # 流式处理
                assistant_content = ""
                async for chunk in self.client.chat_with_session_stream_async(
                    message=content,
                    session_id=session_id,
                    model_name=model_name,
                    system_instruction=system_instruction
                ):
                    assistant_content += chunk
                response_text = assistant_content
            else:
                # 非流式处理 - 使用Chat会话
                response_text = await self.client.chat_with_session_async(
                    message=content,
                    session_id=session_id,
                    model_name=model_name,
                    system_instruction=system_instruction
                )
            
            # 创建助手消息
            assistant_message = Message(
                id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content=response_text,
                timestamp=datetime.now(),
                message_type=MessageType.TEXT
            )
            
            # 添加到会话
            conversation.add_message(assistant_message)
            
            # 保存会话
            if self.history_repo:
                self.history_repo.save_conversation(conversation)
            
            return assistant_message, conversation
            
        except Exception as e:
            # 创建错误消息
            error_message = Message(
                id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content=f"抱歉，发生了错误：{str(e)}",
                timestamp=datetime.now(),
                message_type=MessageType.TEXT,
                metadata={"error": True}
            )
            
            conversation.add_message(error_message)
            return error_message, conversation
    
    async def send_message_stream_with_context_async(
        self, 
        content: str, 
        conversation: Optional['Conversation'] = None,
        model_name: Optional[str] = None,
        system_instruction: Optional[str] = None
    ) -> AsyncIterator[Tuple[str, 'Conversation']]:
        """流式发送消息（使用Chat会话维护上下文）"""
        
        if not self.client:
            raise RuntimeError("Gemini client not initialized")
        
        # 确保使用域模型的Conversation对象
        conversation = self._ensure_domain_conversation(conversation)
        
        # 使用会话ID作为Chat会话的标识
        session_id = conversation.id
        
        # 创建用户消息
        from geminichat.domain.message import Message, MessageRole, MessageType
        user_message = Message(
            id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content=content,
            timestamp=datetime.now(),
            message_type=MessageType.TEXT
        )
        
        # 添加到会话
        conversation.add_message(user_message)
        
        try:
            assistant_content = ""
            async for chunk in self.client.chat_with_session_stream_async(
                message=content,
                session_id=session_id,
                model_name=model_name,
                system_instruction=system_instruction
            ):
                assistant_content += chunk
                yield chunk, conversation
            
            # 创建最终的助手消息
            assistant_message = Message(
                id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                timestamp=datetime.now(),
                message_type=MessageType.TEXT
            )
            
            # 添加到会话
            conversation.add_message(assistant_message)
            
            # 保存会话
            if self.history_repo:
                self.history_repo.save_conversation(conversation)
            
        except Exception as e:
            error_text = f"抱歉，发生了错误：{str(e)}"
            yield error_text, conversation
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if self.client:
            return self.client.get_available_models()
        return []
        
    def set_model(self, model_name: str) -> None:
        """设置当前使用的模型"""
        if self.client:
            self.client.set_model(model_name)
        else:
            print(f"Warning: Cannot set model {model_name}, client not initialized")
    
    def clear_conversation_context(self, conversation_id: str) -> None:
        """清除指定会话的Chat上下文"""
        if self.client:
            self.client.remove_chat_session(conversation_id)
            print(f"✅ 已清除会话 {conversation_id} 的上下文")
    
    def clear_all_contexts(self) -> None:
        """清除所有Chat会话上下文"""
        if self.client:
            self.client.clear_all_sessions()
            print("✅ 已清除所有会话上下文")
    
    def get_context_info(self) -> Dict[str, Any]:
        """获取当前上下文信息"""
        if self.client:
            sessions = self.client.get_chat_sessions()
            return {
                "total_sessions": len(sessions),
                "session_ids": list(sessions.keys()),
                "sessions": sessions
            }
        return {"total_sessions": 0, "session_ids": [], "sessions": {}}
    
    def estimate_tokens(self, conversation_id: str, message: str) -> int:
        """估算消息的token数量"""
        if self.client:
            return self.client.count_tokens_for_session(conversation_id, message)
        return len(message.split())
    
    # 保持向后兼容的方法
    async def send_message_async(self, *args, **kwargs):
        """向后兼容的方法"""
        return await self.send_message_with_context_async(*args, **kwargs)
    
    async def send_message_stream_async(self, *args, **kwargs):
        """向后兼容的方法"""
        async for result in self.send_message_stream_with_context_async(*args, **kwargs):
            yield result
            
    def generate_content(self, prompt: str) -> str:
        """生成内容的同步方法"""
        if self.client:
            try:
                # 创建临时会话ID
                temp_session_id = f"temp_{uuid.uuid4().hex[:8]}"
                response = asyncio.run(self.client.chat_with_session_async(
                    message=prompt,
                    session_id=temp_session_id
                ))
                # 清理临时会话
                self.client.remove_chat_session(temp_session_id)
                return response
            except Exception as e:
                return f"生成内容时出错: {e}"
        return "服务未初始化"
