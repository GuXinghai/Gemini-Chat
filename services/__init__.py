# 服务层模块
"""
服务层组件
优先导出增强版服务，保持向后兼容性
"""

# 优先导出增强版服务
try:
    from .gemini_service_enhanced import GeminiServiceEnhanced as GeminiService
    print("✅ 导出增强版Gemini服务")
except ImportError:
    from .gemini_service import GeminiService
    print("⚠️ 回退到基础版Gemini服务")

from .history_service import HistoryService
from .settings_service import SettingsService
from .file_upload_service import get_file_upload_service

__all__ = ['GeminiService', 'HistoryService', 'SettingsService', 'get_file_upload_service']
