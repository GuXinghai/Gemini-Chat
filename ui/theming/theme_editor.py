"""
主题编辑器 - 提供可视化的主题编辑界面
支持实时预览和受控的自定义选项
"""
from typing import Dict, List, Optional, Callable
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox,
    QSlider, QColorDialog, QFileDialog, QTextEdit,
    QGroupBox, QTabWidget, QWidget, QScrollArea,
    QListWidget, QListWidgetItem, QFrame, QCheckBox,
    QSplitter, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QObject
from PySide6.QtGui import QColor, QPalette, QPixmap, QPainter

from .theme_schema import (
    Theme, ThemeMode, RegionPreset, GradientType, ImageFit,
    ColorStop, GradientConfig, SolidConfig, ImageConfig,
    ComponentDensity, ComponentShape, ComponentIntensity,
    create_default_light_theme, create_default_dark_theme,
    RegionNames
)
from .theme_engine import ThemeEngine
from .color_utils import ColorUtils, ContrastCalculator


class ColorPickerButton(QPushButton):
    """颜色选择器按钮"""
    
    color_changed = Signal(str)  # 颜色变化信号
    
    def __init__(self, initial_color: str = "#FFFFFF"):
        super().__init__()
        self.color = initial_color
        self.setFixedSize(40, 30)
        self.update_color_display()
        self.clicked.connect(self.pick_color)
    
    def update_color_display(self):
        """更新颜色显示"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color};
                border: 2px solid #CCCCCC;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border-color: #666666;
            }}
        """)
        self.setToolTip(f"颜色: {self.color}")
    
    def pick_color(self):
        """打开颜色选择器"""
        color_dialog = QColorDialog()
        color_dialog.setCurrentColor(QColor(self.color))
        
        if color_dialog.exec():
            selected_color = color_dialog.currentColor()
            self.set_color(selected_color.name())
    
    def set_color(self, color: str):
        """设置颜色"""
        self.color = color
        self.update_color_display()
        self.color_changed.emit(color)
    
    def get_color(self) -> str:
        """获取当前颜色"""
        return self.color


class GradientEditor(QWidget):
    """渐变编辑器"""
    
    gradient_changed = Signal()
    
    def __init__(self):
        super().__init__()
        self.gradient_config = GradientConfig(
            type=GradientType.LINEAR,
            stops=[
                ColorStop(0.0, "#FFFFFF"),
                ColorStop(1.0, "#000000")
            ],
            angle=135.0
        )
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        
        # 渐变类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["线性渐变", "径向渐变", "圆锥渐变"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # 角度控制（仅线性渐变）
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("角度:"))
        self.angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.angle_slider.setRange(0, 360)
        self.angle_slider.setValue(135)
        self.angle_slider.valueChanged.connect(self.on_angle_changed)
        angle_layout.addWidget(self.angle_slider)
        self.angle_label = QLabel("135°")
        angle_layout.addWidget(self.angle_label)
        layout.addLayout(angle_layout)
        
        # 色标编辑器
        stops_group = QGroupBox("色标")
        stops_layout = QVBoxLayout(stops_group)
        
        self.stops_list = QListWidget()
        stops_layout.addWidget(self.stops_list)
        
        # 色标控制按钮
        stops_buttons = QHBoxLayout()
        self.add_stop_btn = QPushButton("添加色标")
        self.add_stop_btn.clicked.connect(self.add_color_stop)
        self.remove_stop_btn = QPushButton("删除色标")
        self.remove_stop_btn.clicked.connect(self.remove_color_stop)
        stops_buttons.addWidget(self.add_stop_btn)
        stops_buttons.addWidget(self.remove_stop_btn)
        stops_buttons.addStretch()
        stops_layout.addLayout(stops_buttons)
        
        layout.addWidget(stops_group)
        
        # 初始化色标列表
        self.update_stops_list()
    
    def on_type_changed(self, text: str):
        """渐变类型改变"""
        type_mapping = {
            "线性渐变": GradientType.LINEAR,
            "径向渐变": GradientType.RADIAL,
            "圆锥渐变": GradientType.CONICAL
        }
        self.gradient_config.type = type_mapping[text]
        
        # 角度控制只对线性渐变有效
        is_linear = self.gradient_config.type == GradientType.LINEAR
        self.angle_slider.setVisible(is_linear)
        self.angle_label.setVisible(is_linear)
        
        self.gradient_changed.emit()
    
    def on_angle_changed(self, value: int):
        """角度改变"""
        self.gradient_config.angle = value
        self.angle_label.setText(f"{value}°")
        self.gradient_changed.emit()
    
    def add_color_stop(self):
        """添加色标"""
        if len(self.gradient_config.stops) >= 4:
            QMessageBox.warning(self, "警告", "最多支持4个色标")
            return
        
        # 在中间位置添加新色标
        position = 0.5
        color = "#808080"
        new_stop = ColorStop(position, color)
        self.gradient_config.stops.append(new_stop)
        self.gradient_config.stops.sort(key=lambda x: x.position)
        
        self.update_stops_list()
        self.gradient_changed.emit()
    
    def remove_color_stop(self):
        """删除色标"""
        current_row = self.stops_list.currentRow()
        if current_row >= 0 and len(self.gradient_config.stops) > 2:
            del self.gradient_config.stops[current_row]
            self.update_stops_list()
            self.gradient_changed.emit()
        elif len(self.gradient_config.stops) <= 2:
            QMessageBox.warning(self, "警告", "至少需要2个色标")
    
    def update_stops_list(self):
        """更新色标列表显示"""
        self.stops_list.clear()
        for i, stop in enumerate(self.gradient_config.stops):
            item_widget = self.create_stop_item_widget(i, stop)
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            self.stops_list.addItem(item)
            self.stops_list.setItemWidget(item, item_widget)
    
    def create_stop_item_widget(self, index: int, stop: ColorStop) -> QWidget:
        """创建色标项控件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 位置滑块
        layout.addWidget(QLabel("位置:"))
        position_slider = QSlider(Qt.Orientation.Horizontal)
        position_slider.setRange(0, 100)
        position_slider.setValue(int(stop.position * 100))
        position_slider.valueChanged.connect(
            lambda value, idx=index: self.on_stop_position_changed(idx, value / 100.0)
        )
        layout.addWidget(position_slider)
        
        # 颜色选择器
        color_picker = ColorPickerButton(stop.color)
        color_picker.color_changed.connect(
            lambda color, idx=index: self.on_stop_color_changed(idx, color)
        )
        layout.addWidget(color_picker)
        
        return widget
    
    def on_stop_position_changed(self, index: int, position: float):
        """色标位置改变"""
        if 0 <= index < len(self.gradient_config.stops):
            self.gradient_config.stops[index].position = position
            self.gradient_config.stops.sort(key=lambda x: x.position)
            self.gradient_changed.emit()
    
    def on_stop_color_changed(self, index: int, color: str):
        """色标颜色改变"""
        if 0 <= index < len(self.gradient_config.stops):
            self.gradient_config.stops[index].color = color
            self.gradient_changed.emit()


class RegionEditor(QWidget):
    """区域编辑器"""
    
    region_changed = Signal()
    
    def __init__(self, region_name: str):
        super().__init__()
        self.region_name = region_name
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        
        # 区域标题
        title_label = QLabel(f"区域: {self.region_name}")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # 背景类型选择
        type_group = QGroupBox("背景类型")
        type_layout = QVBoxLayout(type_group)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["纯色", "渐变", "图片"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        
        layout.addWidget(type_group)
        
        # 配置区域（堆叠布局）
        self.config_stack = QTabWidget()
        
        # 纯色配置
        self.solid_widget = self.create_solid_config_widget()
        self.config_stack.addTab(self.solid_widget, "纯色")
        
        # 渐变配置
        self.gradient_widget = GradientEditor()
        self.gradient_widget.gradient_changed.connect(self.region_changed.emit)
        self.config_stack.addTab(self.gradient_widget, "渐变")
        
        # 图片配置
        self.image_widget = self.create_image_config_widget()
        self.config_stack.addTab(self.image_widget, "图片")
        
        layout.addWidget(self.config_stack)
        
        # 设置初始显示
        self.on_type_changed("纯色")
    
    def create_solid_config_widget(self) -> QWidget:
        """创建纯色配置控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 颜色选择
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("颜色:"))
        self.solid_color_picker = ColorPickerButton("#FFFFFF")
        self.solid_color_picker.color_changed.connect(self.region_changed.emit)
        color_layout.addWidget(self.solid_color_picker)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # 透明度控制
        alpha_layout = QHBoxLayout()
        alpha_layout.addWidget(QLabel("透明度:"))
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(100)
        self.alpha_slider.valueChanged.connect(self.on_alpha_changed)
        alpha_layout.addWidget(self.alpha_slider)
        self.alpha_label = QLabel("100%")
        alpha_layout.addWidget(self.alpha_label)
        layout.addLayout(alpha_layout)
        
        layout.addStretch()
        return widget
    
    def create_image_config_widget(self) -> QWidget:
        """创建图片配置控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 图片选择
        image_layout = QHBoxLayout()
        image_layout.addWidget(QLabel("图片:"))
        self.image_path_edit = QLineEdit()
        self.image_path_edit.textChanged.connect(self.region_changed.emit)
        image_layout.addWidget(self.image_path_edit)
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_image)
        image_layout.addWidget(self.browse_btn)
        layout.addLayout(image_layout)
        
        # 适配方式
        fit_layout = QHBoxLayout()
        fit_layout.addWidget(QLabel("适配:"))
        self.fit_combo = QComboBox()
        self.fit_combo.addItems(["覆盖", "包含", "平铺"])
        self.fit_combo.currentTextChanged.connect(self.region_changed.emit)
        fit_layout.addWidget(self.fit_combo)
        fit_layout.addStretch()
        layout.addLayout(fit_layout)
        
        # 不透明度
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("不透明度:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("100%")
        opacity_layout.addWidget(self.opacity_label)
        layout.addLayout(opacity_layout)
        
        # 模糊效果
        blur_layout = QHBoxLayout()
        blur_layout.addWidget(QLabel("模糊:"))
        self.blur_combo = QComboBox()
        self.blur_combo.addItems(["关闭", "轻微", "中等"])
        self.blur_combo.currentTextChanged.connect(self.region_changed.emit)
        blur_layout.addWidget(self.blur_combo)
        blur_layout.addStretch()
        layout.addLayout(blur_layout)
        
        layout.addStretch()
        return widget
    
    def on_type_changed(self, text: str):
        """背景类型改变"""
        type_mapping = {"纯色": 0, "渐变": 1, "图片": 2}
        index = type_mapping.get(text, 0)
        self.config_stack.setCurrentIndex(index)
        self.region_changed.emit()
    
    def on_alpha_changed(self, value: int):
        """透明度改变"""
        self.alpha_label.setText(f"{value}%")
        self.region_changed.emit()
    
    def on_opacity_changed(self, value: int):
        """不透明度改变"""
        self.opacity_label.setText(f"{value}%")
        self.region_changed.emit()
    
    def browse_image(self):
        """浏览图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            self.image_path_edit.setText(file_path)


class ThemePreviewWidget(QWidget):
    """主题预览控件"""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(300, 200)
        self.setup_ui()
    
    def setup_ui(self):
        """设置预览界面"""
        layout = QVBoxLayout(self)
        
        # 模拟界面元素
        title = QLabel("预览窗口")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(title)
        
        # 模拟按钮
        button_layout = QHBoxLayout()
        btn1 = QPushButton("主要按钮")
        btn2 = QPushButton("次要按钮")
        button_layout.addWidget(btn1)
        button_layout.addWidget(btn2)
        layout.addLayout(button_layout)
        
        # 模拟输入框
        input_field = QLineEdit()
        input_field.setPlaceholderText("输入框示例")
        layout.addWidget(input_field)
        
        # 模拟文本
        text_label = QLabel("这是示例文本，用于预览主题效果。")
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        layout.addStretch()


class ThemeEditorDialog(QDialog):
    """主题编辑器对话框"""
    
    theme_applied = Signal(Theme)  # 主题应用信号
    
    def __init__(self, theme_engine: ThemeEngine, initial_theme: Optional[Theme] = None):
        super().__init__()
        self.theme_engine = theme_engine
        self.current_theme = initial_theme or create_default_light_theme()
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        
        self.setWindowTitle("主题编辑器")
        self.setModal(True)
        self.resize(1000, 700)
        self.setup_ui()
        self.load_theme_to_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        
        # 左侧：编辑面板
        edit_panel = self.create_edit_panel()
        layout.addWidget(edit_panel, 2)
        
        # 右侧：预览面板
        preview_panel = self.create_preview_panel()
        layout.addWidget(preview_panel, 1)
        
        # 底部按钮
        self.create_bottom_buttons(layout)
    
    def create_edit_panel(self) -> QWidget:
        """创建编辑面板"""
        panel = QTabWidget()
        
        # 基础设置标签页
        basic_tab = self.create_basic_tab()
        panel.addTab(basic_tab, "基础设置")
        
        # 区域设置标签页
        regions_tab = self.create_regions_tab()
        panel.addTab(regions_tab, "区域设置")
        
        # 组件设置标签页
        components_tab = self.create_components_tab()
        panel.addTab(components_tab, "组件设置")
        
        return panel
    
    def create_basic_tab(self) -> QWidget:
        """创建基础设置标签页"""
        widget = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # 主题信息
        info_group = QGroupBox("主题信息")
        info_layout = QGridLayout(info_group)
        
        info_layout.addWidget(QLabel("名称:"), 0, 0)
        self.name_edit = QLineEdit(self.current_theme.meta.name)
        self.name_edit.textChanged.connect(self.on_theme_changed)
        info_layout.addWidget(self.name_edit, 0, 1)
        
        info_layout.addWidget(QLabel("作者:"), 1, 0)
        self.author_edit = QLineEdit(self.current_theme.meta.author)
        self.author_edit.textChanged.connect(self.on_theme_changed)
        info_layout.addWidget(self.author_edit, 1, 1)
        
        info_layout.addWidget(QLabel("描述:"), 2, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlainText(self.current_theme.meta.description)
        self.description_edit.textChanged.connect(self.on_theme_changed)
        info_layout.addWidget(self.description_edit, 2, 1)
        
        layout.addWidget(info_group)
        
        # 颜色设置
        color_group = QGroupBox("颜色设置")
        color_layout = QGridLayout(color_group)
        
        # 主题模式
        color_layout.addWidget(QLabel("模式:"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["明亮", "暗黑"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        color_layout.addWidget(self.mode_combo, 0, 1)
        
        # 主色调
        color_layout.addWidget(QLabel("主色调:"), 1, 0)
        self.accent_picker = ColorPickerButton(self.current_theme.palette.accent)
        self.accent_picker.color_changed.connect(self.on_accent_changed)
        color_layout.addWidget(self.accent_picker, 1, 1)
        
        # 中性色阶编辑（简化版）
        color_layout.addWidget(QLabel("中性色阶:"), 2, 0)
        neutral_btn = QPushButton("编辑中性色...")
        neutral_btn.clicked.connect(self.edit_neutral_scale)
        color_layout.addWidget(neutral_btn, 2, 1)
        
        layout.addWidget(color_group)
        
        # 几何设置
        geometry_group = QGroupBox("几何设置")
        geometry_layout = QGridLayout(geometry_group)
        
        # 圆角设置
        geometry_layout.addWidget(QLabel("小圆角:"), 0, 0)
        self.radius_sm_edit = QLineEdit(self.current_theme.palette.radius.get('sm', '4px'))
        self.radius_sm_edit.textChanged.connect(self.on_theme_changed)
        geometry_layout.addWidget(self.radius_sm_edit, 0, 1)
        
        geometry_layout.addWidget(QLabel("中圆角:"), 1, 0)
        self.radius_md_edit = QLineEdit(self.current_theme.palette.radius.get('md', '8px'))
        self.radius_md_edit.textChanged.connect(self.on_theme_changed)
        geometry_layout.addWidget(self.radius_md_edit, 1, 1)
        
        geometry_layout.addWidget(QLabel("大圆角:"), 2, 0)
        self.radius_lg_edit = QLineEdit(self.current_theme.palette.radius.get('lg', '12px'))
        self.radius_lg_edit.textChanged.connect(self.on_theme_changed)
        geometry_layout.addWidget(self.radius_lg_edit, 2, 1)
        
        layout.addWidget(geometry_group)
        
        layout.addStretch()
        widget.setWidget(content)
        widget.setWidgetResizable(True)
        return widget
    
    def create_regions_tab(self) -> QWidget:
        """创建区域设置标签页"""
        widget = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # 区域编辑器列表
        self.region_editors = {}
        for region_name in [RegionNames.SIDEBAR, RegionNames.CHAT_PANEL, 
                           RegionNames.COMPOSER, RegionNames.TOOLBAR]:
            editor = RegionEditor(region_name)
            editor.region_changed.connect(self.on_theme_changed)
            self.region_editors[region_name] = editor
            layout.addWidget(editor)
        
        layout.addStretch()
        widget.setWidget(content)
        widget.setWidgetResizable(True)
        return widget
    
    def create_components_tab(self) -> QWidget:
        """创建组件设置标签页"""
        widget = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # 组件覆写设置（简化版）
        components_group = QGroupBox("组件样式覆写")
        components_layout = QVBoxLayout(components_group)
        
        # TODO: 实现组件覆写界面
        placeholder = QLabel("组件覆写设置功能开发中...")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        components_layout.addWidget(placeholder)
        
        layout.addWidget(components_group)
        layout.addStretch()
        
        widget.setWidget(content)
        widget.setWidgetResizable(True)
        return widget
    
    def create_preview_panel(self) -> QWidget:
        """创建预览面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # 预览标题
        title = QLabel("实时预览")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 预览控件
        self.preview_widget = ThemePreviewWidget()
        layout.addWidget(self.preview_widget)
        
        # 预览控制
        preview_controls = QHBoxLayout()
        self.auto_preview_cb = QCheckBox("自动预览")
        self.auto_preview_cb.setChecked(True)
        preview_controls.addWidget(self.auto_preview_cb)
        
        manual_preview_btn = QPushButton("手动预览")
        manual_preview_btn.clicked.connect(self.update_preview)
        preview_controls.addWidget(manual_preview_btn)
        
        layout.addLayout(preview_controls)
        layout.addStretch()
        
        return panel
    
    def create_bottom_buttons(self, parent_layout):
        """创建底部按钮"""
        buttons_layout = QHBoxLayout()
        
        # 预设主题按钮
        presets_btn = QPushButton("预设主题")
        presets_btn.clicked.connect(self.show_presets_menu)
        buttons_layout.addWidget(presets_btn)
        
        # 导入/导出按钮
        import_btn = QPushButton("导入主题")
        import_btn.clicked.connect(self.import_theme)
        buttons_layout.addWidget(import_btn)
        
        export_btn = QPushButton("导出主题")
        export_btn.clicked.connect(self.export_theme)
        buttons_layout.addWidget(export_btn)
        
        buttons_layout.addStretch()
        
        # 对话框按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self.apply_theme)
        buttons_layout.addWidget(apply_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept_and_apply)
        buttons_layout.addWidget(ok_btn)
        
        parent_layout.addLayout(buttons_layout)
    
    def on_theme_changed(self):
        """主题发生变化"""
        if self.auto_preview_cb.isChecked():
            # 延迟更新预览，避免频繁刷新
            self.preview_timer.start(300)
        
        # 更新当前主题对象
        self.update_theme_from_ui()
    
    def on_mode_changed(self, text: str):
        """主题模式改变"""
        from .theme_schema import ThemeMode
        self.current_theme.palette.mode = ThemeMode.LIGHT if text == "明亮" else ThemeMode.DARK
        self.on_theme_changed()
    
    def on_accent_changed(self, color: str):
        """主色调改变"""
        self.current_theme.palette.accent = color
        self.on_theme_changed()
    
    def update_theme_from_ui(self):
        """从界面更新主题对象"""
        # 更新基础信息
        self.current_theme.meta.name = self.name_edit.text()
        self.current_theme.meta.author = self.author_edit.text()
        self.current_theme.meta.description = self.description_edit.toPlainText()
        
        # 更新几何设置
        self.current_theme.palette.radius['sm'] = self.radius_sm_edit.text()
        self.current_theme.palette.radius['md'] = self.radius_md_edit.text()
        self.current_theme.palette.radius['lg'] = self.radius_lg_edit.text()
        
        # TODO: 更新区域和组件设置
    
    def load_theme_to_ui(self):
        """将主题加载到界面"""
        # 加载基础信息
        self.name_edit.setText(self.current_theme.meta.name)
        self.author_edit.setText(self.current_theme.meta.author)
        self.description_edit.setPlainText(self.current_theme.meta.description)
        
        # 加载颜色设置
        mode_text = "明亮" if self.current_theme.palette.mode.value == "light" else "暗黑"
        self.mode_combo.setCurrentText(mode_text)
        self.accent_picker.set_color(self.current_theme.palette.accent)
        
        # 加载几何设置
        self.radius_sm_edit.setText(self.current_theme.palette.radius.get('sm', '4px'))
        self.radius_md_edit.setText(self.current_theme.palette.radius.get('md', '8px'))
        self.radius_lg_edit.setText(self.current_theme.palette.radius.get('lg', '12px'))
        
        # TODO: 加载区域和组件设置
    
    def update_preview(self):
        """更新预览"""
        try:
            # 仅在预览控件上应用主题
            from .color_utils import SemanticColorDeriver
            semantic = SemanticColorDeriver.derive_semantic_colors(self.current_theme.palette)
            
            # 简单的预览样式
            preview_style = f"""
            QWidget {{
                background-color: {semantic.get('window', '#FFFFFF')};
                color: {semantic.get('text_primary', '#000000')};
            }}
            QPushButton {{
                background-color: {semantic.get('control_bg', '#F0F0F0')};
                color: {semantic.get('control_fg', '#000000')};
                border: 1px solid {semantic.get('border', '#CCCCCC')};
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {semantic.get('state_hover', '#E0E0E0')};
            }}
            QLineEdit {{
                background-color: {semantic.get('surface', '#FFFFFF')};
                color: {semantic.get('text_primary', '#000000')};
                border: 1px solid {semantic.get('border', '#CCCCCC')};
                padding: 4px 8px;
                border-radius: 4px;
            }}
            """
            self.preview_widget.setStyleSheet(preview_style)
            
        except Exception as e:
            print(f"更新预览失败: {e}")
    
    def show_presets_menu(self):
        """显示预设主题菜单"""
        # TODO: 实现预设主题选择
        QMessageBox.information(self, "提示", "预设主题功能开发中...")
    
    def edit_neutral_scale(self):
        """编辑中性色阶"""
        # TODO: 实现中性色阶编辑对话框
        QMessageBox.information(self, "提示", "中性色阶编辑功能开发中...")
    
    def import_theme(self):
        """导入主题"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入主题", "", "主题文件 (*.json)"
        )
        if file_path:
            try:
                theme = Theme.load_from_file(Path(file_path))
                self.current_theme = theme
                self.load_theme_to_ui()
                self.on_theme_changed()
                QMessageBox.information(self, "成功", "主题导入成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入主题失败：{e}")
    
    def export_theme(self):
        """导出主题"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出主题", f"{self.current_theme.meta.name}.json", "主题文件 (*.json)"
        )
        if file_path:
            try:
                self.update_theme_from_ui()
                self.current_theme.save_to_file(Path(file_path))
                QMessageBox.information(self, "成功", "主题导出成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出主题失败：{e}")
    
    def apply_theme(self):
        """应用主题"""
        try:
            self.update_theme_from_ui()
            if self.theme_engine.apply_theme(self.current_theme):
                self.theme_applied.emit(self.current_theme)
                QMessageBox.information(self, "成功", "主题应用成功！")
            else:
                QMessageBox.warning(self, "警告", "主题应用失败，请查看错误信息。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用主题失败：{e}")
    
    def accept_and_apply(self):
        """确定并应用"""
        self.apply_theme()
        self.accept()
