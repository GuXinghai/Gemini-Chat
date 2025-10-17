"""
主题模型：定义主题结构和基本组件
提供统一的主题格式和颜色管理
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from enum import Enum
from pathlib import Path
import json
from datetime import datetime
import colorsys


class ThemeMode(Enum):
    """主题模式"""
    LIGHT = "light"
    DARK = "dark"


class ColorToken(Enum):
    """颜色令牌定义"""
    # 基础色
    BACKGROUND = "background"  # 主背景色
    SURFACE = "surface"  # 表面色
    SURFACE_ALT = "surface_alt"  # 替代表面色
    ACCENT = "accent"  # 主色
    ACCENT_ALT = "accent_alt"  # 替代主色
    
    # 文字色
    TEXT_PRIMARY = "text_primary"  # 主要文本色
    TEXT_SECONDARY = "text_secondary"  # 次要文本色
    TEXT_TERTIARY = "text_tertiary"  # 第三级文本色
    TEXT_ON_ACCENT = "text_on_accent"  # 主色上的文字颜色
    
    # 边界和分隔线
    BORDER = "border"  # 边框色
    DIVIDER = "divider"  # 分隔线
    
    # 状态色
    HOVER = "hover"  # 悬停状态
    PRESSED = "pressed"  # 按下状态
    DISABLED = "disabled"  # 禁用状态
    
    # 语义色
    SUCCESS = "success"  # 成功色
    WARNING = "warning"  # 警告色
    ERROR = "error"  # 错误色
    INFO = "info"  # 信息色


class ColorRole(Enum):
    """UI区域角色定义"""
    # 主要区域
    SIDEBAR = "sidebar"  # 侧边栏
    CHAT_PANEL = "chat_panel"  # 聊天面板
    COMPOSER = "composer"  # 输入区
    TOOLBAR = "toolbar"  # 工具栏
    TAB_BAR = "tab_bar"  # 标签栏
    STATUS_BAR = "status_bar"  # 状态栏
    
    # 组件区域
    BUTTON = "button"  # 按钮
    INPUT = "input"  # 输入框
    DROPDOWN = "dropdown"  # 下拉菜单
    CHECKBOX = "checkbox"  # 复选框
    RADIO = "radio"  # 单选框
    SLIDER = "slider"  # 滑块
    
    # 其他区域
    DIALOG = "dialog"  # 对话框
    POPUP = "popup"  # 弹出框
    TOOLTIP = "tooltip"  # 工具提示
    MENU = "menu"  # 菜单


@dataclass
class ThemeMeta:
    """主题元数据"""
    name: str = "未命名主题"
    author: str = "未知"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""
    version: str = "1.0.0"


@dataclass
class ColorPalette:
    """主题调色板定义"""
    # 主模式
    mode: ThemeMode = ThemeMode.LIGHT
    
    # 调色板颜色
    colors: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后验证颜色"""
        # 确保所有颜色令牌都有定义
        for token in ColorToken:
            if token.value not in self.colors:
                # 设置默认值
                if self.mode == ThemeMode.LIGHT:
                    self.colors[token.value] = "#000000"  # 默认黑色
                else:
                    self.colors[token.value] = "#FFFFFF"  # 默认白色
    
    def get(self, token: Union[ColorToken, str]) -> str:
        """获取颜色值"""
        token_key = token.value if isinstance(token, ColorToken) else token
        return self.colors.get(token_key, "#808080")  # 默认灰色
    
    def set(self, token: Union[ColorToken, str], value: str) -> None:
        """设置颜色值"""
        token_key = token.value if isinstance(token, ColorToken) else token
        self.colors[token_key] = value
    
    def ensure_contrast(self, background_token: ColorToken, text_token: ColorToken, 
                       min_contrast: float = 4.5) -> None:
        """确保文本和背景之间有足够的对比度"""
        bg_color = self.get(background_token)
        text_color = self.get(text_token)
        
        # 如果对比度不足，调整文本颜色
        contrast = calculate_contrast(bg_color, text_color)
        if contrast < min_contrast:
            # 决定是使文本更亮还是更暗
            if self.mode == ThemeMode.LIGHT:
                # 亮色主题，文本应该更暗
                text_color = darken_color(text_color, min_contrast, bg_color)
            else:
                # 暗色主题，文本应该更亮
                text_color = lighten_color(text_color, min_contrast, bg_color)
            
            self.set(text_token, text_color)


@dataclass
class RegionColors:
    """UI区域颜色定义"""
    # 区域颜色映射
    regions: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后验证区域颜色"""
        # 确保所有区域角色都有定义
        for role in ColorRole:
            if role.value not in self.regions:
                self.regions[role.value] = {
                    "background": "",
                    "text": "",
                    "border": ""
                }
    
    def get(self, role: Union[ColorRole, str], property: str = "background") -> str:
        """获取区域颜色"""
        role_key = role.value if isinstance(role, ColorRole) else role
        return self.regions.get(role_key, {}).get(property, "")
    
    def set(self, role: Union[ColorRole, str], property: str, value: str) -> None:
        """设置区域颜色"""
        role_key = role.value if isinstance(role, ColorRole) else role
        if role_key not in self.regions:
            self.regions[role_key] = {}
        self.regions[role_key][property] = value
    
    def derive_from_palette(self, palette: ColorPalette) -> None:
        """从调色板派生区域颜色"""
        for role in ColorRole:
            role_key = role.value
            
            # 设置默认背景色
            if role in [ColorRole.SIDEBAR, ColorRole.TOOLBAR, ColorRole.TAB_BAR, ColorRole.STATUS_BAR]:
                self.set(role, "background", palette.get(ColorToken.SURFACE_ALT))
            elif role in [ColorRole.DIALOG, ColorRole.POPUP, ColorRole.MENU, ColorRole.DROPDOWN]:
                self.set(role, "background", palette.get(ColorToken.SURFACE))
            else:
                self.set(role, "background", palette.get(ColorToken.BACKGROUND))
            
            # 设置默认文本色
            self.set(role, "text", palette.get(ColorToken.TEXT_PRIMARY))
            
            # 设置默认边框色
            self.set(role, "border", palette.get(ColorToken.BORDER))
            
        # 特殊区域覆盖
        self.set(ColorRole.BUTTON, "background", palette.get(ColorToken.ACCENT))
        self.set(ColorRole.BUTTON, "text", palette.get(ColorToken.TEXT_ON_ACCENT))


@dataclass
class Theme:
    """主题定义"""
    meta: ThemeMeta
    colors: ColorPalette
    regions: RegionColors
    
    @classmethod
    def create(cls, name: str, mode: ThemeMode = ThemeMode.LIGHT, 
              author: str = "System", description: str = "") -> 'Theme':
        """创建新主题"""
        meta = ThemeMeta(name=name, author=author, description=description)
        
        # 创建默认调色板
        if mode == ThemeMode.LIGHT:
            colors = create_light_palette()
        else:
            colors = create_dark_palette()
        
        # 创建区域颜色
        regions = RegionColors()
        regions.derive_from_palette(colors)
        
        return cls(meta=meta, colors=colors, regions=regions)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        def _convert_value(obj) -> Any:
            if hasattr(obj, '__dict__'):
                if isinstance(obj, Enum):
                    return obj.value
                return {k: _convert_value(v) for k, v in obj.__dict__.items() 
                       if not k.startswith('_')}
            elif isinstance(obj, dict):
                return {k: _convert_value(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_convert_value(item) for item in obj]
            elif isinstance(obj, Enum):
                return obj.value
            return obj
        
        return _convert_value(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        """从字典创建主题（用于反序列化）"""
        try:
            # 处理元信息
            meta_data = data.get('meta', {})
            meta = ThemeMeta(
                name=meta_data.get('name', '未命名主题'),
                author=meta_data.get('author', '未知'),
                version=meta_data.get('version', '1.0.0'),
                description=meta_data.get('description', ''),
                created_at=meta_data.get('created_at', datetime.now().isoformat())
            )
            
            # 处理调色板
            colors_data = data.get('colors', {})
            mode = ThemeMode(colors_data.get('mode', 'light'))
            
            colors = ColorPalette(mode=mode)
            if 'colors' in colors_data:
                for key, value in colors_data['colors'].items():
                    colors.set(key, value)
            
            # 处理区域颜色
            regions_data = data.get('regions', {})
            regions = RegionColors()
            
            if 'regions' in regions_data:
                for role, properties in regions_data['regions'].items():
                    for prop, value in properties.items():
                        regions.set(role, prop, value)
            
            # 如果区域颜色为空，从调色板派生
            if not regions.regions:
                regions.derive_from_palette(colors)
            
            return cls(meta=meta, colors=colors, regions=regions)
            
        except Exception as e:
            print(f"从字典创建主题失败: {e}")
            return create_default_light_theme()
    
    def save_to_file(self, file_path: Path) -> None:
        """保存主题到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: Path) -> 'Theme':
        """从文件加载主题"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def ensure_all_contrasts(self) -> None:
        """确保所有文本颜色与背景颜色有足够对比度"""
        # 确保基本调色板对比度
        self.colors.ensure_contrast(ColorToken.BACKGROUND, ColorToken.TEXT_PRIMARY)
        self.colors.ensure_contrast(ColorToken.BACKGROUND, ColorToken.TEXT_SECONDARY)
        self.colors.ensure_contrast(ColorToken.SURFACE, ColorToken.TEXT_PRIMARY)
        self.colors.ensure_contrast(ColorToken.SURFACE_ALT, ColorToken.TEXT_PRIMARY)
        self.colors.ensure_contrast(ColorToken.ACCENT, ColorToken.TEXT_ON_ACCENT)
        
        # 确保所有区域对比度
        for role in ColorRole:
            bg = self.regions.get(role, "background")
            if not bg:  # 使用默认背景色
                bg = self.colors.get(ColorToken.BACKGROUND)
            
            text = self.regions.get(role, "text")
            if text:
                # 确保区域文本和背景有足够对比度
                contrast = calculate_contrast(bg, text)
                if contrast < 4.5:
                    # 调整文本颜色
                    if self.colors.mode == ThemeMode.LIGHT:
                        text = darken_color(text, 4.5, bg)
                    else:
                        text = lighten_color(text, 4.5, bg)
                    self.regions.set(role, "text", text)


# 颜色工具函数
def hex_to_rgb(hex_color: str) -> tuple:
    """将十六进制颜色转换为RGB元组"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple) -> str:
    """将RGB元组转换为十六进制颜色"""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def calculate_luminance(color: str) -> float:
    """计算颜色的亮度（用于对比度计算）"""
    rgb = hex_to_rgb(color)
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    
    # 将RGB值转换为线性RGB值
    rgb_linear = []
    for c in [r, g, b]:
        if c <= 0.03928:
            rgb_linear.append(c / 12.92)
        else:
            rgb_linear.append(((c + 0.055) / 1.055) ** 2.4)
    
    # 计算亮度
    return 0.2126 * rgb_linear[0] + 0.7152 * rgb_linear[1] + 0.0722 * rgb_linear[2]


def calculate_contrast(color1: str, color2: str) -> float:
    """计算两个颜色之间的对比度"""
    lum1 = calculate_luminance(color1)
    lum2 = calculate_luminance(color2)
    
    # 确保较亮的颜色是第一个
    brighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    # 计算对比度
    return (brighter + 0.05) / (darker + 0.05)


def lighten_color(hex_color: str, target_contrast: float, bg_color: str) -> str:
    """增亮颜色直到达到目标对比度"""
    rgb = hex_to_rgb(hex_color)
    
    # 将RGB转换为HSL
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    # 逐步增加亮度，直到达到目标对比度
    steps = 10
    step_size = (1.0 - l) / steps
    
    for _ in range(steps):
        l = min(0.95, l + step_size)  # 避免纯白
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        new_color = rgb_to_hex((int(r * 255), int(g * 255), int(b * 255)))
        
        if calculate_contrast(new_color, bg_color) >= target_contrast:
            return new_color
    
    # 如果仍然无法达到目标对比度，返回白色
    return "#FFFFFF"


def darken_color(hex_color: str, target_contrast: float, bg_color: str) -> str:
    """加深颜色直到达到目标对比度"""
    rgb = hex_to_rgb(hex_color)
    
    # 将RGB转换为HSL
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    # 逐步减少亮度，直到达到目标对比度
    steps = 10
    step_size = l / steps
    
    for _ in range(steps):
        l = max(0.05, l - step_size)  # 避免纯黑
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        new_color = rgb_to_hex((int(r * 255), int(g * 255), int(b * 255)))
        
        if calculate_contrast(new_color, bg_color) >= target_contrast:
            return new_color
    
    # 如果仍然无法达到目标对比度，返回黑色
    return "#000000"


def create_light_palette() -> ColorPalette:
    """创建亮色调色板"""
    return ColorPalette(
        mode=ThemeMode.LIGHT,
        colors={
            # 基础色
            ColorToken.BACKGROUND.value: "#FFFFFF",  # 纯白背景
            ColorToken.SURFACE.value: "#F8F8F8",  # 浅灰表面
            ColorToken.SURFACE_ALT.value: "#F0F0F0",  # 更浅灰替代表面
            ColorToken.ACCENT.value: "#0078D4",  # 微软蓝
            ColorToken.ACCENT_ALT.value: "#106EBE",  # 深蓝
            
            # 文字色
            ColorToken.TEXT_PRIMARY.value: "#202020",  # 近黑主要文本
            ColorToken.TEXT_SECONDARY.value: "#666666",  # 深灰次要文本
            ColorToken.TEXT_TERTIARY.value: "#A0A0A0",  # 浅灰第三级文本
            ColorToken.TEXT_ON_ACCENT.value: "#FFFFFF",  # 主色上的文字为白色
            
            # 边界和分隔线
            ColorToken.BORDER.value: "#E0E0E0",  # 浅灰边框
            ColorToken.DIVIDER.value: "#EEEEEE",  # 浅灰分隔线
            
            # 状态色
            ColorToken.HOVER.value: "#F5F5F5",  # 悬停状态
            ColorToken.PRESSED.value: "#E0E0E0",  # 按下状态
            ColorToken.DISABLED.value: "#CCCCCC",  # 禁用状态
            
            # 语义色
            ColorToken.SUCCESS.value: "#107C10",  # 绿色成功
            ColorToken.WARNING.value: "#FFB900",  # 黄色警告
            ColorToken.ERROR.value: "#D83B01",  # 红色错误
            ColorToken.INFO.value: "#0078D4"  # 蓝色信息
        }
    )


def create_dark_palette() -> ColorPalette:
    """创建暗色调色板"""
    return ColorPalette(
        mode=ThemeMode.DARK,
        colors={
            # 基础色
            ColorToken.BACKGROUND.value: "#1F1F1F",  # 深灰背景
            ColorToken.SURFACE.value: "#252525",  # 中灰表面
            ColorToken.SURFACE_ALT.value: "#2D2D2D",  # 浅灰替代表面
            ColorToken.ACCENT.value: "#0078D4",  # 保持微软蓝
            ColorToken.ACCENT_ALT.value: "#2B88D8",  # 亮蓝
            
            # 文字色
            ColorToken.TEXT_PRIMARY.value: "#F0F0F0",  # 近白主要文本
            ColorToken.TEXT_SECONDARY.value: "#A0A0A0",  # 浅灰次要文本
            ColorToken.TEXT_TERTIARY.value: "#767676",  # 中灰第三级文本
            ColorToken.TEXT_ON_ACCENT.value: "#FFFFFF",  # 主色上的文字为白色
            
            # 边界和分隔线
            ColorToken.BORDER.value: "#404040",  # 中灰边框
            ColorToken.DIVIDER.value: "#333333",  # 深灰分隔线
            
            # 状态色
            ColorToken.HOVER.value: "#333333",  # 悬停状态
            ColorToken.PRESSED.value: "#404040",  # 按下状态
            ColorToken.DISABLED.value: "#3C3C3C",  # 禁用状态
            
            # 语义色
            ColorToken.SUCCESS.value: "#0EA30E",  # 亮绿色成功
            ColorToken.WARNING.value: "#FFC83D",  # 亮黄色警告
            ColorToken.ERROR.value: "#F44336",  # 亮红色错误
            ColorToken.INFO.value: "#2B88D8"  # 亮蓝色信息
        }
    )


def create_default_light_theme() -> Theme:
    """创建默认亮色主题"""
    # 创建基础调色板
    colors = create_light_palette()
    
    # 创建区域颜色
    regions = RegionColors()
    regions.derive_from_palette(colors)
    
    # 设置特定区域颜色
    regions.set(ColorRole.SIDEBAR, "background", "#F0F0F0")
    regions.set(ColorRole.SIDEBAR, "text", "#202020")
    
    regions.set(ColorRole.TAB_BAR, "background", "#F0F0F0")
    regions.set(ColorRole.TAB_BAR, "text", "#202020")
    
    regions.set(ColorRole.TOOLBAR, "background", "#F8F8F8")
    regions.set(ColorRole.TOOLBAR, "text", "#202020")
    
    regions.set(ColorRole.STATUS_BAR, "background", "#F0F0F0")
    regions.set(ColorRole.STATUS_BAR, "text", "#666666")
    
    regions.set(ColorRole.CHAT_PANEL, "background", "#FFFFFF")
    regions.set(ColorRole.CHAT_PANEL, "text", "#202020")
    
    regions.set(ColorRole.COMPOSER, "background", "#FFFFFF")
    regions.set(ColorRole.COMPOSER, "text", "#202020")
    
    return Theme(
        meta=ThemeMeta(
            name="默认亮色",
            author="系统",
            description="默认亮色主题：白色背景、黑色文字、蓝色强调色"
        ),
        colors=colors,
        regions=regions
    )


def create_default_dark_theme() -> Theme:
    """创建默认暗色主题"""
    # 创建基础调色板
    colors = create_dark_palette()
    
    # 创建区域颜色
    regions = RegionColors()
    regions.derive_from_palette(colors)
    
    # 设置特定区域颜色
    regions.set(ColorRole.SIDEBAR, "background", "#252525")
    regions.set(ColorRole.SIDEBAR, "text", "#F0F0F0")
    
    regions.set(ColorRole.TAB_BAR, "background", "#252525")
    regions.set(ColorRole.TAB_BAR, "text", "#F0F0F0")
    
    regions.set(ColorRole.TOOLBAR, "background", "#252525")
    regions.set(ColorRole.TOOLBAR, "text", "#F0F0F0")
    
    regions.set(ColorRole.STATUS_BAR, "background", "#252525")
    regions.set(ColorRole.STATUS_BAR, "text", "#A0A0A0")
    
    regions.set(ColorRole.CHAT_PANEL, "background", "#1F1F1F")
    regions.set(ColorRole.CHAT_PANEL, "text", "#F0F0F0")
    
    regions.set(ColorRole.COMPOSER, "background", "#2D2D2D")
    regions.set(ColorRole.COMPOSER, "text", "#F0F0F0")
    
    return Theme(
        meta=ThemeMeta(
            name="默认暗色",
            author="系统",
            description="默认暗色主题：深灰背景、白色文字、蓝色强调色"
        ),
        colors=colors,
        regions=regions
    )
