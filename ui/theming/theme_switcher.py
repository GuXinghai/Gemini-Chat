"""
主题切换器组件
提供简洁的主题切换界面
"""
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QComboBox, 
                               QPushButton, QLabel, QFrame)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from .theme_manager import ThemeManager
from .theme_schema import ThemeMode


class ThemeSwitcherWidget(QFrame):
    """主题切换器组件"""
    
    theme_changed = Signal(str)
    mode_changed = Signal(str)
    
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("主题设置")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 主题选择
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("主题:"))
        
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(150)
        theme_layout.addWidget(self.theme_combo)
        
        layout.addLayout(theme_layout)
        
        # 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["浅色", "深色"])
        self.mode_combo.setMinimumWidth(150)
        mode_layout.addWidget(self.mode_combo)
        
        layout.addLayout(mode_layout)
        
        # 应用按钮
        self.apply_btn = QPushButton("应用主题")
        layout.addWidget(self.apply_btn)
        
        # 加载数据
        self.refresh_themes()
        self.refresh_current_settings()
    
    def connect_signals(self):
        """连接信号"""
        self.apply_btn.clicked.connect(self.apply_theme)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        # 连接主题管理器的信号
        self.theme_manager.theme_changed.connect(self.on_theme_manager_changed)
        self.theme_manager.mode_changed.connect(self.on_mode_manager_changed)
    
    def refresh_themes(self):
        """刷新主题列表"""
        self.theme_combo.clear()
        themes = self.theme_manager.get_available_themes()
        for theme_id, theme_name in themes.items():
            self.theme_combo.addItem(theme_name, theme_id)
    
    def refresh_current_settings(self):
        """刷新当前设置"""
        # 设置当前主题
        current_theme = self.theme_manager.get_current_theme_name()
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        # 设置当前模式
        current_mode = self.theme_manager.get_current_mode()
        if current_mode == ThemeMode.LIGHT:
            self.mode_combo.setCurrentText("浅色")
        else:
            self.mode_combo.setCurrentText("深色")
    
    def apply_theme(self):
        """应用主题"""
        # 暂时断开信号以防止循环调用
        self.theme_manager.theme_changed.disconnect()
        self.theme_manager.mode_changed.disconnect()
        
        try:
            # 获取选择的主题
            theme_id = self.theme_combo.currentData()
            if theme_id:
                self.theme_manager.set_theme(theme_id)
                self.theme_changed.emit(theme_id)
            
            # 获取选择的模式
            mode_text = self.mode_combo.currentText()
            mode = ThemeMode.LIGHT if mode_text == "浅色" else ThemeMode.DARK
            self.theme_manager.set_mode(mode)
            self.mode_changed.emit(mode.value)
        finally:
            # 重新连接信号
            self.theme_manager.theme_changed.connect(self.on_theme_manager_changed)
            self.theme_manager.mode_changed.connect(self.on_mode_manager_changed)
    
    def on_theme_changed(self, theme_name: str):
        """主题改变时的处理"""
        pass
    
    def on_mode_changed(self, mode_text: str):
        """模式改变时的处理"""
        pass
    
    def on_theme_manager_changed(self, theme_name: str):
        """主题管理器主题变更时的处理"""
        self.refresh_current_settings()
    
    def on_mode_manager_changed(self, mode_value: str):
        """主题管理器模式变更时的处理"""
        self.refresh_current_settings()


class CompactThemeSwitcher(QFrame):
    """紧凑版主题切换器"""
    
    theme_changed = Signal(str)
    mode_changed = Signal(str)
    
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        # 主题选择
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(120)
        layout.addWidget(self.theme_combo)
        
        # 模式切换按钮
        self.mode_btn = QPushButton("🌙")
        self.mode_btn.setMaximumWidth(32)
        self.mode_btn.setToolTip("切换浅色/深色模式")
        layout.addWidget(self.mode_btn)
        
        # 加载数据
        self.refresh_themes()
        self.refresh_current_settings()
    
    def connect_signals(self):
        """连接信号"""
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        self.mode_btn.clicked.connect(self.toggle_mode)
        
        # 连接主题管理器的信号
        self.theme_manager.theme_changed.connect(self.on_theme_manager_changed)
        self.theme_manager.mode_changed.connect(self.on_mode_manager_changed)
        
    def on_theme_manager_changed(self, theme_name: str):
        """主题管理器主题变更时的处理"""
        self.refresh_current_settings()
    
    def on_mode_manager_changed(self, mode_value: str):
        """主题管理器模式变更时的处理"""
        self.refresh_current_settings()
    
    def refresh_themes(self):
        """刷新主题列表"""
        self.theme_combo.clear()
        themes = self.theme_manager.get_available_themes()
        for theme_id, theme_name in themes.items():
            self.theme_combo.addItem(theme_name, theme_id)
    
    def refresh_current_settings(self):
        """刷新当前设置"""
        # 设置当前主题
        current_theme = self.theme_manager.get_current_theme_name()
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        # 更新模式按钮
        current_mode = self.theme_manager.get_current_mode()
        if current_mode == ThemeMode.LIGHT:
            self.mode_btn.setText("🌙")
            self.mode_btn.setToolTip("切换到深色模式")
        else:
            self.mode_btn.setText("☀️")
            self.mode_btn.setToolTip("切换到浅色模式")
    
    def apply_theme(self):
        """应用主题"""
        # 暂时断开信号以防止循环调用
        self.theme_manager.theme_changed.disconnect()
        
        try:
            theme_id = self.theme_combo.currentData()
            if theme_id:
                self.theme_manager.set_theme(theme_id)
                self.theme_changed.emit(theme_id)
        finally:
            # 重新连接信号
            self.theme_manager.theme_changed.connect(self.on_theme_manager_changed)
    
    def toggle_mode(self):
        """切换模式"""
        # 暂时断开信号以防止循环调用
        self.theme_manager.mode_changed.disconnect()
        
        try:
            current_mode = self.theme_manager.get_current_mode()
            new_mode = ThemeMode.DARK if current_mode == ThemeMode.LIGHT else ThemeMode.LIGHT
            self.theme_manager.set_mode(new_mode)
            self.mode_changed.emit(new_mode.value)
            
            # 更新按钮显示
            self.refresh_current_settings()
        finally:
            # 重新连接信号
            self.theme_manager.mode_changed.connect(self.on_mode_manager_changed)
