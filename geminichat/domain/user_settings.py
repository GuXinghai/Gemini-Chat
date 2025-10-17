# domain/user_settings.py
# 存储用户偏好/配置

import json
import threading
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict
from geminichat.domain.model_type import ModelType

# —— 如果需要迁移、版本控制，可在这里加版本号字段 —— 
SETTINGS_VERSION = 1

@dataclass
class UserSettings:
    """
    管理用户偏好配置，包括默认值、加载/保存、字段更新等功能。
    """
    preferred_model: ModelType = ModelType.GEMINI_2_5_FLASH
    dark_mode: bool = False
    history_limit: int = 100               # 最多保留多少条聊天记录
    user_name: str = "用户"                 # 用户显示名称
    enable_streaming: bool = True          # 启用流式回复（默认开启）
    other_flags: Dict[str, Any] = field(default_factory=dict)
    # 内部字段，不序列化到磁盘
    _file_path: Path = field(init=False, repr=False, compare=False)
    _lock: threading.Lock = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        # 初始化文件路径 & 线程锁
        self._file_path = Path.home() / ".gemini_chat_settings.json"
        self._lock = threading.Lock()

    @classmethod
    def load(cls) -> "UserSettings":
        """
        从磁盘加载设置；出错时返回默认配置并写回文件。
        """
        inst = cls()  # 先用默认值
        try:
            raw = inst._file_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            # 兼容历史版本：检查版本号
            if data.get("version") != SETTINGS_VERSION:
                # TODO: 在此处写迁移逻辑
                pass
            # 只解析我们关心的字段
            inst.preferred_model = ModelType(data.get("preferred_model", inst.preferred_model.value))
            inst.dark_mode = bool(data.get("dark_mode", inst.dark_mode))
            inst.history_limit = int(data.get("history_limit", inst.history_limit))
            inst.user_name = str(data.get("user_name", inst.user_name))
            inst.enable_streaming = bool(data.get("enable_streaming", inst.enable_streaming))
            inst.other_flags = data.get("other_flags", inst.other_flags)
        except FileNotFoundError:
            # 第一次使用，直接写出默认配置
            inst.save()
        except (json.JSONDecodeError, ValueError) as e:
            # 配置文件损坏：重命名备份，恢复默认
            backup = inst._file_path.with_suffix(".broken.json")
            inst._file_path.rename(backup)
            inst.save()
        return inst

    def save(self) -> None:
        """
        将当前配置序列化写入磁盘，保证原子性与线程安全。
        """
        # 创建数据字典，排除不需要序列化的字段
        payload = {
            'preferred_model': self.preferred_model.value,
            'dark_mode': self.dark_mode,
            'history_limit': self.history_limit,
            'user_name': self.user_name,
            'enable_streaming': self.enable_streaming,
            'other_flags': self.other_flags,
            'version': SETTINGS_VERSION
        }

        text = json.dumps(payload, ensure_ascii=False, indent=2)
        tmp = self._file_path.with_suffix(".tmp")
        with self._lock:
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(self._file_path)

    # —— 若需要更新单个字段，可以用下面的 helper —— 
    def update_model(self, model: ModelType) -> None:
        """
        切换模型，并立即持久化。
        """
        if model != self.preferred_model:
            self.preferred_model = model
            self.save()

    def update_user_name(self, name: str) -> None:
        """
        更新用户名称，并立即持久化。
        """
        if name != self.user_name:
            self.user_name = name
            self.save()

    def update_streaming(self, enable: bool) -> None:
        """
        更新流式回复设置，并立即持久化。
        """
        if enable != self.enable_streaming:
            self.enable_streaming = enable
            self.save()

    def update_flag(self, key: str, value: Any) -> None:
        """
        通用设置更新：修改 other_flags 下任意键值并持久化。
        """
        self.other_flags[key] = value
        self.save()
