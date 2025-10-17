"""
配置仓储实现
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # fallback
from ..config.settings_schema import Settings
from ..config.secrets import Config


class ConfigRepository:
    """配置仓储"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or Config.CONFIG_DIR)
        self.config_file = self.config_dir / "user_config.json"
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_defaults(self) -> Dict[str, Any]:
        """加载默认配置"""
        defaults_file = self.config_dir / "defaults.toml"
        if defaults_file.exists():
            try:
                with open(defaults_file, 'rb') as f:
                    return tomllib.load(f)
            except Exception:
                return {}
        return {}
    
    def load_user_config(self) -> Dict[str, Any]:
        """加载用户配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def save_user_config(self, config: Dict[str, Any]) -> bool:
        """保存用户配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False
    
    def get_settings(self) -> Settings:
        """获取完整设置"""
        defaults = self.load_defaults()
        user_config = self.load_user_config()
        
        # 合并配置
        merged_config = {**defaults, **user_config}
        return Settings(**merged_config)
    
    def update_setting(self, key: str, value: Any) -> bool:
        """更新单个设置"""
        user_config = self.load_user_config()
        
        # 处理嵌套键
        keys = key.split('.')
        current = user_config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        return self.save_user_config(user_config)
