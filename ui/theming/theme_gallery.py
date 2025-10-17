"""
主题画廊 - 提供更好的主题浏览和管理界面
支持网格显示、筛选和预览功能
"""
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QGroupBox, QWidget, QScrollArea, QFrame,
    QCheckBox, QButtonGroup, QRadioButton,
    QMessageBox, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont

from .theme_manager import ThemeManager
from .theme_schema import Theme


class ThemeCard(QFrame):
    """主题卡片控件"""
    
    selected = Signal(str)  # 主题名称
    edit_requested = Signal(str)  # 编辑请求
    delete_requested = Signal(str)  # 删除请求
    
    def __init__(self, theme_name: str, theme_info: dict):
        super().__init__()
        self.theme_name = theme_name
        self.theme_info = theme_info
        self.is_selected = False
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFixedSize(250, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 主题预览区域
        self.preview_widget = self.create_preview()
        layout.addWidget(self.preview_widget)
        
        # 主题信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # 主题名称
        name_label = QLabel(self.theme_info.get('name', self.theme_name))
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(13)
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(name_label)
        
        # 作者和模式
        meta_layout = QHBoxLayout()
        meta_layout.setContentsMargins(0, 0, 0, 0)
        
        author = self.theme_info.get('author', '未知')
        if len(author) > 10:
            author = author[:8] + "..."
        author_label = QLabel(f"👤 {author}")
        author_label.setStyleSheet("color: #7F8C8D; font-size: 11px;")
        meta_layout.addWidget(author_label)
        
        meta_layout.addStretch()
        
        mode = self.theme_info.get('mode', 'light')
        mode_icon = "🌞" if mode == 'light' else "🌙"
        mode_label = QLabel(mode_icon)
        mode_label.setToolTip(f"{'亮色' if mode == 'light' else '暗色'}模式")
        meta_layout.addWidget(mode_label)
        
        info_layout.addLayout(meta_layout)
        layout.addLayout(info_layout)
        
        # 操作按钮区域（默认隐藏）
        self.actions_widget = self.create_actions()
        self.actions_widget.setVisible(False)
        layout.addWidget(self.actions_widget)
        
        self.update_selection_style()
    
    def create_preview(self) -> QWidget:
        """创建主题预览"""
        preview = QFrame()
        preview.setFixedHeight(90)
        preview.setFrameStyle(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout(preview)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # 获取主题颜色
        mode = self.theme_info.get('mode', 'light')
        accent = self.theme_info.get('accent', '#007ACC')
        
        if mode == 'light':
            bg_color = '#FFFFFF'
            text_color = '#333333'
            secondary_bg = '#F8F9FA'
        else:
            bg_color = '#2C3E50'
            text_color = '#E0E0E0'
            secondary_bg = '#34495E'
        
        # 设置预览背景
        preview.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {accent};
                border-radius: 6px;
            }}
        """)
        
        # 模拟标题栏
        title_bar = QFrame()
        title_bar.setFixedHeight(18)
        title_bar.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {accent}, stop:1 {self.adjust_color(accent, 0.8)});
            border-radius: 3px;
        """)
        layout.addWidget(title_bar)
        
        # 模拟内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(4)
        
        # 侧边栏模拟
        sidebar = QFrame()
        sidebar.setFixedWidth(30)
        sidebar.setStyleSheet(f"""
            background-color: {secondary_bg};
            border-radius: 2px;
        """)
        content_layout.addWidget(sidebar)
        
        # 主内容模拟
        main_content = QVBoxLayout()
        main_content.setSpacing(2)
        
        # 模拟按钮
        button = QFrame()
        button.setFixedHeight(12)
        button.setStyleSheet(f"""
            background-color: {accent};
            border-radius: 2px;
        """)
        main_content.addWidget(button)
        
        # 模拟文本行
        for _ in range(2):
            text_line = QFrame()
            text_line.setFixedHeight(6)
            text_line.setStyleSheet(f"""
                background-color: {text_color};
                border-radius: 1px;
            """)
            main_content.addWidget(text_line)
        
        main_content.addStretch()
        
        content_widget = QWidget()
        content_widget.setLayout(main_content)
        content_layout.addWidget(content_widget)
        
        layout.addLayout(content_layout)
        
        return preview
    
    def adjust_color(self, color: str, factor: float) -> str:
        """调整颜色亮度"""
        try:
            qcolor = QColor(color)
            h = qcolor.hue()
            s = qcolor.saturation()
            v = qcolor.value()
            v = int(v * factor)
            qcolor.setHsv(h, s, min(255, max(0, v)))
            return qcolor.name()
        except Exception as e:
            print(f"调整颜色时出错: {e}")
            return color
    
    def create_actions(self) -> QWidget:
        """创建操作按钮"""
        actions = QWidget()
        layout = QHBoxLayout(actions)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setToolTip("编辑主题")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                border-radius: 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.theme_name))
        layout.addWidget(edit_btn)
        
        # 只有非默认主题才显示删除按钮
        if not self.theme_name.startswith('Default') and not self.theme_name.startswith('default_'):
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(24, 24)
            delete_btn.setToolTip("删除主题")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #DC3545;
                    color: white;
                    border-radius: 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #C82333;
                }
            """)
            delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.theme_name))
            layout.addWidget(delete_btn)
        
        layout.addStretch()
        
        return actions
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_selected(True)
            self.selected.emit(self.theme_name)
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self.actions_widget.setVisible(True)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.actions_widget.setVisible(False)
        super().leaveEvent(event)
    
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
                    border-radius: 12px;
                    background-color: #F0F8FF;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    border: 2px solid #E0E0E0;
                    border-radius: 12px;
                    background-color: #FAFAFA;
                }
                QFrame:hover {
                    border-color: #007ACC;
                    background-color: #F8F8F8;
                    transform: translateY(-2px);
                }
            """)


class ThemeGalleryDialog(QDialog):
    """主题画廊对话框"""
    
    theme_selected = Signal(str)  # 主题选择信号
    
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.theme_cards = {}
        self.current_filter = 'all'  # all, light, dark
        self.current_sort = 'name'   # name, date, author
        
        self.setWindowTitle("主题画廊")
        self.setModal(True)
        self.resize(900, 650)
        self.setup_ui()
        self.load_themes()
    
    def setup_ui(self):
        """设置界面"""
        main_layout = QVBoxLayout(self)
        
        # 顶部工具栏
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # 主题网格区域
        self.scroll_area = QScrollArea()
        self.themes_container = QWidget()
        self.themes_layout = QGridLayout(self.themes_container)
        self.themes_layout.setSpacing(15)
        
        self.scroll_area.setWidget(self.themes_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        main_layout.addWidget(self.scroll_area)
        
        # 底部状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel()
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        status_layout.addWidget(close_btn)
        
        main_layout.addLayout(status_layout)
    
    def create_toolbar(self) -> QWidget:
        """创建工具栏"""
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.Shape.StyledPanel)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 搜索框
        layout.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索主题...")
        self.search_edit.setMaximumWidth(200)
        self.search_edit.textChanged.connect(self.filter_themes)
        layout.addWidget(self.search_edit)
        
        layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        
        # 模式筛选
        layout.addWidget(QLabel("模式:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "亮色模式", "暗色模式"])
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        layout.addWidget(self.filter_combo)
        
        layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        
        # 排序方式
        layout.addWidget(QLabel("排序:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["按名称", "按创建时间", "按作者"])
        self.sort_combo.currentTextChanged.connect(self.on_sort_changed)
        layout.addWidget(self.sort_combo)
        
        layout.addStretch()
        
        # 新建主题按钮
        create_btn = QPushButton("✨ 新建主题")
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        create_btn.clicked.connect(self.create_new_theme)
        layout.addWidget(create_btn)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setToolTip("刷新主题列表")
        refresh_btn.clicked.connect(self.load_themes)
        layout.addWidget(refresh_btn)
        
        return toolbar
    
    def load_themes(self):
        """加载主题"""
        # 清理现有卡片
        for card in self.theme_cards.values():
            card.setParent(None)
        self.theme_cards.clear()
        
        # 获取主题列表
        theme_names = self.theme_manager.get_available_themes()
        
        row = 0
        col = 0
        displayed_count = 0
        
        for theme_name in theme_names:
            theme_info = self.theme_manager.get_theme_info(theme_name)
            if not theme_info:
                continue
            
            # 应用筛选
            if not self.should_show_theme(theme_name, theme_info):
                continue
            
            # 创建主题卡片
            card = ThemeCard(theme_name, theme_info)
            card.selected.connect(self.on_theme_selected)
            card.edit_requested.connect(self.edit_theme)
            card.delete_requested.connect(self.delete_theme)
            
            self.theme_cards[theme_name] = card
            self.themes_layout.addWidget(card, row, col)
            
            displayed_count += 1
            col += 1
            if col >= 3:  # 每行3个主题
                col = 0
                row += 1
        
        # 更新状态信息
        total_count = len(theme_names)
        self.status_label.setText(f"显示 {displayed_count} / {total_count} 个主题")
    
    def should_show_theme(self, theme_name: str, theme_info: dict) -> bool:
        """判断是否应该显示主题"""
        # 搜索筛选
        search_text = self.search_edit.text().lower()
        if search_text:
            if (search_text not in theme_name.lower() and 
                search_text not in theme_info.get('description', '').lower() and
                search_text not in theme_info.get('author', '').lower()):
                return False
        
        # 模式筛选
        if self.current_filter == 'light':
            return theme_info.get('mode', 'light') == 'light'
        elif self.current_filter == 'dark':
            return theme_info.get('mode', 'light') == 'dark'
        
        return True
    
    def filter_themes(self):
        """筛选主题"""
        self.load_themes()
    
    def on_filter_changed(self, filter_text: str):
        """筛选模式改变"""
        filter_mapping = {
            "全部": 'all',
            "亮色模式": 'light',
            "暗色模式": 'dark'
        }
        self.current_filter = filter_mapping.get(filter_text, 'all')
        self.load_themes()
    
    def on_sort_changed(self, sort_text: str):
        """排序方式改变"""
        sort_mapping = {
            "按名称": 'name',
            "按创建时间": 'date',
            "按作者": 'author'
        }
        self.current_sort = sort_mapping.get(sort_text, 'name')
        # TODO: 实现排序功能
        self.load_themes()
    
    def on_theme_selected(self, theme_name: str):
        """主题被选中"""
        # 取消其他主题的选中状态
        for name, card in self.theme_cards.items():
            card.set_selected(name == theme_name)
        
        # 切换到选中的主题
        success = self.theme_manager.switch_theme(theme_name)
        if success:
            self.theme_selected.emit(theme_name)
    
    def edit_theme(self, theme_name: str):
        """编辑主题"""
        editor = self.theme_manager.open_theme_editor(self, theme_name)
        if editor:
            editor.exec()
            self.load_themes()  # 刷新显示
    
    def delete_theme(self, theme_name: str):
        """删除主题"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除主题 '{theme_name}' 吗？\n此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.theme_manager.delete_theme(theme_name)
            if success:
                self.load_themes()  # 刷新显示
                QMessageBox.information(self, "成功", f"主题 '{theme_name}' 已删除。")
    
    def create_new_theme(self):
        """创建新主题"""
        from .theme_creator import ThemeCreatorDialog
        
        creator = ThemeCreatorDialog(self.theme_manager, self)
        creator.theme_created.connect(self.on_new_theme_created)
        creator.exec()
    
    def on_new_theme_created(self, theme_name: str):
        """新主题创建完成"""
        self.load_themes()
        # 选中新创建的主题
        if theme_name in self.theme_cards:
            self.theme_cards[theme_name].set_selected(True)
            self.theme_manager.switch_theme(theme_name)
