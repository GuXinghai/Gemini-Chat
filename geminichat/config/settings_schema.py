"""
Settings schema definitions using pydantic for validation
"""
from pydantic import BaseModel, Field
from typing import Optional


class AppSettings(BaseModel):
    """应用基本设置"""
    name: str = "Gemini Chat"
    version: str = "1.0.0"
    debug: bool = False
    locale: str = "zh-CN"


class UISettings(BaseModel):
    """界面设置"""
    theme: str = "dark"
    window_width: int = Field(default=1200, ge=600)
    window_height: int = Field(default=800, ge=400)
    min_width: int = Field(default=600, ge=400)
    min_height: int = Field(default=400, ge=300)
    font_family: str = "微软雅黑"
    font_size: int = Field(default=12, ge=8, le=24)


class APISettings(BaseModel):
    """API 设置"""
    default_model: str = "gemini-2.5-flash"
    max_tokens: int = Field(default=8192, ge=1, le=32768)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout: int = Field(default=30, ge=5, le=120)
    retry_count: int = Field(default=3, ge=1, le=10)


class ChatSettings(BaseModel):
    """聊天设置"""
    max_history_entries: int = Field(default=1000, ge=10, le=10000)
    auto_save: bool = True
    save_interval: int = Field(default=5, ge=1, le=60)  # minutes
    enable_streaming: bool = True  # 启用流式回复（默认开启）


class StorageSettings(BaseModel):
    """存储设置"""
    chat_history_dir: str = "chat_history"
    config_file: str = "config.json"
    logs_dir: str = "logs"


class Settings(BaseModel):
    """全局设置"""
    app: AppSettings = AppSettings()
    ui: UISettings = UISettings()
    api: APISettings = APISettings()
    chat: ChatSettings = ChatSettings()
    storage: StorageSettings = StorageSettings()
