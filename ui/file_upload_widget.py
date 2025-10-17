"""
增强的多模态文件上传和拖拽组件
支持文档/图片/视频/音频上传，URL采集，即时预览，历史追溯
遵循设计规范：拖拽/上传/URL采集→即时预览→一键调用→可追溯历史
"""
import os
import sys
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QProgressBar, QMessageBox,
    QFrame, QFileDialog, QToolButton, QMenu, QTextEdit,
    QSplitter, QGroupBox, QScrollArea, QTabWidget
)
from PySide6.QtCore import Qt, Signal, QThread, QMimeData, QUrl, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QPainter, QPen, QBrush, QColor, QFont

# 添加项目根目录到路径
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir))

from services.file_upload_service import get_file_upload_service, ProcessedFile, parse_urls_from_text
from ui.dialogs.url_collection_dialog import URLCollectionDialog


class FileProcessingWorker(QThread):
    """文件处理工作线程"""
    
    processing_progress = Signal(str, int)  # filename, progress
    processing_finished = Signal(list)  # List[ProcessedFile]
    processing_error = Signal(str)
    
    def __init__(self, file_upload_service, file_paths: Optional[List[str]] = None, urls: Optional[List[str]] = None):
        super().__init__()
        self.file_upload_service = file_upload_service
        self.file_paths = file_paths or []
        self.urls = urls or []
    
    def run(self):
        """执行文件处理"""
        try:
            # 异步处理文件和URL
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                processed_files = loop.run_until_complete(self._process_all())
                self.processing_finished.emit(processed_files)
            finally:
                loop.close()
                
        except Exception as e:
            print(f"FileProcessingWorker异常: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            self.processing_error.emit(str(e))
    
    async def _process_all(self):
        """处理所有文件和URL"""
        processed_files = []
        
        # 处理文件
        if self.file_paths:
            for i, file_path in enumerate(self.file_paths):
                self.processing_progress.emit(file_path, int(50 * i / len(self.file_paths)))
            
            file_results = await self.file_upload_service.process_files(self.file_paths)
            processed_files.extend(file_results)
        
        # 处理URL
        if self.urls:
            url_results = await self.file_upload_service.process_urls(self.urls)
            processed_files.extend(url_results)
        
        return processed_files


class FilePreviewItem(QListWidgetItem):
    """文件预览列表项"""
    
    def __init__(self, processed_file: ProcessedFile):
        super().__init__()
        self.processed_file = processed_file
        self.update_display()
    
    def update_display(self):
        """更新显示内容"""
        file = self.processed_file
        
        # 格式化显示文本
        type_icon = {
            'IMAGE': '🖼️',
            'DOCUMENT': '📄',
            'VIDEO': '🎥',
            'AUDIO': '🎵',
            'OTHER': '📎'
        }.get(file.attachment_type.value, '📎')
        
        # 文件大小
        size_text = self._format_file_size(file.file_size)
        
        # 主要信息
        text = f"{type_icon} {file.original_name}"
        
        # 详细信息
        details = []
        details.append(f"大小: {size_text}")
        details.append(f"类型: {file.mime_type}")
        
        if file.metadata and file.metadata.get('source_url'):
            details.append(f"来源: URL")
        
        if file.gemini_file:
            details.append("✅ 已上传到File API")
        
        text += "\n" + " | ".join(details)
        
        self.setText(text)
        self.setToolTip(f"路径: {file.file_path}")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"


class EnhancedFileUploadWidget(QWidget):
    """增强的多模态文件上传组件"""
    
    # 信号定义
    files_processed = Signal(list)  # List[ProcessedFile] - 文件处理完成
    processing_status_changed = Signal(str)  # 处理状态变化
    
    def __init__(self, api_key: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.file_upload_service = get_file_upload_service(api_key)
        
        # 状态管理
        self.processed_files: List[ProcessedFile] = []
        self.is_processing = False
        
        # UI组件
        self.setup_ui()
        self.setup_drag_drop()
        self.connect_signals()
        
        print("增强文件上传组件初始化完成")
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 头部工具栏
        header_layout = self.create_header_toolbar()
        layout.addLayout(header_layout)
        
        # 主内容区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：拖拽区域和快速操作
        left_panel = self.create_left_panel()
        content_splitter.addWidget(left_panel)
        
        # 右侧：文件预览列表
        right_panel = self.create_right_panel()
        content_splitter.addWidget(right_panel)
        
        content_splitter.setSizes([300, 400])
        layout.addWidget(content_splitter)
        
        # 底部状态栏
        status_layout = self.create_status_bar()
        layout.addLayout(status_layout)
    
    def create_header_toolbar(self) -> QHBoxLayout:
        """创建头部工具栏"""
        layout = QHBoxLayout()
        
        # 标题
        title_label = QLabel("📎 多模态文件上传")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        layout.addWidget(title_label)
        layout.addStretch()
        
        # 主要操作按钮
        self.file_btn = QPushButton("📁 选择文件")
        self.file_btn.setToolTip("从文件管理器选择文件")
        
        self.url_btn = QPushButton("🔗 URL采集")
        self.url_btn.setToolTip("输入URL来采集网络内容")
        
        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setToolTip("清空所有已选择的文件")
        
        layout.addWidget(self.file_btn)
        layout.addWidget(self.url_btn)
        layout.addWidget(self.clear_btn)
        
        return layout
    
    def create_left_panel(self) -> QGroupBox:
        """创建左侧面板"""
        group = QGroupBox("📥 拖拽上传区")
        layout = QVBoxLayout(group)
        
        # 拖拽区域
        self.drop_area = self.create_drop_area()
        layout.addWidget(self.drop_area)
        
        # 快速统计
        self.quick_stats = QLabel("支持：文档📄 图片🖼️ 视频🎥 音频🎵")
        self.quick_stats.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
        self.quick_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.quick_stats)
        
        # 支持格式说明
        formats_text = QLabel(
            "支持格式：\n"
            "• 文档：PDF, TXT, MD, HTML\n"
            "• 图片：JPG, PNG, WebP, HEIC\n" 
            "• 视频：MP4, AVI, MOV, WebM\n"
            "• 音频：MP3, WAV, AAC, FLAC"
        )
        formats_text.setStyleSheet("color: #888; font-size: 11px; padding: 5px;")
        layout.addWidget(formats_text)
        
        return group
    
    def create_drop_area(self) -> QFrame:
        """创建拖拽区域"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame.setMinimumHeight(200)
        frame.setStyleSheet("""
            QFrame {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f9f9f9;
            }
            QFrame:hover {
                border-color: #007ACC;
                background-color: #f0f8ff;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        # 拖拽提示
        drop_icon = QLabel("📁")
        drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_icon.setStyleSheet("font-size: 48px; color: #ccc; margin: 20px;")
        
        drop_text = QLabel(
            "拖拽文件到这里\n或点击上方按钮选择文件\n\n"
            "支持多文件选择\n支持文件夹拖拽（递归扫描）"
        )
        drop_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_text.setStyleSheet("color: #666; font-size: 14px; line-height: 1.5;")
        
        layout.addStretch()
        layout.addWidget(drop_icon)
        layout.addWidget(drop_text)
        layout.addStretch()
        
        return frame
    
    def create_right_panel(self) -> QGroupBox:
        """创建右侧面板"""
        group = QGroupBox("👀 文件预览")
        layout = QVBoxLayout(group)
        
        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.file_list.setMinimumHeight(200)
        layout.addWidget(self.file_list)
        
        # 列表操作按钮
        list_actions = QHBoxLayout()
        
        self.select_all_btn = QPushButton("✅ 全选")
        self.select_none_btn = QPushButton("❌ 全不选")  
        self.remove_selected_btn = QPushButton("🗑️ 删除选中")
        
        list_actions.addWidget(self.select_all_btn)
        list_actions.addWidget(self.select_none_btn)
        list_actions.addWidget(self.remove_selected_btn)
        list_actions.addStretch()
        
        layout.addLayout(list_actions)
        
        # 文件统计
        self.file_stats = QLabel("文件: 0个, 大小: 0MB")
        self.file_stats.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.file_stats)
        
        return group
    
    def create_status_bar(self) -> QHBoxLayout:
        """创建状态栏"""
        layout = QHBoxLayout()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.progress_bar)
        
        return layout
    
    def setup_drag_drop(self):
        """设置拖拽功能"""
        self.setAcceptDrops(True)
        self.drop_area.setAcceptDrops(True)
    
    def connect_signals(self):
        """连接信号"""
        # 工具栏按钮
        self.file_btn.clicked.connect(self.select_files)
        self.url_btn.clicked.connect(self.collect_urls)
        self.clear_btn.clicked.connect(self.clear_all_files)
        
        # 列表操作
        self.select_all_btn.clicked.connect(self.select_all_files)
        self.select_none_btn.clicked.connect(self.select_no_files)
        self.remove_selected_btn.clicked.connect(self.remove_selected_files)
        
        # 文件列表
        self.file_list.itemSelectionChanged.connect(self.update_selection_ui)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_area.setStyleSheet("""
                QFrame {
                    border: 2px dashed #007ACC;
                    border-radius: 10px;
                    background-color: #e6f3ff;
                }
            """)
    
    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self.drop_area.setStyleSheet("""
            QFrame {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f9f9f9;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        self.drop_area.setStyleSheet("""
            QFrame {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f9f9f9;
            }
        """)
        
        urls = event.mimeData().urls()
        file_paths = []
        
        for url in urls:
            if url.isLocalFile():
                file_path = url.toLocalFile()
                path = Path(file_path)
                
                if path.is_file():
                    file_paths.append(str(path))
                elif path.is_dir():
                    # 递归扫描文件夹
                    folder_files = self.scan_folder(path)
                    file_paths.extend(folder_files)
        
        if file_paths:
            self.add_files(file_paths)
        
        event.acceptProposedAction()
    
    def scan_folder(self, folder_path: Path, max_depth: int = 3) -> List[str]:
        """扫描文件夹，递归获取文件"""
        files = []
        try:
            def _scan_recursive(path: Path, current_depth: int = 0):
                if current_depth >= max_depth:
                    return
                
                for item in path.iterdir():
                    if item.is_file():
                        # 检查是否为支持的格式
                        if self.is_supported_file(str(item)):
                            files.append(str(item))
                    elif item.is_dir() and not item.name.startswith('.'):
                        _scan_recursive(item, current_depth + 1)
            
            _scan_recursive(folder_path)
        except Exception as e:
            print(f"扫描文件夹失败: {e}")
        
        return files
    
    def is_supported_file(self, file_path: str) -> bool:
        """检查是否为支持的文件类型"""
        from services.file_upload_service import FileUploadService
        return Path(file_path).suffix.lower() in [
            '.pdf', '.txt', '.md', '.html', '.xml',  # 文档
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.heic', '.heif',  # 图片
            '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.3gpp',  # 视频
            '.mp3', '.wav', '.aac', '.ogg', '.flac', '.aiff'  # 音频
        ]
    
    def select_files(self):
        """选择文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择文件",
            "",
            "所有支持的文件 (*.pdf *.txt *.md *.html *.jpg *.jpeg *.png *.gif *.webp *.mp4 *.avi *.mov *.mp3 *.wav *.aac);;""所有文件 (*.*)"
        )
        
        if file_paths:
            self.add_files(file_paths)
    
    def collect_urls(self):
        """采集URL"""
        dialog = URLCollectionDialog(self.file_upload_service, self)
        
        if dialog.exec():
            urls = dialog.selected_urls
            if urls:
                self.add_urls(urls)
    
    def add_files(self, file_paths: List[str]):
        """添加文件"""
        if self.is_processing:
            QMessageBox.information(self, "提示", "正在处理文件，请稍等...")
            return
        
        # 验证文件
        valid, error_msg, valid_files = self.file_upload_service.validate_files(file_paths)
        
        if not valid:
            QMessageBox.warning(self, "文件验证失败", error_msg)
            return
        
        if not valid_files:
            QMessageBox.information(self, "提示", "没有找到支持的文件")
            return
        
        # 开始处理文件
        self.start_processing(file_paths=valid_files)
    
    def add_urls(self, urls: List[str]):
        """添加URL"""
        if self.is_processing:
            QMessageBox.information(self, "提示", "正在处理文件，请稍等...")
            return
        
        # 开始处理URL
        self.start_processing(urls=urls)
    
    def start_processing(self, file_paths: Optional[List[str]] = None, urls: Optional[List[str]] = None):
        """开始处理文件/URL"""
        self.is_processing = True
        self.update_processing_ui(True)
        
        # 启动处理线程
        self.processing_worker = FileProcessingWorker(
            self.file_upload_service, 
            file_paths=file_paths, 
            urls=urls
        )
        self.processing_worker.processing_progress.connect(self.on_processing_progress)
        self.processing_worker.processing_finished.connect(self.on_processing_finished)
        self.processing_worker.processing_error.connect(self.on_processing_error)
        self.processing_worker.start()
    
    def on_processing_progress(self, filename: str, progress: int):
        """处理进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"处理中: {Path(filename).name}")
    
    def on_processing_finished(self, processed_files: List[ProcessedFile]):
        """处理完成"""
        self.processed_files.extend(processed_files)
        self.update_file_list()
        self.update_file_stats()
        
        self.is_processing = False
        self.update_processing_ui(False)
        
        self.status_label.setText(f"处理完成，添加了 {len(processed_files)} 个文件")
        
        # 发出信号
        self.files_processed.emit(self.processed_files)
    
    def on_processing_error(self, error: str):
        """处理出错"""
        self.is_processing = False
        self.update_processing_ui(False)
        
        self.status_label.setText("处理失败")
        QMessageBox.warning(self, "处理失败", f"文件处理失败：{error}")
    
    def update_processing_ui(self, is_processing: bool):
        """更新处理中的UI状态"""
        # 禁用/启用按钮
        self.file_btn.setEnabled(not is_processing)
        self.url_btn.setEnabled(not is_processing)
        self.clear_btn.setEnabled(not is_processing)
        
        # 显示/隐藏进度条
        self.progress_bar.setVisible(is_processing)
        if is_processing:
            self.progress_bar.setRange(0, 0)  # 不确定进度
        
        # 更新状态
        if is_processing:
            self.processing_status_changed.emit("处理中...")
        else:
            self.processing_status_changed.emit("就绪")
    
    def update_file_list(self):
        """更新文件列表"""
        self.file_list.clear()
        
        for processed_file in self.processed_files:
            item = FilePreviewItem(processed_file)
            self.file_list.addItem(item)
    
    def update_file_stats(self):
        """更新文件统计"""
        total_count = len(self.processed_files)
        total_size = sum(f.file_size for f in self.processed_files)
        size_mb = total_size / 1024 / 1024 if total_size > 0 else 0
        
        self.file_stats.setText(f"文件: {total_count}个, 大小: {size_mb:.1f}MB")
        
        # 更新快速统计
        type_counts = {}
        for f in self.processed_files:
            type_name = f.attachment_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        type_icons = {
            'DOCUMENT': '📄',
            'IMAGE': '🖼️', 
            'VIDEO': '🎥',
            'AUDIO': '🎵',
            'OTHER': '📎'
        }
        
        stats_text = []
        for type_name, count in type_counts.items():
            icon = type_icons.get(type_name, '📎')
            stats_text.append(f"{icon}{count}")
        
        if stats_text:
            self.quick_stats.setText(" | ".join(stats_text))
        else:
            self.quick_stats.setText("支持：文档📄 图片🖼️ 视频🎥 音频🎵")
    
    def update_selection_ui(self):
        """更新选择相关UI"""
        selected_count = len(self.file_list.selectedItems())
        self.remove_selected_btn.setEnabled(selected_count > 0)
    
    def select_all_files(self):
        """全选文件"""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setSelected(True)
    
    def select_no_files(self):
        """全不选文件"""
        self.file_list.clearSelection()
    
    def remove_selected_files(self):
        """删除选中的文件"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除选中的 {len(selected_items)} 个文件吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 从后往前删除，避免索引问题
            for item in reversed(selected_items):
                row = self.file_list.row(item)
                self.file_list.takeItem(row)
                if 0 <= row < len(self.processed_files):
                    self.processed_files.pop(row)
            
            self.update_file_stats()
            self.files_processed.emit(self.processed_files)
    
    def clear_all_files(self):
        """清空所有文件"""
        if not self.processed_files:
            return
        
        reply = QMessageBox.question(
            self, "确认清空",
            f"确定要清空所有 {len(self.processed_files)} 个文件吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.processed_files.clear()
            self.file_list.clear()
            self.update_file_stats()
            self.status_label.setText("已清空")
            self.files_processed.emit(self.processed_files)
    
    def get_processed_files(self) -> List[ProcessedFile]:
        """获取已处理的文件列表"""
        return self.processed_files.copy()
    
    def get_gemini_parts(self) -> List[Any]:
        """获取用于Gemini API的内容部分"""
        return self.file_upload_service.create_gemini_parts(self.processed_files)
