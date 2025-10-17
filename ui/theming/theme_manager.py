"""
强化版主题管理器
负责主题的加载、应用、切换和管理
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtWidgets import QApplication

from .theme_schema import Theme, ThemeMode, create_default_light_theme, create_default_dark_theme
from .theme_model import ColorToken


class ThemeManager(QObject):
    """强化版主题管理器"""
    
    theme_changed = Signal(str)  # 主题切换信号
    mode_changed = Signal(str)   # 模式切换信号
    
    def __init__(self, app_data_dir: Optional[str] = None):
        super().__init__()
        
        # 设置目录
        if app_data_dir is None:
            app_data_dir = os.path.expanduser("~/.gemini-chat")
        self.app_data_dir = Path(app_data_dir)
        self.themes_dir = self.app_data_dir / "themes"
        self.themes_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置存储
        self.settings = QSettings("GeminiChat", "ThemeSettings")
        
        # 主题存储
        self._themes: Dict[str, Theme] = {}
        self._current_theme_name: str = "default_light"
        self._current_mode: ThemeMode = ThemeMode.LIGHT
        
        # 初始化
        self._load_builtin_themes()
        self._load_custom_themes()
        self._restore_settings()
    
    def _load_builtin_themes(self):
        """加载内置主题"""
        # 加载默认浅色主题
        light_theme = create_default_light_theme()
        self._themes["default_light"] = light_theme
        
        # 加载默认深色主题  
        dark_theme = create_default_dark_theme()
        self._themes["default_dark"] = dark_theme
    
    def _load_custom_themes(self):
        """加载用户自定义主题"""
        for theme_file in self.themes_dir.glob("*.json"):
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                    theme = Theme.from_dict(theme_data)
                    self._themes[theme.meta.name] = theme
            except Exception as e:
                print(f"加载主题失败 {theme_file}: {e}")
    
    def _restore_settings(self):
        """恢复设置"""
        # 恢复当前主题
        saved_theme = self.settings.value("current_theme", "default_light")
        if saved_theme in self._themes:
            self._current_theme_name = str(saved_theme)
            
        # 恢复当前模式
        saved_mode = self.settings.value("current_mode", "light")
        try:
            self._current_mode = ThemeMode(saved_mode)
        except ValueError:
            self._current_mode = ThemeMode.LIGHT
    
    def _save_settings(self):
        """保存设置"""
        self.settings.setValue("current_theme", self._current_theme_name)
        self.settings.setValue("current_mode", self._current_mode.value)
    
    def get_available_themes(self) -> Dict[str, str]:
        """获取可用主题列表"""
        return {
            theme_id: theme.meta.name
            for theme_id, theme in self._themes.items()
        }
    
    def get_current_theme(self) -> Optional[Theme]:
        """获取当前主题"""
        return self._themes.get(self._current_theme_name)
    
    def get_current_theme_name(self) -> str:
        """获取当前主题名称"""
        return self._current_theme_name
    
    def get_current_mode(self) -> ThemeMode:
        """获取当前模式"""
        return self._current_mode
    
    def set_theme(self, theme_name: str):
        """设置主题"""
        if theme_name not in self._themes:
            print(f"主题不存在: {theme_name}")
            return
            
        if self._current_theme_name != theme_name:
            self._current_theme_name = theme_name
            self._save_settings()
            # 自动应用主题到应用程序
            self.apply_theme_to_app()
            self.theme_changed.emit(theme_name)
    
    def set_mode(self, mode: ThemeMode):
        """设置模式"""
        if self._current_mode != mode:
            self._current_mode = mode
            self._save_settings()
            # 模式改变后重新应用主题
            self.apply_theme_to_app()
            self.mode_changed.emit(mode.value)
    
    def switch_theme(self, theme_name: str) -> bool:
        """切换主题（兼容方法）"""
        if theme_name not in self._themes:
            print(f"主题不存在: {theme_name}")
            return False
            
        self.set_theme(theme_name)
        return True
    
    def add_theme(self, theme: Theme):
        """添加主题"""
        self._themes[theme.meta.name] = theme
        
        # 保存到文件
        theme_file = self.themes_dir / f"{theme.meta.name}.json"
        try:
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存主题失败: {e}")
    
    def remove_theme(self, theme_name: str) -> bool:
        """移除主题"""
        if theme_name.startswith("default_"):
            print("无法删除内置主题")
            return False
            
        if theme_name not in self._themes:
            return False
            
        # 如果是当前主题，切换到默认主题
        if self._current_theme_name == theme_name:
            self.set_theme("default_light")
            
        # 删除主题
        del self._themes[theme_name]
        
        # 删除文件
        theme_file = self.themes_dir / f"{theme_name}.json"
        if theme_file.exists():
            theme_file.unlink()
            
        return True
    
    def get_theme_info(self, theme_name: str) -> Optional[dict]:
        """获取主题信息"""
        theme = self._themes.get(theme_name)
        if theme:
            return {
                'name': theme.meta.name,
                'author': theme.meta.author,
                'description': theme.meta.description,
                'created_at': getattr(theme.meta, 'created_at', ''),
                'schema_version': getattr(theme.meta, 'schema_version', '1.0.0')
            }
        return None
    
    def delete_theme(self, theme_name: str) -> bool:
        """删除主题（别名方法）"""
        return self.remove_theme(theme_name)
    
    def open_theme_editor(self, parent=None, theme_name: Optional[str] = None):
        """打开主题编辑器"""
        try:
            from .theme_editor import ThemeEditorDialog
            if theme_name:
                editor = ThemeEditorDialog(self, parent)
                # 可能需要设置编辑的主题
            else:
                editor = ThemeEditorDialog(self, parent)
            return editor
        except ImportError as e:
            print(f"主题编辑器不可用: {e}")
            return None
    
    def get_theme_color(self, color_token: ColorToken) -> str:
        """获取主题颜色"""
        current_theme = self.get_current_theme()
        if not current_theme:
            return "#000000"
            
        # 获取中性色调色板
        neutral_scale = current_theme.palette.neutral_scale
        
        # 根据当前模式获取颜色映射
        if self._current_mode == ThemeMode.LIGHT:
            color_mapping = {
                ColorToken.BACKGROUND.value: neutral_scale[0] if len(neutral_scale) > 0 else "#FFFFFF",
                ColorToken.SURFACE.value: neutral_scale[1] if len(neutral_scale) > 1 else "#F5F5F5", 
                ColorToken.SURFACE_ALT.value: neutral_scale[2] if len(neutral_scale) > 2 else "#E0E0E0",
                ColorToken.TEXT_PRIMARY.value: neutral_scale[7] if len(neutral_scale) > 7 else "#000000",
                ColorToken.TEXT_SECONDARY.value: neutral_scale[6] if len(neutral_scale) > 6 else "#666666",
                ColorToken.BORDER.value: neutral_scale[3] if len(neutral_scale) > 3 else "#CCCCCC",
                ColorToken.ACCENT.value: current_theme.palette.accent,
            }
        else:
            color_mapping = {
                ColorToken.BACKGROUND.value: neutral_scale[8] if len(neutral_scale) > 8 else "#1E1E1E",
                ColorToken.SURFACE.value: neutral_scale[6] if len(neutral_scale) > 6 else "#2D2D2D", 
                ColorToken.SURFACE_ALT.value: neutral_scale[7] if len(neutral_scale) > 7 else "#404040",
                ColorToken.TEXT_PRIMARY.value: neutral_scale[0] if len(neutral_scale) > 0 else "#FFFFFF",
                ColorToken.TEXT_SECONDARY.value: neutral_scale[1] if len(neutral_scale) > 1 else "#E0E0E0",
                ColorToken.BORDER.value: neutral_scale[4] if len(neutral_scale) > 4 else "#606060",
                ColorToken.ACCENT.value: current_theme.palette.accent,
            }
        
        return color_mapping.get(color_token.value, "#000000")
    
    def apply_theme_to_app(self, app: Optional[QApplication] = None):
        """将主题应用到应用程序"""
        if app is None:
            app_instance = QApplication.instance()
            if isinstance(app_instance, QApplication):
                app = app_instance
            
        if not app:
            return
            
        current_theme = self.get_current_theme()
        if not current_theme:
            return
            
        # 应用全局样式表
        stylesheet = self._generate_stylesheet(current_theme)
        app.setStyleSheet(stylesheet)
    
    def _generate_stylesheet(self, theme: Theme) -> str:
        """生成样式表"""
        # 获取调色板
        neutral_scale = theme.palette.neutral_scale
        accent = theme.palette.accent
        
        # 根据主题模式设置颜色映射
        if self._current_mode == ThemeMode.LIGHT:
            background = neutral_scale[0] if len(neutral_scale) > 0 else "#FFFFFF"
            surface = neutral_scale[1] if len(neutral_scale) > 1 else "#F5F5F5"
            surface_alt = neutral_scale[2] if len(neutral_scale) > 2 else "#E0E0E0"
            text_primary = neutral_scale[7] if len(neutral_scale) > 7 else "#000000"
            text_secondary = neutral_scale[6] if len(neutral_scale) > 6 else "#666666"
            border = neutral_scale[3] if len(neutral_scale) > 3 else "#CCCCCC"
            hover = neutral_scale[2] if len(neutral_scale) > 2 else "#E8E8E8"
            pressed = neutral_scale[4] if len(neutral_scale) > 4 else "#D0D0D0"
            disabled = neutral_scale[5] if len(neutral_scale) > 5 else "#A0A0A0"
            text_on_accent = "#FFFFFF"
        else:
            background = neutral_scale[8] if len(neutral_scale) > 8 else "#1E1E1E"
            surface = neutral_scale[6] if len(neutral_scale) > 6 else "#2D2D2D"
            surface_alt = neutral_scale[7] if len(neutral_scale) > 7 else "#404040"
            text_primary = neutral_scale[0] if len(neutral_scale) > 0 else "#FFFFFF"
            text_secondary = neutral_scale[1] if len(neutral_scale) > 1 else "#E0E0E0"
            border = neutral_scale[4] if len(neutral_scale) > 4 else "#606060"
            hover = neutral_scale[5] if len(neutral_scale) > 5 else "#505050"
            pressed = neutral_scale[7] if len(neutral_scale) > 7 else "#303030"
            disabled = neutral_scale[5] if len(neutral_scale) > 5 else "#606060"
            text_on_accent = "#FFFFFF"
        
        # 基础样式
        stylesheet = f"""
        QMainWindow {{
            background-color: {background};
            color: {text_primary};
        }}
        
        QWidget {{
            background-color: {background};
            color: {text_primary};
        }}
        
        QPushButton {{
            background-color: {accent};
            color: {text_on_accent};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 6px 12px;
        }}
        
        QPushButton:hover {{
            background-color: {hover};
        }}
        
        QPushButton:pressed {{
            background-color: {pressed};
        }}
        
        QPushButton:disabled {{
            background-color: {disabled};
            color: {text_secondary};
        }}
        
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {surface};
            color: {text_primary};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {accent};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {border};
            background-color: {surface};
        }}
        
        QTabBar::tab {{
            background-color: {surface_alt};
            color: {text_secondary};
            border: 1px solid {border};
            padding: 6px 12px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {accent};
            color: {text_on_accent};
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {hover};
        }}
        
        QMenuBar {{
            background-color: {surface};
            color: {text_primary};
            border-bottom: 1px solid {border};
        }}
        
        QMenuBar::item:selected {{
            background-color: {hover};
        }}
        
        QMenu {{
            background-color: {surface};
            color: {text_primary};
            border: 1px solid {border};
        }}
        
        QMenu::item:selected {{
            background-color: {hover};
        }}
        """
        
        return stylesheet
