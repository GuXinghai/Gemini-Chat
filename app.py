"""
Gemini Chat - AI 聊天客户端主入口

基于 Google Gemini API 与 PySide6 的跨平台 AI 聊天应用
支持多模态文件上传、主题定制、会话管理等功能

作者: Gemini Chat Team
版本: 1.0.0
许可: MIT License
"""
import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QCoreApplication

# 设置应用程序属性
QCoreApplication.setApplicationName("Gemini Chat")
QCoreApplication.setApplicationVersion("1.0.0")
QCoreApplication.setOrganizationName("Gemini Chat Team")

# 添加项目根目录到 Python 路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def main():
    """主函数 - 增强版应用启动流程"""
    app = QApplication(sys.argv)
    
    # 1. 加载配置并确保目录存在
    from geminichat.config.secrets import Config
    Config.ensure_directories()

    # 2. 检查 API 密钥
    if not Config.GEMINI_API_KEY:
        print("错误: 未设置 GEMINI_API_KEY，请在 .env 文件中设置: GEMINI_API_KEY=your_key_here")
        return 1
    print("✅ API密钥已配置")

    # 3. 初始化服务层
    from services.settings_service import SettingsService
    from services.history_service import HistoryService
    
    # 初始化增强版Gemini服务（支持Chat会话连续对话）
    from services.gemini_service_enhanced import GeminiServiceEnhanced
    gemini_service = GeminiServiceEnhanced(Config.GEMINI_API_KEY)
    print("✅ 使用增强版Gemini服务（支持Chat会话连续对话）")
    
    from services.file_upload_service import get_file_upload_service

    # 设置服务
    settings_service = SettingsService()

    # 历史记录服务
    history_service = HistoryService()

    # 文件上传服务
    file_upload_service = get_file_upload_service(Config.GEMINI_API_KEY)

    print("✅ 所有服务初始化完成")

    # 3.5. 启动时自动清理空的临时会话记录
    try:
        from services.startup_cleanup_service import perform_startup_cleanup
        deleted_count = perform_startup_cleanup(silent=True)
        if deleted_count > 0:
            print(f"🧹 启动清理: 自动删除了 {deleted_count} 个空的临时会话记录")
    except Exception as e:
        print(f"启动清理失败: {e}")

    # 4. 创建增强版主窗口（支持混合式情境感知启动）
    from ui.main_window_enhanced import EnhancedMainWindow
    from ui.ui_config import SimpleSettingsService
    ui_settings_service = SimpleSettingsService()
    window = EnhancedMainWindow(gemini_service, ui_settings_service, file_upload_service)
    print("✅ 使用增强版完整功能界面（支持情境感知启动和临时会话）")

    # 5. 显示窗口并启动应用
    window.show()
    print("🚀 应用程序启动成功！")
    
    # 打印启动信息
    if len(sys.argv) > 1:
        print(f"📎 检测到命令行参数: {sys.argv[1:]}")
        print("💡 将根据参数内容智能创建会话或预填充内容")
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
