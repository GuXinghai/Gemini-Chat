"""
Gemini API 客户端 - 增强版，支持Chat会话连续对话
"""
import asyncio
import os
from typing import Optional, AsyncIterator, List, Dict, Any

from ...domain.model_type import ModelType
from ...config.secrets import Config


class GeminiClientEnhanced:
    """Gemini API 客户端 - 增强版，基于最新Google GenAI SDK，支持Chat会话连续对话"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("必须提供有效的 API 密钥")
        
        self.client = None
        self.current_model_name: Optional[str] = None
        self._chat_sessions: Dict[str, Any] = {}  # 存储Chat会话对象
        self._connection_tested = False  # 标记是否已测试连接
        
        # 导入和初始化最新的Google GenAI SDK
        try:
            from google import genai
            from google.genai import types
            # 使用最新SDK的Client初始化方式
            self.client = genai.Client(api_key=self.api_key)
            self.types = types  # 保存types引用以便后续使用
            print("✅ Gemini API已成功配置（增强版，支持Chat会话）")
            
            # 预先测试连接
            try:
                self._test_connection()
            except Exception as test_error:
                print(f"⚠️ 连接测试失败: {test_error}")
                # 不抛出异常，允许程序继续运行
            
        except ImportError as e:
            print(f"⚠️ google-genai SDK未安装: {e}")
            print("请运行: pip install google-genai")
            raise ImportError("必须安装 google-genai 库") from e
        except Exception as e:
            print(f"⚠️ API配置失败: {e}")
            raise ValueError("API 配置失败") from e
    
    def _test_connection(self):
        """测试API连接"""
        try:
            if not self.client:
                raise ValueError("客户端未初始化")
            
            # 简单的连接测试 - 列出模型
            models = self.client.models.list()
            print("✅ API连接测试成功")
            self._connection_tested = True
        except Exception as e:
            print(f"⚠️ API连接测试失败: {e}")
            self._connection_tested = False
            raise e
    
    def set_model(self, model_name: Optional[str] = None) -> None:
        """设置使用的模型"""
        if model_name is None:
            model_name = "gemini-2.0-flash-001"  # 使用官方推荐的新模型
        elif hasattr(model_name, 'value') and not isinstance(model_name, str):
            model_name = model_name.value
            
        try:
            self.current_model_name = model_name
            print(f"✅ 模型已设置: {model_name}")
        except Exception as e:
            print(f"模型设置失败: {e}")
            raise ValueError(f"无法设置模型 {model_name}") from e
    
    def get_or_create_chat_session(
        self, 
        session_id: str, 
        model_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7
    ) -> Any:
        """获取或创建Chat会话对象（官方推荐方式）"""
        if session_id in self._chat_sessions:
            print(f"使用现有Chat会话: {session_id}")
            return self._chat_sessions[session_id]
        
        if model_name is None:
            model_name = self.current_model_name or "gemini-2.0-flash-001"
        elif hasattr(model_name, 'value') and not isinstance(model_name, str):
            model_name = model_name.value
            
        print(f"创建新Chat会话: {session_id}, 模型: {model_name}")
        
        try:
            if not self.client:
                raise ValueError("客户端未初始化")
            
            # 尝试使用官方Chat API创建会话
            try:
                # 根据最新SDK文档，创建Chat会话
                chat_session = self.client.chats.create(
                    model=model_name
                )
                self._chat_sessions[session_id] = chat_session
                print(f"✅ 创建官方Chat会话成功: {session_id}")
                return chat_session
                
            except (AttributeError, TypeError) as e:
                print(f"官方Chat API不可用，使用手动上下文管理: {e}")
                # 手动维护上下文的会话对象
                chat_session = {
                    "session_id": session_id,
                    "model": model_name,
                    "messages": [],
                    "config": {
                        "system_instruction": system_instruction or "你是一个有帮助的AI助手，请用简洁而有用的方式回答问题。",
                        "temperature": temperature
                    },
                    "created_time": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
                }
                self._chat_sessions[session_id] = chat_session
                print(f"✅ 创建手动上下文会话成功: {session_id}")
                return chat_session
            
        except Exception as e:
            print(f"创建Chat会话失败: {e}")
            # 创建一个最基础的会话对象作为回退
            fallback_session = {
                "session_id": session_id,
                "model": model_name,
                "messages": [],
                "config": {
                    "system_instruction": system_instruction or "你是一个有帮助的AI助手，请用简洁而有用的方式回答问题。",
                    "temperature": temperature
                },
                "created_time": 0,
                "fallback": True
            }
            self._chat_sessions[session_id] = fallback_session
            print(f"⚠️ 使用回退会话对象: {session_id}")
            return fallback_session
    
    def remove_chat_session(self, session_id: str) -> None:
        """删除Chat会话对象"""
        if session_id in self._chat_sessions:
            del self._chat_sessions[session_id]
            print(f"✅ 删除Chat会话: {session_id}")
    
    def count_tokens_for_session(self, session_id: str, message: str) -> int:
        """计算指定会话和消息的token数量"""
        try:
            if self.client and hasattr(self.client, 'models'):
                model_name = self.current_model_name or "gemini-2.0-flash-001"
                stats = self.client.models.count_tokens(
                    model=model_name,
                    contents=message
                )
                return stats.total_tokens if stats.total_tokens else len(message.split())
            return len(message.split())
        except Exception as e:
            print(f"Token计算失败: {e}")
            return len(message.split())
    
    async def chat_with_session_async(
        self, 
        message: str,
        session_id: str,
        model_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> str:
        """使用Chat会话进行连续对话（非流式）- 官方推荐方式"""
        if model_name is None:
            model_name = self.current_model_name or "gemini-2.0-flash-001"
        elif hasattr(model_name, 'value') and not isinstance(model_name, str):
            model_name = model_name.value
        
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # 获取或创建Chat会话
                chat_session = self.get_or_create_chat_session(
                    session_id=session_id,
                    model_name=model_name,
                    system_instruction=system_instruction
                )
                
                print(f"使用会话 {session_id} 发送消息 (第 {attempt + 1} 次): {message[:100]}...")
                
                # 检查是否是官方Chat会话对象
                if hasattr(chat_session, 'send_message'):
                    # 使用官方Chat会话API - 上下文自动管理
                    response = chat_session.send_message(message)
                    result = response.text if hasattr(response, 'text') and response.text else "空回复"
                    print(f"收到官方Chat会话响应: {result[:100]}...")
                    return result
                else:
                    # 使用手动维护的上下文
                    if isinstance(chat_session, dict):
                        # 添加用户消息到历史中
                        chat_session["messages"].append({"role": "user", "content": message})
                        
                        # 构造完整的消息历史用于API调用
                        contents = []
                        system_msg = chat_session.get("config", {}).get("system_instruction")
                        if system_msg:
                            contents.append({"role": "system", "content": system_msg})
                        
                        contents.extend(chat_session["messages"])
                        
                        # 调用基础API
                        response = await self._call_basic_api(contents, model_name)
                        
                        # 添加助手回复到历史中
                        chat_session["messages"].append({"role": "assistant", "content": response})
                        
                        print(f"收到手动上下文响应: {response[:100]}...")
                        return response
                    else:
                        # 回退到单次调用
                        return await self._call_basic_api([{"role": "user", "content": message}], model_name)
                
            except Exception as e:
                error_str = str(e).lower()
                is_network_error = any(keyword in error_str for keyword in ['10054', 'connection', 'network', 'timeout'])
                
                print(f"会话聊天失败 (第 {attempt + 1} 次): {e}")
                
                if is_network_error and attempt < max_retries - 1:
                    print(f"网络连接错误，{retry_delay}秒后重试...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    print(f"会话聊天最终失败: {e}")
                    import traceback
                    print(f"错误堆栈: {traceback.format_exc()}")
                    return f"抱歉，发生了错误：{str(e)}"
        
        return "抱歉，发生了错误：重试次数已用完"
    
    async def chat_with_session_stream_async(
        self, 
        message: str,
        session_id: str,
        model_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """使用Chat会话进行连续对话（流式）- 官方推荐方式"""
        if model_name is None:
            model_name = self.current_model_name or "gemini-2.0-flash-001"
        elif hasattr(model_name, 'value') and not isinstance(model_name, str):
            model_name = model_name.value
            
        try:
            # 获取或创建Chat会话
            chat_session = self.get_or_create_chat_session(
                session_id=session_id,
                model_name=model_name,
                system_instruction=system_instruction
            )
            
            print(f"使用会话 {session_id} 发送流式消息: {message[:100]}...")
            
            # 检查是否是官方Chat会话对象
            if hasattr(chat_session, 'send_message_stream'):
                # 使用官方Chat会话流式API - 上下文自动管理
                print("使用官方流式Chat API")
                for chunk in chat_session.send_message_stream(message):
                    if hasattr(chunk, 'text') and chunk.text:
                        yield chunk.text
                    await asyncio.sleep(0.01)
            else:
                # 使用手动维护的上下文进行流式调用
                if isinstance(chat_session, dict):
                    print("使用手动上下文流式API")
                    # 添加用户消息到历史中
                    chat_session["messages"].append({"role": "user", "content": message})
                    
                    # 构造完整的消息历史
                    contents = []
                    system_msg = chat_session.get("config", {}).get("system_instruction")
                    if system_msg:
                        contents.append({"role": "system", "content": system_msg})
                    
                    contents.extend(chat_session["messages"])
                    
                    # 调用流式API
                    full_response = ""
                    async for chunk in self._call_basic_stream_api(contents, model_name):
                        full_response += chunk
                        yield chunk
                    
                    # 添加助手回复到历史中
                    if full_response.strip():
                        chat_session["messages"].append({"role": "assistant", "content": full_response})
                else:
                    # 回退到单次流式调用
                    async for chunk in self._call_basic_stream_api([{"role": "user", "content": message}], model_name):
                        yield chunk
            
        except Exception as e:
            print(f"会话流式聊天失败: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            error_msg = f"抱歉，发生了错误：{str(e)}"
            yield error_msg
    
    async def _call_basic_api(self, messages: List[Dict[str, Any]], model_name: str) -> str:
        """调用基础API（非流式）"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                if not self.client:
                    raise Exception("客户端未正确初始化")
                
                # 只发送最后一条用户消息到API（简化处理）
                user_messages = [msg for msg in messages if msg.get("role") == "user"]
                if not user_messages:
                    raise Exception("没有用户消息")
                
                last_user_message = user_messages[-1]["content"]
                
                print(f"尝试API调用 (第 {attempt + 1} 次)...")
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=last_user_message
                )
                
                result = response.text if hasattr(response, 'text') and response.text else "空回复"
                print(f"API调用成功，响应长度: {len(result)}")
                return result
                
            except Exception as e:
                print(f"基础API调用失败 (第 {attempt + 1} 次): {e}")
                
                # 检查是否是网络连接错误
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['10054', 'connection', 'network', 'timeout']):
                    if attempt < max_retries - 1:
                        print(f"网络连接错误，{retry_delay}秒后重试...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        raise Exception(f"基础API调用失败：网络连接问题 - {str(e)}")
                else:
                    # 非网络错误，直接抛出
                    raise Exception(f"基础API调用失败: {str(e)}")
        
        raise Exception("基础API调用失败：重试次数已用完")
    
    async def _call_basic_stream_api(self, messages: List[Dict[str, Any]], model_name: str) -> AsyncIterator[str]:
        """调用基础流式API"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                if not self.client:
                    raise Exception("客户端未正确初始化")
                
                # 只发送最后一条用户消息到API（简化处理）
                user_messages = [msg for msg in messages if msg.get("role") == "user"]
                if not user_messages:
                    raise Exception("没有用户消息")
                
                last_user_message = user_messages[-1]["content"]
                
                print(f"尝试流式API调用 (第 {attempt + 1} 次)...")
                stream_response = self.client.models.generate_content_stream(
                    model=model_name,
                    contents=last_user_message
                )
                
                chunk_count = 0
                for chunk in stream_response:
                    chunk_count += 1
                    if hasattr(chunk, 'text') and chunk.text:
                        yield chunk.text
                    await asyncio.sleep(0.01)
                    
                print(f"流式响应完成，共收到 {chunk_count} 个块")
                return  # 成功完成，退出重试循环
                    
            except Exception as e:
                print(f"基础流式API调用失败 (第 {attempt + 1} 次): {e}")
                
                # 检查是否是网络连接错误
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['10054', 'connection', 'network', 'timeout']):
                    if attempt < max_retries - 1:
                        print(f"网络连接错误，{retry_delay}秒后重试...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        error_msg = f"基础流式API调用失败：网络连接问题 - {str(e)}"
                        yield error_msg
                        return
                else:
                    # 非网络错误，直接返回错误
                    error_msg = f"基础流式API调用失败: {str(e)}"
                    yield error_msg
                    return
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            "gemini-2.0-flash-001",  # 官方推荐的最新模型
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
    
    def get_chat_sessions(self) -> Dict[str, Any]:
        """获取所有Chat会话"""
        return self._chat_sessions.copy()
    
    def clear_all_sessions(self) -> None:
        """清除所有Chat会话"""
        self._chat_sessions.clear()
        print("✅ 已清除所有Chat会话")
