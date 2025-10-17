# ui/enhanced_main_config.py
# 增强版主窗口的配置和基础类定义

from pathlib import Path
from enum import Enum
from uuid import uuid4
from datetime import datetime

# 配置常量
HISTORY_DIR = Path.home() / ".gemini_chat" / "history"
BASE_DIR = Path(__file__).parent.parent

# 需要跳过的特殊文件
SKIP_FILES = {'folders.json'}


def is_conversation_file(file_path: Path) -> bool:
    """判断是否为有效的对话文件"""
    return file_path.suffix == '.json' and file_path.name not in SKIP_FILES

# 字体配置工具函数
def get_safe_font(size=10, bold=False):
    """获取安全的字体配置，优先使用系统字体"""
    from PySide6.QtGui import QFont
    import platform
    
    # 根据操作系统选择合适的字体
    if platform.system() == "Windows":
        # Windows 优先字体顺序
        font_families = ["Microsoft YaHei", "SimHei", "Arial", "Segoe UI"]
    elif platform.system() == "Darwin":  # macOS
        font_families = ["PingFang SC", "Arial", "Helvetica"]
    else:  # Linux
        font_families = ["Noto Sans CJK SC", "DejaVu Sans", "Arial"]
    
    # 尝试创建字体，找到第一个可用的
    for family in font_families:
        font = QFont(family, size)
        if bold:
            font.setBold(True)
        
        # 检查字体是否可用
        if font.family() == family or QFont(family).family() == family:
            return font
    
    # 如果所有指定字体都不可用，使用默认字体
    font = QFont()
    font.setPointSize(size)
    if bold:
        font.setBold(True)
    return font

class ModelType(Enum):
    GEMINI_2_5_FLASH = "gemini-2.0-flash-exp"
    GEMINI_PRO = "gemini-pro"
    GEMINI_1_5_PRO = "gemini-1.5-pro"

# 会话模型 - 定义统一接口
from uuid import uuid4

class Conversation:
    """UI层会话模型，兼容域模型接口"""
    def __init__(self, id=None, title="新聊天", messages=None, is_ephemeral=True):
        self.id = id or str(uuid4())
        self.title = title
        self.messages = messages or []
        self.attachments = []
        self.is_ephemeral = is_ephemeral
        self.created_at = None
        self.updated_at = None
        self.metadata = {}
    
    def add_message(self, message):
        self.messages.append(message)
        if self.is_ephemeral:
            self.is_ephemeral = False
        if not self.title or self.title == "新聊天":
            if hasattr(message, 'content') and message.content:
                self.title = message.content[:50] + "..." if len(message.content) > 50 else message.content
    
    def add_attachment(self, attachment):
        """添加附件"""
        self.attachments.append(attachment)
    
    def has_content(self):
        return len(self.messages) > 0 or len(self.attachments) > 0
    
    def is_empty_ephemeral(self):
        return self.is_ephemeral and not self.has_content()
    
    def ensure_persistency_if_content(self):
        """如果有内容则确保持久化"""
        if self.is_ephemeral and self.has_content():
            self.is_ephemeral = False
            return True
        return False

# 域模型转换函数
def create_conversation_from_domain(domain_conv):
    """从域模型创建UI会话对象"""
    try:
        # 如果是域模型对象，转换为UI模型
        if hasattr(domain_conv, '__class__') and 'geminichat.domain' in str(domain_conv.__class__):
            return Conversation(
                id=domain_conv.id,
                title=domain_conv.title,
                messages=getattr(domain_conv, 'messages', []),
                is_ephemeral=getattr(domain_conv, 'is_ephemeral', True)
            )
        else:
            # 已经是UI模型或兼容对象
            return domain_conv
    except Exception:
        # 发生错误时创建新的临时会话
        return Conversation(is_ephemeral=True)

class UserSettings:
    def __init__(self):
        self.preferred_model = ModelType.GEMINI_2_5_FLASH
        self.dark_mode = False
        self.history_limit = 100
        
    @classmethod
    def load(cls):
        return cls()
        
    def save(self):
        pass

class SimpleHistoryService:
    def __init__(self, history_dir):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # 尝试使用真正的历史记录仓储
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from geminichat.infrastructure.history_repo import HistoryRepository
            self.repo = HistoryRepository()
            print("✅ 使用增强版历史记录服务")
        except ImportError as e:
            print(f"⚠️ 回退到简化版历史记录服务: {e}")
            self.repo = None
        
    def save(self, conversation):
        """保存会话"""
        if self.repo:
            # 确保conversation有正确的属性
            if hasattr(conversation, 'to_dict'):
                return self.repo.save_conversation(conversation)
            else:
                # 转换简化对象为域模型对象
                from geminichat.domain.conversation import Conversation as DomainConversation
                domain_conv = DomainConversation(
                    id=conversation.id,
                    title=conversation.title,
                    messages=getattr(conversation, 'messages', [])
                )
                return self.repo.save_conversation(domain_conv)
        else:
            # 回退到本地文件保存
            try:
                import json
                file_path = self.history_dir / f"{conversation.id}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    if hasattr(conversation, 'to_dict'):
                        json.dump(conversation.to_dict(), f, ensure_ascii=False, indent=2)
                    else:
                        # 简单对象的保存
                        data = {
                            'id': conversation.id,
                            'title': conversation.title,
                            'created_at': getattr(conversation, 'created_at', datetime.now()).isoformat(),
                            'updated_at': getattr(conversation, 'updated_at', datetime.now()).isoformat(),
                            'messages': [],
                            'metadata': {}
                        }
                        json.dump(data, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                print(f"保存会话失败: {e}")
                return False
        
    def load(self, conv_id):
        """加载会话"""
        if self.repo:
            return self.repo.load_conversation(conv_id)
        else:
            # 回退到本地文件加载
            try:
                import json
                file_path = self.history_dir / f"{conv_id}.json"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return Conversation(id=data['id'], title=data.get('title', f"聊天 {conv_id[:8]}"))
                else:
                    return Conversation(id=conv_id, title=f"聊天 {conv_id[:8]}")
            except Exception as e:
                print(f"加载会话失败: {e}")
                return Conversation(id=conv_id, title=f"聊天 {conv_id[:8]}")
    
    def list_conversations(self):
        """列出所有会话"""
        if self.repo:
            return self.repo.list_conversations()
        else:
            # 回退到本地文件列表
            conversations = []
            try:
                import json
                for file_path in self.history_dir.glob("*.json"):
                    # 使用通用过滤函数跳过特殊文件
                    if not is_conversation_file(file_path):
                        continue
                        
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        conversations.append(Conversation(
                            id=data['id'], 
                            title=data.get('title', f"聊天 {data['id'][:8]}")
                        ))
                    except:
                        continue
            except Exception as e:
                print(f"列出会话失败: {e}")
            return sorted(conversations, key=lambda c: getattr(c, 'updated_at', datetime.min), reverse=True)
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        if self.repo:
            return self.repo.delete_conversation(conversation_id)
        else:
            # 回退到本地文件删除
            try:
                file_path = self.history_dir / f"{conversation_id}.json"
                if file_path.exists():
                    file_path.unlink()
                return True
            except Exception as e:
                print(f"删除会话失败: {e}")
                return False
    
    def rename_conversation(self, conversation_id: str, new_title: str) -> bool:
        """重命名会话"""
        if self.repo:
            return self.repo.rename_conversation(conversation_id, new_title)
        else:
            # 回退到本地文件重命名
            try:
                import json
                file_path = self.history_dir / f"{conversation_id}.json"
                if not file_path.exists():
                    return False
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                data['title'] = new_title
                data['updated_at'] = datetime.now().isoformat()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return True
            except Exception as e:
                print(f"重命名会话失败: {e}")
                return False

class SimpleSettingsService:
    def __init__(self):
        self.settings = UserSettings.load()

class SimpleGeminiService:
    """简化的Gemini服务，用于UI配置"""
    def __init__(self, model=None, api_key=None):
        self.current_model = model or ModelType.GEMINI_2_5_FLASH
        self.model_name = self.current_model.value if hasattr(self.current_model, 'value') else str(self.current_model)
        
        # 尝试导入真实的GeminiService
        try:
            from services.gemini_service_enhanced import GeminiServiceEnhanced
            import os
            self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
            self.real_service = GeminiServiceEnhanced(self.api_key)
        except Exception as e:
            raise ImportError(f"无法初始化Gemini服务: {e}")
        
    def set_model(self, model):
        self.current_model = model
        self.model_name = model.value if hasattr(model, 'value') else str(model)
        
    async def send_message_async(self, content, conversation=None, model_name=None, streaming=False):
        """发送消息并获取回复"""
        return await self.real_service.send_message_async(content, conversation, model_name, streaming)
    
    async def send_message_stream_async(self, content, conversation=None, model_name=None):
        """流式发送消息并获取回复"""
        return self.real_service.send_message_stream_async(content, conversation, model_name)
    
    def get_available_models(self):
        """获取可用模型列表"""
        default_models = [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash", 
            "gemini-1.0-pro"
        ]
        
        if not hasattr(self, 'real_service') or not self.real_service:
            return default_models
            
        try:
            if not self.real_service.client:
                return default_models
            return self.real_service.client.get_available_models()
        except:
            return default_models
