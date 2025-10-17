"""
设置服务层
"""
from typing import Any, Optional
import sys
import os

try:
    from geminichat.domain.model_type import ModelType
except ImportError:
    ModelType = None

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from geminichat.config.settings_schema import Settings
    from geminichat.infrastructure.config_repo import ConfigRepository
    from geminichat.domain.model_type import ModelType
except ImportError as e:
    print(f"Import warning in settings_service: {e}")
    Settings = None
    ConfigRepository = None
    ModelType = None


class SettingsService:
    """设置服务"""
    
    def __init__(self, initial_model: Optional[Any] = None):
        try:
            if ConfigRepository:
                self.config_repo = ConfigRepository()
            else:
                self.config_repo = None
            self._settings = None
            self.initial_model = initial_model
        except Exception:
            self.config_repo = None
            self._settings = None
            self.initial_model = None
    
    def get_settings(self) -> Optional[Any]:
        """获取设置"""
        if not self._settings and self.config_repo:
            try:
                self._settings = self.config_repo.get_settings()
            except Exception:
                pass
        return self._settings
    
    def update_setting(self, key: str, value: Any) -> bool:
        """更新设置"""
        if self.config_repo:
            result = self.config_repo.update_setting(key, value)
            if result:
                # 重新加载设置
                self._settings = None
                self.get_settings()
            return result
        return False

    @property
    def preferred_model(self):
        """获取首选模型"""
        if self.initial_model:
            return self.initial_model
        settings = self.get_settings()
        if settings and hasattr(settings, 'preferred_model'):
            return settings.preferred_model
        return ModelType.GEMINI_2_5_FLASH

    def update_model(self, model):
        """更新模型设置"""
        self.initial_model = model
        return self.update_setting('preferred_model', model.value if hasattr(model, 'value') else str(model))

    @classmethod
    def load(cls):
        """加载设置服务实例"""
        return cls()

