"""
加载状态管理器 - 行业标准的加载状态管理
"""

from typing import Dict, Optional, Any, Callable, List
from PySide6.QtWidgets import QWidget, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QMovie


class LoadingStateManager(QObject):
    """
    加载状态管理器 - 行业通用的加载状态管理模式
    
    功能特点：
    1. 支持多种加载状态类型（文本、进度条、动画）
    2. 防抖动处理
    3. 状态队列管理
    4. 自动清理机制
    5. 错误状态处理
    """
    
    # 信号定义
    loading_started = Signal(str)  # 加载开始
    loading_finished = Signal(str)  # 加载完成
    loading_error = Signal(str, str)  # 加载错误(状态ID, 错误信息)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.parent_widget = parent
        
        # 状态管理
        self._loading_states: Dict[str, 'LoadingState'] = {}
        self._state_queue: List[str] = []
        
        # 防抖动设置
        self._debounce_delay = 100  # 100ms
        self._last_update_time = 0
        
        # 自动清理定时器
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._auto_cleanup)
        self._cleanup_timer.start(30000)  # 30秒清理一次
    
    def start_loading(
        self, 
        state_id: str, 
        message: str = "加载中...", 
        loading_type: str = "text",
        show_progress: bool = False,
        parent_widget: Optional[QWidget] = None
    ) -> Optional['LoadingState']:
        """
        开始加载状态
        
        Args:
            state_id: 状态唯一标识
            message: 加载消息
            loading_type: 加载类型 (text, progress, animation)
            show_progress: 是否显示进度条
            parent_widget: 父组件
            
        Returns:
            LoadingState对象或None
        """
        import time
        
        # 防抖动检查
        current_time = int(time.time() * 1000)
        if current_time - self._last_update_time < self._debounce_delay:
            return self._loading_states.get(state_id)
        
        self._last_update_time = current_time
        
        # 如果状态已存在，更新它
        if state_id in self._loading_states:
            existing_state = self._loading_states[state_id]
            existing_state.update_message(message)
            return existing_state
        
        # 创建新的加载状态
        target_widget = parent_widget or self.parent_widget
        loading_state = LoadingState(
            state_id=state_id,
            message=message,
            loading_type=loading_type,
            show_progress=show_progress,
            parent_widget=target_widget
        )
        
        # 连接信号
        loading_state.finished.connect(lambda: self.finish_loading(state_id))
        loading_state.error.connect(lambda err: self.error_loading(state_id, err))
        
        # 存储状态
        self._loading_states[state_id] = loading_state
        self._state_queue.append(state_id)
        
        # 显示加载状态
        loading_state.show()
        
        # 发出信号
        self.loading_started.emit(state_id)
        
        return loading_state
    
    def update_progress(self, state_id: str, progress: int, message: Optional[str] = None):
        """更新进度"""
        if state_id in self._loading_states:
            self._loading_states[state_id].update_progress(progress, message)
    
    def finish_loading(self, state_id: str):
        """完成加载"""
        if state_id in self._loading_states:
            loading_state = self._loading_states[state_id]
            loading_state.hide()
            
            # 延迟删除，避免立即删除导致的问题
            QTimer.singleShot(1000, lambda: self._remove_state(state_id))
            
            self.loading_finished.emit(state_id)
    
    def error_loading(self, state_id: str, error_message: str):
        """加载错误"""
        if state_id in self._loading_states:
            loading_state = self._loading_states[state_id]
            loading_state.show_error(error_message)
            
            # 延迟删除
            QTimer.singleShot(3000, lambda: self._remove_state(state_id))
            
            self.loading_error.emit(state_id, error_message)
    
    def cancel_loading(self, state_id: str):
        """取消加载"""
        if state_id in self._loading_states:
            self._loading_states[state_id].hide()
            self._remove_state(state_id)
    
    def cancel_all_loading(self):
        """取消所有加载"""
        for state_id in list(self._loading_states.keys()):
            self.cancel_loading(state_id)
    
    def is_loading(self, state_id: Optional[str] = None) -> bool:
        """检查是否在加载"""
        if state_id:
            return state_id in self._loading_states
        return len(self._loading_states) > 0
    
    def get_loading_states(self) -> Dict[str, 'LoadingState']:
        """获取所有加载状态"""
        return self._loading_states.copy()
    
    def _remove_state(self, state_id: str):
        """移除状态"""
        if state_id in self._loading_states:
            del self._loading_states[state_id]
        
        if state_id in self._state_queue:
            self._state_queue.remove(state_id)
    
    def _auto_cleanup(self):
        """自动清理过期状态"""
        import time
        current_time = time.time()
        
        states_to_remove = []
        for state_id, loading_state in self._loading_states.items():
            # 如果状态超过5分钟未活动，自动清理
            if current_time - loading_state.created_time > 300:  # 5分钟
                states_to_remove.append(state_id)
        
        for state_id in states_to_remove:
            self.cancel_loading(state_id)


class LoadingState(QObject):
    """单个加载状态"""
    
    # 信号定义
    finished = Signal()
    error = Signal(str)
    progress_updated = Signal(int, str)
    
    def __init__(
        self,
        state_id: str,
        message: str,
        loading_type: str = "text",
        show_progress: bool = False,
        parent_widget: Optional[QWidget] = None
    ):
        super().__init__()
        
        self.state_id = state_id
        self.message = message
        self.loading_type = loading_type
        self.show_progress = show_progress
        self.parent_widget = parent_widget
        
        import time
        self.created_time = time.time()
        self.last_update_time = time.time()
        
        # 创建UI组件
        self._create_ui()
    
    def _create_ui(self):
        """创建UI组件"""
        if not self.parent_widget:
            return
        
        # 创建加载widget
        self.widget = QWidget(self.parent_widget)
        self.widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(self.widget)
        
        # 消息标签
        self.message_label = QLabel(self.message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)
        
        # 进度条（可选）
        if self.show_progress:
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            layout.addWidget(self.progress_bar)
        
        # 根据类型添加不同的组件
        if self.loading_type == "animation":
            self._add_animation()
        elif self.loading_type == "spinner":
            self._add_spinner()
        
        # 初始隐藏
        self.widget.hide()
    
    def _add_animation(self):
        """添加动画"""
        # 这里可以添加GIF动画或其他动画效果
        pass
    
    def _add_spinner(self):
        """添加转圈动画"""
        # 这里可以添加转圈动画
        pass
    
    def show(self):
        """显示加载状态"""
        if self.widget and self.parent_widget:
            # 居中显示
            parent_rect = self.parent_widget.rect()
            widget_size = self.widget.sizeHint()
            
            x = (parent_rect.width() - widget_size.width()) // 2
            y = (parent_rect.height() - widget_size.height()) // 2
            
            self.widget.move(x, y)
            self.widget.show()
            self.widget.raise_()  # 确保在顶层
    
    def hide(self):
        """隐藏加载状态"""
        if self.widget:
            self.widget.hide()
    
    def update_message(self, message: str):
        """更新消息"""
        self.message = message
        if hasattr(self, 'message_label'):
            self.message_label.setText(message)
        
        import time
        self.last_update_time = time.time()
    
    def update_progress(self, progress: int, message: Optional[str] = None):
        """更新进度"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(progress)
        
        if message:
            self.update_message(message)
        
        self.progress_updated.emit(progress, message or "")
    
    def show_error(self, error_message: str):
        """显示错误"""
        self.update_message(f"错误: {error_message}")
        
        # 改变样式为错误样式
        if self.widget:
            self.widget.setStyleSheet("""
                QWidget {
                    background-color: rgba(220, 53, 69, 0.8);
                    color: white;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
        
        self.error.emit(error_message)
    
    def finish(self):
        """完成加载"""
        self.finished.emit()


# 全局加载状态管理器实例
_global_loading_manager: Optional[LoadingStateManager] = None


def get_loading_manager(parent: Optional[QWidget] = None) -> LoadingStateManager:
    """获取全局加载状态管理器"""
    global _global_loading_manager
    
    if _global_loading_manager is None:
        _global_loading_manager = LoadingStateManager(parent)
    
    return _global_loading_manager


def start_loading(
    state_id: str, 
    message: str = "加载中...", 
    loading_type: str = "text",
    show_progress: bool = False,
    parent_widget: Optional[QWidget] = None
) -> Optional[LoadingState]:
    """快捷方式：开始加载"""
    manager = get_loading_manager(parent_widget)
    return manager.start_loading(state_id, message, loading_type, show_progress, parent_widget)


def finish_loading(state_id: str):
    """快捷方式：完成加载"""
    manager = get_loading_manager()
    manager.finish_loading(state_id)


def error_loading(state_id: str, error_message: str):
    """快捷方式：加载错误"""
    manager = get_loading_manager()
    manager.error_loading(state_id, error_message)
