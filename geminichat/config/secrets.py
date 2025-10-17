"""
配置管理模块
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置类"""
    
    # API 配置
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # 应用配置
    APP_NAME = "Gemini Chat"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # 文件和目录配置
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CHAT_HISTORY_DIR = os.path.join(BASE_DIR, 'chat_history')
    FOLDER_CONFIG_PATH = os.path.join(CHAT_HISTORY_DIR, 'folders.json')
    
    # 数据存储路径
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CHAT_HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
    CONFIG_DIR = os.path.join(BASE_DIR, "config")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    
    # 确保目录存在
    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        os.makedirs(cls.CHAT_HISTORY_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
