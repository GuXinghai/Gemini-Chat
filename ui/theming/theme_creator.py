"""
主题创建器 - 提供可视化的新建主题界面
支持从模板创建、自定义配置和实时预览
"""
from typing import Dict, List, Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QGroupBox, QTabWidget, QWidget, QScrollArea,
    QTextEdit, QCheckBox, QButtonGroup, QRadioButton,
    QMessageBox, QFrame, QSlider, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor

from .theme_schema import (
    Theme, ThemeMode, RegionPreset, ThemeMeta,
    create_default_light_theme, create_default_dark_theme,
    RegionNames, PaletteTokens, ComponentDensity
)
from .theme_manager import ThemeManager
from .color_utils import ColorUtils


class ThemeTemplateCard(QFrame):
    """主题模板卡片"""
    
    selected = Signal(str)  # 模板名称
    
    def __init__(self, template_name: str, template_info: dict):
        super().__init__()
        self.template_name = template_name
        self.template_info = template_info
        self.is_selected = False
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFixedSize(200, 150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 预览区域
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        preview_frame.setFixedHeight(80)
        self.setup_preview(preview_frame)
        layout.addWidget(preview_frame)
        
        # 模板信息
        name_label = QLabel(self.template_info.get('display_name', self.template_name))
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        desc_label = QLabel(self.template_info.get('description', ''))
        desc_label.setStyleSheet("color: #666; font-size: 12px;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        self.update_selection_style()
    
    def setup_preview(self, preview_frame: QFrame):
        """设置预览区域"""
        layout = QVBoxLayout(preview_frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        
        # 创建简单的预览效果
        colors = self.template_info.get('colors', {})
        bg_color = colors.get('background', '#FFFFFF')
        accent_color = colors.get('accent', '#007ACC')
        text_color = colors.get('text', '#333333')
        
        # 模拟窗口标题栏
        title_bar = QFrame()
        title_bar.setFixedHeight(16)
        title_bar.setStyleSheet(f"background-color: {bg_color}; border: 1px solid #CCC;")
        layout.addWidget(title_bar)
        
        # 模拟内容区域
        content_area = QFrame()
        content_area.setStyleSheet(f"""
            background-color: {bg_color};
            border: 1px solid #CCC;
            border-top: none;
        """)
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(2)
        
        # 模拟按钮
        button_frame = QFrame()
        button_frame.setFixedHeight(12)
        button_frame.setStyleSheet(f"""
            background-color: {accent_color};
            border-radius: 2px;
        """)
        content_layout.addWidget(button_frame)
        
        # 模拟文本
        text_frame = QFrame()
        text_frame.setFixedHeight(8)
        text_frame.setStyleSheet(f"""
            background-color: {text_color};
            border-radius: 1px;
        """)
        content_layout.addWidget(text_frame)
        
        layout.addWidget(content_area)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_selected(True)
            self.selected.emit(self.template_name)
        super().mousePressEvent(event)
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.is_selected = selected
        self.update_selection_style()
    
    def update_selection_style(self):
        """更新选中样式"""
        if self.is_selected:
            self.setStyleSheet("""
                QFrame {
                    border: 3px solid #007ACC;
                    border-radius: 8px;
                    background-color: #F0F8FF;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    border: 2px solid #E0E0E0;
                    border-radius: 8px;
                    background-color: #FAFAFA;
                }
                QFrame:hover {
                    border-color: #007ACC;
                    background-color: #F8F8F8;
                }
            """)


class ColorSchemePreview(QWidget):
    """颜色方案预览控件"""
    
    def __init__(self, colors: dict):
        super().__init__()
        self.colors = colors
        self.setFixedSize(150, 100)
    
    def paintEvent(self, event):
        """绘制颜色预览"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景色
        bg_color = QColor(self.colors.get('background', '#FFFFFF'))
        painter.fillRect(self.rect(), bg_color)
        
        # 绘制主色条带
        accent_color = QColor(self.colors.get('accent', '#007ACC'))
        painter.fillRect(0, 0, self.width(), 20, accent_color)
        
        # 绘制文本颜色示例
        text_color = QColor(self.colors.get('text', '#333333'))
        painter.setPen(text_color)
        painter.drawText(10, 40, "示例文本")
        painter.drawText(10, 60, "Sample Text")
        
        # 绘制边框
        painter.setPen(QColor('#CCC'))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))


class ThemeCreatorDialog(QDialog):
    """主题创建器对话框"""
    
    theme_created = Signal(str)  # 发送创建的主题名称
    
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.selected_template = None
        self.template_cards = {}
        
        self.setWindowTitle("创建新主题")
        self.setModal(True)
        self.resize(800, 600)
        self.setup_ui()
        self.setup_templates()
    
    def setup_ui(self):
        """设置界面"""
        main_layout = QVBoxLayout(self)
        
        # 创建选项卡
        tabs = QTabWidget()
        
        # 从模板创建标签页
        template_tab = self.create_template_tab()
        tabs.addTab(template_tab, "从模板创建")
        
        # 自定义创建标签页
        custom_tab = self.create_custom_tab()
        tabs.addTab(custom_tab, "自定义创建")
        
        main_layout.addWidget(tabs)
        
        # 底部按钮
        self.create_bottom_buttons(main_layout)
    
    def create_template_tab(self) -> QWidget:
        """创建模板选择标签页"""
        widget = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # 标题和说明
        title = QLabel("选择主题模板")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        desc = QLabel("从预设模板快速创建主题，您可以稍后进行自定义修改。")
        desc.setStyleSheet("color: #666; margin: 5px 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 模板网格
        self.templates_layout = QGridLayout()
        self.templates_layout.setSpacing(15)
        layout.addWidget(QWidget())  # 占位符，实际模板在setup_templates中添加
        
        # 临时容器
        templates_container = QWidget()
        templates_container.setLayout(self.templates_layout)
        layout.addWidget(templates_container)
        
        layout.addStretch()
        
        widget.setWidget(content)
        widget.setWidgetResizable(True)
        return widget
    
    def create_custom_tab(self) -> QWidget:
        """创建自定义配置标签页"""
        widget = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # 基础配置组
        basic_group = QGroupBox("基础配置")
        basic_layout = QGridLayout(basic_group)
        
        basic_layout.addWidget(QLabel("主题名称:"), 0, 0)
        self.custom_name_edit = QLineEdit()
        self.custom_name_edit.setPlaceholderText("输入主题名称")
        basic_layout.addWidget(self.custom_name_edit, 0, 1)
        
        basic_layout.addWidget(QLabel("作者:"), 1, 0)
        self.custom_author_edit = QLineEdit()
        self.custom_author_edit.setPlaceholderText("输入作者名称")
        basic_layout.addWidget(self.custom_author_edit, 1, 1)
        
        basic_layout.addWidget(QLabel("描述:"), 2, 0)
        self.custom_desc_edit = QTextEdit()
        self.custom_desc_edit.setMaximumHeight(80)
        self.custom_desc_edit.setPlaceholderText("输入主题描述")
        basic_layout.addWidget(self.custom_desc_edit, 2, 1)
        
        layout.addWidget(basic_group)
        
        # 主题模式选择
        mode_group = QGroupBox("主题模式")
        mode_layout = QHBoxLayout(mode_group)
        
        self.mode_button_group = QButtonGroup()
        self.light_mode_rb = QRadioButton("亮色模式")
        self.dark_mode_rb = QRadioButton("暗色模式")
        self.light_mode_rb.setChecked(True)
        
        self.mode_button_group.addButton(self.light_mode_rb)
        self.mode_button_group.addButton(self.dark_mode_rb)
        
        mode_layout.addWidget(self.light_mode_rb)
        mode_layout.addWidget(self.dark_mode_rb)
        mode_layout.addStretch()
        
        layout.addWidget(mode_group)
        
        # 颜色配置
        color_group = QGroupBox("颜色配置")
        color_layout = QGridLayout(color_group)
        
        color_layout.addWidget(QLabel("主色调:"), 0, 0)
        self.custom_accent_btn = self.create_color_button("#007ACC")
        color_layout.addWidget(self.custom_accent_btn, 0, 1)
        
        color_layout.addWidget(QLabel("背景色:"), 1, 0)
        self.custom_bg_btn = self.create_color_button("#FFFFFF")
        color_layout.addWidget(self.custom_bg_btn, 1, 1)
        
        color_layout.addWidget(QLabel("文本色:"), 2, 0)
        self.custom_text_btn = self.create_color_button("#333333")
        color_layout.addWidget(self.custom_text_btn, 2, 1)
        
        layout.addWidget(color_group)
        
        # 样式选项
        style_group = QGroupBox("样式选项")
        style_layout = QVBoxLayout(style_group)
        
        self.rounded_corners_cb = QCheckBox("使用圆角")
        self.rounded_corners_cb.setChecked(True)
        style_layout.addWidget(self.rounded_corners_cb)
        
        self.shadows_cb = QCheckBox("启用阴影效果")
        self.shadows_cb.setChecked(True)
        style_layout.addWidget(self.shadows_cb)
        
        self.animations_cb = QCheckBox("启用动画")
        self.animations_cb.setChecked(True)
        style_layout.addWidget(self.animations_cb)
        
        layout.addWidget(style_group)
        
        # 预览区域
        preview_group = QGroupBox("实时预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.custom_preview = ColorSchemePreview({
            'background': '#FFFFFF',
            'accent': '#007ACC',
            'text': '#333333'
        })
        preview_layout.addWidget(self.custom_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(preview_group)
        
        layout.addStretch()
        
        # 连接信号以更新预览
        self.light_mode_rb.toggled.connect(self.update_custom_preview)
        self.dark_mode_rb.toggled.connect(self.update_custom_preview)
        
        widget.setWidget(content)
        widget.setWidgetResizable(True)
        return widget
    
    def create_color_button(self, initial_color: str) -> QPushButton:
        """创建颜色选择按钮"""
        button = QPushButton()
        button.setFixedSize(60, 30)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {initial_color};
                border: 2px solid #CCC;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border-color: #007ACC;
            }}
        """)
        button.clicked.connect(lambda: self.pick_color(button))
        button.setProperty("color_value", initial_color)
        return button
    
    def pick_color(self, button: QPushButton):
        """打开颜色选择器"""
        from PySide6.QtWidgets import QColorDialog
        
        color_dialog = QColorDialog()
        current_color = button.property("color_value")
        color_dialog.setCurrentColor(QColor(current_color))
        
        if color_dialog.exec():
            new_color = color_dialog.currentColor().name()
            button.setProperty("color_value", new_color)
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {new_color};
                    border: 2px solid #CCC;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border-color: #007ACC;
                }}
            """)
            self.update_custom_preview()
    
    def update_custom_preview(self):
        """更新自定义预览"""
        if hasattr(self, 'custom_preview'):
            colors = {
                'background': self.custom_bg_btn.property("color_value"),
                'accent': self.custom_accent_btn.property("color_value"),
                'text': self.custom_text_btn.property("color_value")
            }
            
            # 如果是暗色模式，自动调整颜色
            if self.dark_mode_rb.isChecked():
                if colors['background'] == '#FFFFFF':
                    colors['background'] = '#2B2B2B'
                if colors['text'] == '#333333':
                    colors['text'] = '#E0E0E0'
            
            self.custom_preview.colors = colors
            self.custom_preview.update()
    
    def setup_templates(self):
        """设置预定义模板"""
        templates = {
            'modern_light': {
                'display_name': '现代亮色',
                'description': '简洁现代的亮色主题',
                'colors': {
                    'background': '#FFFFFF',
                    'accent': '#007ACC',
                    'text': '#333333'
                },
                'base_theme': 'light'
            },
            'modern_dark': {
                'display_name': '现代暗色',
                'description': '简洁现代的暗色主题',
                'colors': {
                    'background': '#2B2B2B',
                    'accent': '#00D2FF',
                    'text': '#E0E0E0'
                },
                'base_theme': 'dark'
            },
            'warm_light': {
                'display_name': '温暖亮色',
                'description': '温暖舒适的亮色主题',
                'colors': {
                    'background': '#FDF6E3',
                    'accent': '#CB4B16',
                    'text': '#657B83'
                },
                'base_theme': 'light'
            },
            'cool_dark': {
                'display_name': '冷色暗黑',
                'description': '冷静专业的暗色主题',
                'colors': {
                    'background': '#1E1E1E',
                    'accent': '#4FC3F7',
                    'text': '#CCCCCC'
                },
                'base_theme': 'dark'
            },
            'nature_green': {
                'display_name': '自然绿色',
                'description': '清新自然的绿色主题',
                'colors': {
                    'background': '#F8FFFA',
                    'accent': '#4CAF50',
                    'text': '#2E7D32'
                },
                'base_theme': 'light'
            },
            'sunset_orange': {
                'display_name': '日落橙色',
                'description': '温暖活力的橙色主题',
                'colors': {
                    'background': '#FFF8F0',
                    'accent': '#FF9800',
                    'text': '#BF360C'
                },
                'base_theme': 'light'
            }
        }
        
        row = 0
        col = 0
        for template_name, template_info in templates.items():
            card = ThemeTemplateCard(template_name, template_info)
            card.selected.connect(self.on_template_selected)
            self.template_cards[template_name] = card
            
            self.templates_layout.addWidget(card, row, col)
            
            col += 1
            if col >= 3:  # 每行3个模板
                col = 0
                row += 1
    
    def on_template_selected(self, template_name: str):
        """模板被选中"""
        # 取消其他模板的选中状态
        for name, card in self.template_cards.items():
            card.set_selected(name == template_name)
        
        self.selected_template = template_name
    
    def create_bottom_buttons(self, parent_layout):
        """创建底部按钮"""
        buttons_layout = QHBoxLayout()
        
        # 预览按钮
        preview_btn = QPushButton("预览主题")
        preview_btn.clicked.connect(self.preview_theme)
        buttons_layout.addWidget(preview_btn)
        
        buttons_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        # 创建按钮
        self.create_btn = QPushButton("创建主题")
        self.create_btn.clicked.connect(self.create_theme)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        """)
        buttons_layout.addWidget(self.create_btn)
        
        parent_layout.addLayout(buttons_layout)
    
    def preview_theme(self):
        """预览主题"""
        # TODO: 实现主题预览功能
        QMessageBox.information(self, "提示", "主题预览功能开发中...")
    
    def create_theme(self):
        """创建主题"""
        try:
            # 获取当前选中的标签页
            current_tab = self.sender().parent()
            tab_widget = self.findChild(QTabWidget)
            
            if tab_widget and tab_widget.currentIndex() == 0:  # 从模板创建
                if not self.selected_template:
                    QMessageBox.warning(self, "警告", "请选择一个主题模板。")
                    return
                
                theme = self.create_from_template()
            else:  # 自定义创建
                if not self.custom_name_edit.text().strip():
                    QMessageBox.warning(self, "警告", "请输入主题名称。")
                    return
                
                theme = self.create_custom_theme()
            
            if theme:
                # 保存主题
                success = self.theme_manager.save_theme(theme, theme.meta.name)
                if success:
                    QMessageBox.information(self, "成功", f"主题 '{theme.meta.name}' 创建成功！")
                    self.theme_created.emit(theme.meta.name)
                    self.accept()
                else:
                    QMessageBox.critical(self, "错误", "主题保存失败。")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建主题时发生错误：{str(e)}")
    
    def create_from_template(self) -> Optional[Theme]:
        """从模板创建主题"""
        if not self.selected_template:
            return None
        
        template_info = None
        for card in self.template_cards.values():
            if card.template_name == self.selected_template:
                template_info = card.template_info
                break
        
        if not template_info:
            return None
        
        # 获取用户输入的主题名称
        from PySide6.QtWidgets import QInputDialog
        theme_name, ok = QInputDialog.getText(
            self, "主题名称", 
            f"请输入基于 '{template_info['display_name']}' 的新主题名称:",
            text=template_info['display_name']
        )
        
        if not ok or not theme_name.strip():
            return None
        
        # 基于模板创建主题
        if template_info['base_theme'] == 'light':
            theme = create_default_light_theme()
        else:
            theme = create_default_dark_theme()
        
        # 更新主题信息
        theme.meta.name = theme_name.strip()
        theme.meta.description = template_info['description']
        
        # 应用模板颜色
        colors = template_info['colors']
        theme.palette.accent = colors.get('accent', theme.palette.accent)
        
        # 根据模板调整中性色阶
        if template_info['base_theme'] == 'dark':
            theme.palette.mode = ThemeMode.DARK
        
        return theme
    
    def create_custom_theme(self) -> Optional[Theme]:
        """创建自定义主题"""
        theme_name = self.custom_name_edit.text().strip()
        if not theme_name:
            return None
        
        # 创建基础主题
        if self.light_mode_rb.isChecked():
            theme = create_default_light_theme()
        else:
            theme = create_default_dark_theme()
        
        # 更新主题信息
        theme.meta.name = theme_name
        theme.meta.author = self.custom_author_edit.text().strip()
        theme.meta.description = self.custom_desc_edit.toPlainText().strip()
        
        # 应用自定义颜色
        theme.palette.accent = self.custom_accent_btn.property("color_value")
        
        return theme
