"""
历史记录管理组件 - PySide6版本
改进版本：采用行业标准的加载状态管理模式
"""
from typing import Dict, List, Optional, Callable, Any, Union
from pathlib import Path
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMenu, QDialog, QLineEdit, QDialogButtonBox,
    QLabel, QMessageBox, QApplication, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QAction, QCursor

from services.folder_service import FolderService
from services.history_service import HistoryService

# 延迟导入加载状态管理器，避免循环导入
LOADING_MANAGER_AVAILABLE = False
try:
    # 不在模块级别导入，而是在需要时动态导入
    import importlib
    loading_module = importlib.import_module('ui.loading_state_manager')
    LOADING_MANAGER_AVAILABLE = True
except ImportError:
    print("加载状态管理器不可用，使用简单的加载提示")


class ChatHistoryManager(QWidget):
    """聊天记录管理组件 - PySide6版本"""
    
    # 信号定义
    chat_selected = Signal(str)  # 聊天记录被选中
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        history_service: Optional[HistoryService] = None,
        on_chat_selected: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent)
        
        self.history_service = history_service
        self.folder_service = FolderService()
        self.on_chat_selected = on_chat_selected
        
        # 防重复点击的时间戳
        self._last_click_time = 0
        self._click_delay = 300  # 300ms防抖动
        
        # 防频繁刷新的时间戳
        self._last_refresh_time = 0
        self._refresh_delay = 100  # 100ms防抖动
        
        # 连接信号（只在没有回调函数时连接信号）
        if on_chat_selected and not callable(on_chat_selected):
            # 如果传入的不是函数而是其他对象，尝试连接信号
            self.chat_selected.connect(on_chat_selected)
        # 如果传入的是回调函数，则不连接信号，避免重复调用
        
        # 加载图标
        self.icons = self._load_icons()
        
        # 创建界面
        self._create_widgets()
        
        # 加载历史记录
        self.refresh_history()
    
    def _load_icons(self) -> Dict[str, QIcon]:
        """加载图标"""
        icons = {}
        icon_path = Path(__file__).parent / "resources" / "icons"
        
        icon_files = {
            "delete": "delete.png",
            "rename": "rename.png", 
            "folder": "folder.png",
            "star": "star.png",
            "starred": "starred.png"
        }
        
        for name, filename in icon_files.items():
            file_path = icon_path / filename
            if file_path.exists():
                icons[name] = QIcon(str(file_path))
            else:
                # 创建空图标作为备用
                icons[name] = QIcon()
                
        return icons
    
    def _create_widgets(self):
        """创建界面组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建树形视图
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["聊天记录", "操作"])
        
        # 设置列宽 - 确保操作列有足够空间显示按钮
        self.tree.setColumnWidth(0, 160)
        self.tree.setColumnWidth(1, 120)
        
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # 显示表头以便看到操作列
        self.tree.setHeaderHidden(False)
        
        # 连接信号
        self.tree.itemClicked.connect(self._on_chat_selected)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.tree)
    
    def refresh_history(self):
        """刷新历史记录"""
        import time
        
        # 防频繁刷新检查
        current_time = int(time.time() * 1000)  # 毫秒时间戳
        if current_time - self._last_refresh_time < self._refresh_delay:
            return  # 忽略过于频繁的刷新
        
        self._last_refresh_time = current_time
        
        # 清空树形视图
        self.tree.clear()
        self._load_history()
    
    def _remove_chat_item(self, chat_id: str):
        """从树中移除指定的聊天记录项"""
        for i in range(self.tree.topLevelItemCount()):
            folder_item = self.tree.topLevelItem(i)
            if folder_item:
                # 检查文件夹下的聊天记录
                for j in range(folder_item.childCount()):
                    chat_item = folder_item.child(j)
                    if chat_item and chat_item.data(0, Qt.ItemDataRole.UserRole) == chat_id:
                        folder_item.removeChild(chat_item)
                        # 如果文件夹为空且不是特殊文件夹，移除文件夹
                        if folder_item.childCount() == 0:
                            folder_type = folder_item.data(0, Qt.ItemDataRole.UserRole + 1)
                            if folder_type not in ["starred", "all"]:
                                self.tree.takeTopLevelItem(i)
                        return
    
    def _update_chat_item(self, chat_id: str, new_title: Optional[str] = None):
        """更新指定聊天记录项的显示"""
        for i in range(self.tree.topLevelItemCount()):
            folder_item = self.tree.topLevelItem(i)
            if folder_item:
                for j in range(folder_item.childCount()):
                    chat_item = folder_item.child(j)
                    if chat_item and chat_item.data(0, Qt.ItemDataRole.UserRole) == chat_id:
                        if new_title:
                            chat_item.setText(0, new_title)
                        # 更新星标图标
                        actions_widget = self.tree.itemWidget(chat_item, 1)
                        if actions_widget:
                            layout = actions_widget.layout()
                            if layout and layout.count() >= 4:  # 星标按钮是第4个
                                layout_item = layout.itemAt(3)
                                if layout_item:
                                    star_btn = layout_item.widget()
                                    if star_btn and isinstance(star_btn, QPushButton):
                                        current_folders = self.folder_service.get_chat_folders(chat_id)
                                        is_starred = "starred" in current_folders
                                        star_btn.setIcon(self.icons.get("starred" if is_starred else "star", QIcon()))
                        return
    
    def _load_history(self):
        folders = self.folder_service.list_folders()
        
        # 获取所有会话
        conversations = self.history_service.list_conversations() if self.history_service else []
        
        # 添加文件夹和会话
        folder_items = {}
        for folder in folders:
            folder_id = folder["id"]
            folder_name = folder["name"]
            
            # 创建文件夹节点
            folder_item = QTreeWidgetItem(self.tree)
            folder_item.setText(0, folder_name)
            folder_item.setData(0, Qt.ItemDataRole.UserRole, folder_id)
            folder_item.setData(0, Qt.ItemDataRole.UserRole + 1, "folder")
            folder_item.setExpanded(True)
            
            # 如果有文件夹图标，设置图标
            if "folder" in self.icons:
                folder_item.setIcon(0, self.icons["folder"])
            
            folder_items[folder_id] = folder_item
            
            # 添加该文件夹下的会话
            for conv in conversations:
                if conv.id in folder["chats"]:
                    self._add_chat_item(folder_item, conv)
        
        # 添加未分类的会话
        uncategorized_item = QTreeWidgetItem(self.tree)
        uncategorized_item.setText(0, "未分类")
        uncategorized_item.setData(0, Qt.ItemDataRole.UserRole, "uncategorized")
        uncategorized_item.setData(0, Qt.ItemDataRole.UserRole + 1, "folder")
        uncategorized_item.setExpanded(True)
        
        # 收集所有已分类的聊天记录
        all_folder_chats = set()
        for folder in folders:
            all_folder_chats.update(folder["chats"])
        
        # 添加未分类的会话
        for conv in conversations:
            if conv.id not in all_folder_chats:
                self._add_chat_item(uncategorized_item, conv)
        
        # 调整列宽
        self.tree.resizeColumnToContents(0)
    
    def _add_chat_item(self, parent_item: QTreeWidgetItem, conversation: Any):
        """添加聊天记录项"""
        chat_item = QTreeWidgetItem(parent_item)
        chat_item.setText(0, conversation.title or "未命名对话")
        chat_item.setData(0, Qt.ItemDataRole.UserRole, conversation.id)
        chat_item.setData(0, Qt.ItemDataRole.UserRole + 1, "chat")
        
        # 创建操作按钮容器
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(2, 2, 2, 2)
        actions_layout.setSpacing(2)
        
        # 删除按钮
        delete_btn = QPushButton()
        delete_btn.setIcon(self.icons.get("delete", QIcon()))
        delete_btn.setToolTip("删除")
        delete_btn.setMaximumSize(QSize(24, 24))
        delete_btn.clicked.connect(partial(self._delete_chat, conversation.id))
        actions_layout.addWidget(delete_btn)
        
        # 重命名按钮
        rename_btn = QPushButton()
        rename_btn.setIcon(self.icons.get("rename", QIcon()))
        rename_btn.setToolTip("重命名")
        rename_btn.setMaximumSize(QSize(24, 24))
        rename_btn.clicked.connect(partial(self._rename_chat, conversation.id))
        actions_layout.addWidget(rename_btn)
        
        # 添加到文件夹按钮
        folder_btn = QPushButton()
        folder_btn.setIcon(self.icons.get("folder", QIcon()))
        folder_btn.setToolTip("管理文件夹")
        folder_btn.setMaximumSize(QSize(24, 24))
        folder_btn.clicked.connect(partial(self._show_folder_menu, conversation.id, folder_btn))
        actions_layout.addWidget(folder_btn)
        
        # 星标按钮
        current_folders = self.folder_service.get_chat_folders(conversation.id)
        is_starred = "starred" in current_folders
        star_btn = QPushButton()
        star_btn.setIcon(self.icons.get("starred" if is_starred else "star", QIcon()))
        star_btn.setToolTip("星标")
        star_btn.setMaximumSize(QSize(24, 24))
        star_btn.clicked.connect(partial(self._toggle_star, conversation.id))
        actions_layout.addWidget(star_btn)
        
        # 添加弹簧推到右边
        actions_layout.addStretch()
        
        # 将操作组件设置到树形视图中
        self.tree.setItemWidget(chat_item, 1, actions_widget)
    
    def _on_chat_selected(self, item: QTreeWidgetItem, column: int):
        """处理聊天记录单击事件 - 使用行业标准的异步加载模式"""
        import time
        
        # 1. 防抖动检查 - 行业标准做法
        current_time = int(time.time() * 1000)
        if current_time - self._last_click_time < self._click_delay:
            return
        
        self._last_click_time = current_time
        
        if not item:
            return
            
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        if item_type == "chat" and item_id:
            # 2. 立即显示加载状态 - 提升用户体验
            self._show_loading_state(item)
            
            # 3. 异步加载和处理 - 避免阻塞UI线程
            self._load_chat_async(item_id, item)
    
    def _show_loading_state(self, item: QTreeWidgetItem):
        """显示加载状态 - 使用行业标准的加载管理器"""
        original_text = item.text(0)
        item.setData(0, Qt.ItemDataRole.UserRole + 2, original_text)  # 保存原始文本
        
        if LOADING_MANAGER_AVAILABLE:
            # 使用加载状态管理器
            chat_id = item.data(0, Qt.ItemDataRole.UserRole)
            from .loading_state_manager import start_loading
            start_loading(f"chat_load_{chat_id}", f"正在加载 {original_text}...", parent_widget=self)
        
        # 同时更新UI项目显示
        item.setText(0, f"⏳ {original_text}")
        item.setDisabled(True)  # 防止重复点击
    
    def _hide_loading_state(self, item: QTreeWidgetItem):
        """隐藏加载状态"""
        original_text = item.data(0, Qt.ItemDataRole.UserRole + 2)
        if original_text:
            item.setText(0, original_text)
        item.setDisabled(False)
        
        if LOADING_MANAGER_AVAILABLE:
            # 完成加载状态
            chat_id = item.data(0, Qt.ItemDataRole.UserRole)
            from .loading_state_manager import finish_loading
            finish_loading(f"chat_load_{chat_id}")
    
    def _load_chat_async(self, chat_id: str, item: QTreeWidgetItem):
        """异步加载聊天 - 行业标准的异步处理模式"""
        from PySide6.QtCore import QTimer
        
        def load_and_callback():
            try:
                # 4. 错误处理和回退机制
                success = False
                
                # 优先使用回调函数
                if self.on_chat_selected and callable(self.on_chat_selected):
                    success = self.on_chat_selected(chat_id)
                    if success is None:  # 回调函数没有返回值，视为成功
                        success = True
                elif hasattr(self, 'chat_selected'):
                    self.chat_selected.emit(chat_id)
                    success = True
                
                # 5. 隐藏加载状态
                self._hide_loading_state(item)
                
                # 6. 如果加载失败，显示错误提示
                if not success:
                    self._show_load_error(item, "加载失败")
                    
            except Exception as e:
                print(f"加载聊天记录异常: {e}")
                self._hide_loading_state(item)
                self._show_load_error(item, f"加载错误: {str(e)}")
        
        # 使用QTimer实现异步执行，避免阻塞UI
        QTimer.singleShot(50, load_and_callback)
    
    def _show_load_error(self, item: QTreeWidgetItem, error_msg: str):
        """显示加载错误"""
        from PySide6.QtWidgets import QMessageBox
        
        # 恢复原始状态
        original_text = item.data(0, Qt.ItemDataRole.UserRole + 2)
        if original_text:
            item.setText(0, original_text)
        item.setDisabled(False)
        
        if LOADING_MANAGER_AVAILABLE:
            # 使用加载状态管理器显示错误
            chat_id = item.data(0, Qt.ItemDataRole.UserRole)
            from .loading_state_manager import error_loading
            error_loading(f"chat_load_{chat_id}", error_msg)
        else:
            # 回退到简单的错误提示
            QMessageBox.warning(
                self,
                "加载失败",
                f"无法加载聊天记录:\n{error_msg}",
                QMessageBox.StandardButton.Ok
            )
    
    def _delete_chat(self, chat_id: str):
        """删除聊天记录"""
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            "确定要删除这条聊天记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 从所有文件夹中移除
            folders = self.folder_service.list_folders()
            for folder in folders:
                self.folder_service.remove_chat_from_folder(folder["id"], chat_id)
            
            # 删除聊天记录文件
            if self.history_service and self.history_service.delete_conversation(chat_id):
                # 使用增量更新，而不是全量刷新
                self._remove_chat_item(chat_id)
    
    def _rename_chat(self, chat_id: str):
        """重命名聊天记录"""
        dialog = RenameDialog(self, "重命名聊天记录")
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.get_name():
            new_name = dialog.get_name()
            if self.history_service and self.history_service.rename_conversation(chat_id, new_name):
                # 使用增量更新，而不是全量刷新
                self._update_chat_item(chat_id, new_name)
    
    def _show_folder_menu(self, chat_id: str, button: QPushButton):
        """显示文件夹菜单"""
        menu = QMenu(self)
        
        # 获取所有文件夹和当前聊天记录所在的文件夹
        folders = self.folder_service.list_folders()
        current_folders = self.folder_service.get_chat_folders(chat_id)
        
        for folder in folders:
            folder_id = folder["id"]
            folder_name = folder["name"]
            is_in_folder = folder_id in current_folders
            
            action = QAction(folder_name, self)
            action.setCheckable(True)
            action.setChecked(is_in_folder)
            action.triggered.connect(lambda checked, fid=folder_id: self._toggle_folder(chat_id, fid))
            menu.addAction(action)
        
        # 如果没有文件夹，添加提示
        if not folders:
            action = QAction("暂无文件夹", self)
            action.setEnabled(False)
            menu.addAction(action)
        
        # 显示菜单
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
    
    def _toggle_folder(self, chat_id: str, folder_id: str):
        """切换文件夹状态"""
        current_folders = self.folder_service.get_chat_folders(chat_id)
        
        if folder_id in current_folders:
            self.folder_service.remove_chat_from_folder(folder_id, chat_id)
        else:
            self.folder_service.add_chat_to_folder(folder_id, chat_id)
        
        # 使用增量更新，而不是全量刷新
        self._update_chat_item(chat_id)
    
    def _toggle_star(self, chat_id: str):
        """切换星标状态"""
        current_folders = self.folder_service.get_chat_folders(chat_id)
        is_starred = "starred" in current_folders
        
        if is_starred:
            self.folder_service.remove_chat_from_folder("starred", chat_id)
        else:
            self.folder_service.add_chat_to_folder("starred", chat_id)
        
        # 使用增量更新，而不是全量刷新
        self._update_chat_item(chat_id)
    
    def _show_context_menu(self, position):
        """显示右键菜单"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        
        if item_type == "folder" and item_id == "uncategorized":
            action = QAction("新建文件夹", self)
            action.triggered.connect(self._create_folder)
            menu.addAction(action)
        elif item_type == "folder" and item_id != "uncategorized":
            # 文件夹右键菜单
            rename_action = QAction("重命名文件夹", self)
            rename_action.triggered.connect(partial(self._rename_folder, item_id))
            menu.addAction(rename_action)
            
            delete_action = QAction("删除文件夹", self)
            delete_action.triggered.connect(partial(self._delete_folder, item_id))
            menu.addAction(delete_action)
        elif item_type == "chat":
            # 聊天记录右键菜单
            rename_action = QAction("重命名", self)
            rename_action.triggered.connect(partial(self._rename_chat, item_id))
            menu.addAction(rename_action)
            
            delete_action = QAction("删除", self)
            delete_action.triggered.connect(partial(self._delete_chat, item_id))
            menu.addAction(delete_action)
        
        if menu.actions():
            menu.exec(self.tree.mapToGlobal(position))
    
    def _create_folder(self):
        """创建新文件夹"""
        dialog = RenameDialog(self, "新建文件夹")
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.get_name():
            folder_name = dialog.get_name()
            self.folder_service.create_folder(folder_name)
            # 创建文件夹需要全量刷新，因为要添加新的顶级项
            self.refresh_history()
    
    def _rename_folder(self, folder_id: str):
        """重命名文件夹"""
        dialog = RenameDialog(self, "重命名文件夹")
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.get_name():
            new_name = dialog.get_name()
            if self.folder_service.rename_folder(folder_id, new_name):
                # 文件夹重命名需要全量刷新，因为要更新顶级项文本
                self.refresh_history()
    
    def _delete_folder(self, folder_id: str):
        """删除文件夹"""
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            "确定要删除这个文件夹吗？（聊天记录不会被删除）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.folder_service.delete_folder(folder_id):
                # 删除文件夹需要全量刷新，因为要移除顶级项
                self.refresh_history()


class RenameDialog(QDialog):
    """重命名对话框 - PySide6版本"""
    
    def __init__(self, parent: Optional[QWidget] = None, title: str = "重命名"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(300)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        
        # 标签
        label = QLabel("名称:")
        layout.addWidget(label)
        
        # 输入框
        self.name_edit = QLineEdit()
        self.name_edit.returnPressed.connect(self.accept)
        layout.addWidget(self.name_edit)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 设置焦点
        self.name_edit.setFocus()
    
    def get_name(self) -> str:
        """获取输入的名称"""
        return self.name_edit.text().strip()
    
    def set_name(self, name: str):
        """设置初始名称"""
        self.name_edit.setText(name)
        self.name_edit.selectAll()