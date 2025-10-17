# UI组件模块
"""
用户界面组件模块
优先导出增强版UI组件，保持向后兼容性
"""

# 优先导出增强版UI组件
try:
    from .main_window_enhanced import EnhancedMainWindow as MainWindow
    from .chat_tab import EnhancedChatTab as ChatTab
    from .chat_input import EnhancedChatInput as ChatInput
    from .file_upload_widget import EnhancedFileUploadWidget as FileUploadWidget
    print("✅ 导出增强版UI组件")
    ENHANCED_UI = True
except ImportError:
    from .main_window import MainWindow
    from .chat_tab import ChatTab
    from .file_upload_widget import FileUploadWidget
    print("⚠️ 回退到基础版UI组件")
    ENHANCED_UI = False

from .ui_config import SimpleSettingsService, SimpleGeminiService

__all__ = ['MainWindow', 'ChatTab', 'FileUploadWidget', 'SimpleSettingsService', 'SimpleGeminiService', 'ENHANCED_UI']

