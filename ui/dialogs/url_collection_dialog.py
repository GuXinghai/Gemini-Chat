"""
URL采集对话框
支持多个URL输入，自动识别类型，提供预览功能
"""
import re
from typing import List, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QProgressBar,
    QGroupBox, QScrollArea, QFrame, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QIcon

from services.file_upload_service import URLInfo, parse_urls_from_text


class URLAnalysisWorker(QThread):
    """URL分析工作线程"""
    
    analysis_finished = Signal(list)  # List[URLInfo]
    analysis_error = Signal(str)
    
    def __init__(self, file_upload_service, urls: List[str]):
        super().__init__()
        self.file_upload_service = file_upload_service
        self.urls = urls
    
    def run(self):
        try:
            url_infos = self.file_upload_service.analyze_urls(self.urls)
            self.analysis_finished.emit(url_infos)
        except Exception as e:
            self.analysis_error.emit(str(e))


class URLCollectionDialog(QDialog):
    """URL采集对话框"""
    
    urls_selected = Signal(list)  # List[str] - 选中的URL列表
    
    def __init__(self, file_upload_service, parent=None):
        super().__init__(parent)
        self.file_upload_service = file_upload_service
        self.url_infos: List[URLInfo] = []
        self.selected_urls: List[str] = []
        
        self.setWindowTitle("URL 采集")
        self.setMinimumSize(600, 500)
        self.resize(800, 600)
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题和说明
        title_label = QLabel("🔗 URL 采集器")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        desc_label = QLabel(
            "粘贴多个URL，支持PDF、图片、视频、音频、YouTube链接等\n"
            "支持换行、空格、逗号分隔；系统会自动识别类型并预估大小"
        )
        desc_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：URL输入区域
        input_group = self.create_input_group()
        splitter.addWidget(input_group)
        
        # 右侧：URL预览区域
        preview_group = self.create_preview_group()
        splitter.addWidget(preview_group)
        
        # 设置分割比例
        splitter.setSizes([300, 400])
        
        # 底部按钮
        button_layout = self.create_button_layout()
        layout.addLayout(button_layout)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def create_input_group(self) -> QGroupBox:
        """创建URL输入组"""
        group = QGroupBox("📝 URL 输入")
        layout = QVBoxLayout(group)
        
        # URL输入框
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText(
            "请粘贴URL，例如：\n\n"
            "https://example.com/document.pdf\n"
            "https://example.com/image.jpg\n"
            "https://www.youtube.com/watch?v=xxx\n"
            "https://example.com/page.html\n\n"
            "支持多种分隔符：换行、空格、逗号、中文逗号"
        )
        self.url_input.setMaximumHeight(200)
        
        # 快速操作按钮
        quick_actions = QHBoxLayout()
        
        self.analyze_btn = QPushButton("🔍 分析URL")
        self.analyze_btn.setToolTip("分析输入的URL，识别类型和大小")
        
        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setToolTip("清空输入框")
        
        self.paste_btn = QPushButton("📋 粘贴")
        self.paste_btn.setToolTip("从剪贴板粘贴")
        
        quick_actions.addWidget(self.analyze_btn)
        quick_actions.addWidget(self.clear_btn)
        quick_actions.addWidget(self.paste_btn)
        quick_actions.addStretch()
        
        layout.addWidget(self.url_input)
        layout.addLayout(quick_actions)
        
        # URL计数和统计
        self.stats_label = QLabel("输入URL: 0个")
        self.stats_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.stats_label)
        
        return group
    
    def create_preview_group(self) -> QGroupBox:
        """创建URL预览组"""
        group = QGroupBox("👀 URL 预览")
        layout = QVBoxLayout(group)
        
        # URL列表
        self.url_list = QListWidget()
        self.url_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.url_list)
        
        # 预览操作
        preview_actions = QHBoxLayout()
        
        self.select_all_btn = QPushButton("✅ 全选")
        self.select_none_btn = QPushButton("❌ 全不选")
        self.remove_selected_btn = QPushButton("🗑️ 删除选中")
        
        preview_actions.addWidget(self.select_all_btn)
        preview_actions.addWidget(self.select_none_btn)
        preview_actions.addWidget(self.remove_selected_btn)
        preview_actions.addStretch()
        
        layout.addLayout(preview_actions)
        
        # 预览统计
        self.preview_stats_label = QLabel("已识别: 0个URL，预估大小: 0MB")
        self.preview_stats_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.preview_stats_label)
        
        return group
    
    def create_button_layout(self) -> QHBoxLayout:
        """创建底部按钮布局"""
        layout = QHBoxLayout()
        
        # 帮助按钮
        self.help_btn = QPushButton("❓ 帮助")
        self.help_btn.setToolTip("查看支持的URL类型和使用说明")
        
        layout.addWidget(self.help_btn)
        layout.addStretch()
        
        # 主要操作按钮
        self.cancel_btn = QPushButton("取消")
        self.ok_btn = QPushButton("确定使用选中的URL")
        self.ok_btn.setEnabled(False)
        
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept_selected_urls)
        
        layout.addWidget(self.cancel_btn)
        layout.addWidget(self.ok_btn)
        
        return layout
    
    def connect_signals(self):
        """连接信号"""
        # URL输入相关
        self.url_input.textChanged.connect(self.on_input_changed)
        self.analyze_btn.clicked.connect(self.analyze_urls)
        self.clear_btn.clicked.connect(self.clear_input)
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        
        # 预览相关
        self.url_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.select_all_btn.clicked.connect(self.select_all_urls)
        self.select_none_btn.clicked.connect(self.select_no_urls)
        self.remove_selected_btn.clicked.connect(self.remove_selected_urls)
        
        # 帮助
        self.help_btn.clicked.connect(self.show_help)
        
        # 自动分析定时器
        self.auto_analyze_timer = QTimer()
        self.auto_analyze_timer.setSingleShot(True)
        self.auto_analyze_timer.timeout.connect(self.analyze_urls)
    
    def on_input_changed(self):
        """输入内容变化时"""
        text = self.url_input.toPlainText().strip()
        urls = parse_urls_from_text(text) if text else []
        
        self.stats_label.setText(f"输入URL: {len(urls)}个")
        
        # 重置自动分析定时器
        self.auto_analyze_timer.stop()
        if urls:
            self.auto_analyze_timer.start(2000)  # 2秒后自动分析
    
    def analyze_urls(self):
        """分析URL"""
        text = self.url_input.toPlainText().strip()
        if not text:
            self.url_list.clear()
            self.url_infos.clear()
            self.update_preview_stats()
            return
        
        urls = parse_urls_from_text(text)
        if not urls:
            QMessageBox.information(self, "提示", "未识别到有效的URL")
            return
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.analyze_btn.setEnabled(False)
        
        # 启动分析线程
        self.analysis_worker = URLAnalysisWorker(self.file_upload_service, urls)
        self.analysis_worker.analysis_finished.connect(self.on_analysis_finished)
        self.analysis_worker.analysis_error.connect(self.on_analysis_error)
        self.analysis_worker.start()
    
    def on_analysis_finished(self, url_infos: List[URLInfo]):
        """分析完成"""
        self.url_infos = url_infos
        self.update_url_list()
        self.update_preview_stats()
        
        # 隐藏进度
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        
        # 默认全选
        self.select_all_urls()
    
    def on_analysis_error(self, error: str):
        """分析出错"""
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        QMessageBox.warning(self, "分析失败", f"URL分析失败：{error}")
    
    def update_url_list(self):
        """更新URL列表"""
        self.url_list.clear()
        
        for url_info in self.url_infos:
            item_text = self.format_url_item(url_info)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, url_info.url)
            
            # 设置图标和样式
            icon = self.get_type_icon(url_info.url_type)
            item.setIcon(icon)
            
            self.url_list.addItem(item)
    
    def format_url_item(self, url_info: URLInfo) -> str:
        """格式化URL列表项文本"""
        type_name = {
            'pdf': 'PDF文档',
            'image': '图片',
            'video': '视频',
            'audio': '音频',
            'youtube': 'YouTube',
            'html': '网页'
        }.get(url_info.url_type, '未知')
        
        # 基本信息
        text = f"[{type_name}] {url_info.title or url_info.url}"
        
        # 添加大小信息
        if url_info.estimated_size:
            size_mb = url_info.estimated_size / 1024 / 1024
            text += f" ({size_mb:.1f}MB)"
        
        # 添加MIME类型
        if url_info.mime_type:
            text += f"\n类型: {url_info.mime_type}"
        
        text += f"\n地址: {url_info.url}"
        
        return text
    
    def get_type_icon(self, url_type: str) -> QIcon:
        """获取类型图标"""
        # 这里可以添加实际的图标，现在返回空图标
        return QIcon()
    
    def update_preview_stats(self):
        """更新预览统计"""
        total_count = len(self.url_infos)
        total_size = sum(info.estimated_size or 0 for info in self.url_infos)
        size_mb = total_size / 1024 / 1024 if total_size > 0 else 0
        
        self.preview_stats_label.setText(
            f"已识别: {total_count}个URL，预估大小: {size_mb:.1f}MB"
        )
    
    def clear_input(self):
        """清空输入"""
        self.url_input.clear()
        self.url_list.clear()
        self.url_infos.clear()
        self.update_preview_stats()
    
    def paste_from_clipboard(self):
        """从剪贴板粘贴"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            current_text = self.url_input.toPlainText()
            if current_text:
                self.url_input.append(text)
            else:
                self.url_input.setPlainText(text)
    
    def on_selection_changed(self):
        """选择变化时"""
        selected_items = self.url_list.selectedItems()
        self.selected_urls = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        
        # 更新按钮状态
        has_selection = len(self.selected_urls) > 0
        self.ok_btn.setEnabled(has_selection)
        self.remove_selected_btn.setEnabled(has_selection)
        
        # 更新确定按钮文本
        if has_selection:
            self.ok_btn.setText(f"确定使用选中的 {len(self.selected_urls)} 个URL")
        else:
            self.ok_btn.setText("确定使用选中的URL")
    
    def select_all_urls(self):
        """全选URL"""
        for i in range(self.url_list.count()):
            item = self.url_list.item(i)
            item.setSelected(True)
    
    def select_no_urls(self):
        """全不选URL"""
        self.url_list.clearSelection()
    
    def remove_selected_urls(self):
        """删除选中的URL"""
        selected_items = self.url_list.selectedItems()
        if not selected_items:
            return
        
        # 从后往前删除，避免索引问题
        for item in reversed(selected_items):
            row = self.url_list.row(item)
            self.url_list.takeItem(row)
            if 0 <= row < len(self.url_infos):
                self.url_infos.pop(row)
        
        self.update_preview_stats()
    
    def accept_selected_urls(self):
        """接受选中的URL"""
        if not self.selected_urls:
            QMessageBox.information(self, "提示", "请选择要使用的URL")
            return
        
        self.urls_selected.emit(self.selected_urls)
        self.accept()
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
🔗 URL 采集器使用说明

支持的URL类型：
• PDF文档：直接链接到PDF文件
• 图片：JPG、PNG、GIF、WebP等格式
• 视频：MP4、AVI、MOV等格式  
• 音频：MP3、WAV、AAC等格式
• YouTube：YouTube视频链接
• 网页：HTML页面（将提取文本内容）

输入格式：
• 每行一个URL，或用空格、逗号分隔
• 支持http://和https://协议
• 如果没有协议前缀，会自动添加https://

使用步骤：
1. 粘贴或输入URL
2. 点击"分析URL"或等待自动分析
3. 在预览区选择要使用的URL  
4. 点击"确定"完成选择

注意事项：
• 系统会尝试获取文件大小和类型
• 大文件可能需要更长的分析时间
• YouTube视频会直接传递给Gemini处理
• 网页内容会被下载并提取文本
        """
        
        QMessageBox.information(self, "帮助", help_text.strip())
