"""
主题架构定义 - 基于设计令牌的主题模型
实现可持久化的主题Schema，支持单色/渐变/图片三种区域背景
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Literal, Any
from enum import Enum
from pathlib import Path
import json
from datetime import datetime

from .color_utils import ColorUtils  # 导入 ColorUtils


class ThemeMode(Enum):
    """主题模式"""
    LIGHT = "light"
    DARK = "dark"


class RegionPreset(Enum):
    """区域背景预设类型"""
    SOLID = "solid"
    GRADIENT = "gradient"
    IMAGE = "image"


class GradientType(Enum):
    """渐变类型"""
    LINEAR = "linear"
    RADIAL = "radial"
    CONICAL = "conical"


class ImageFit(Enum):
    """图片适配方式"""
    COVER = "cover"
    CONTAIN = "contain"
    TILE = "tile"


class ComponentDensity(Enum):
    """组件密度"""
    COMPACT = "compact"
    REGULAR = "regular"
    COZY = "cozy"


class ComponentShape(Enum):
    """组件形状"""
    PILL = "pill"
    ROUNDED = "rounded"
    SQUARE = "square"


class ComponentIntensity(Enum):
    """组件强度"""
    SUBTLE = "subtle"
    DEFAULT = "default"
    BOLD = "bold"


@dataclass
class ColorStop:
    """渐变色标"""
    pos: float  # 0.0 - 1.0
    color: str  # HEX color


@dataclass
class GradientConfig:
    """渐变配置"""
    type: GradientType
    stops: List[ColorStop]
    angle: Optional[float] = 135.0  # 线性渐变角度


@dataclass
class SolidConfig:
    """纯色配置"""
    color: str  # HEX color or semantic reference
    alpha: Optional[float] = 1.0


@dataclass
class ImageConfig:
    """图片配置"""
    path: str  # 图片路径
    fit: ImageFit = field(default=ImageFit.COVER)
    opacity: float = field(default=1.0)
    overlay: Optional[Union[SolidConfig, GradientConfig]] = field(default=None)
    blur: Literal["off", "low", "med"] = field(default="off")


@dataclass
class RegionOverrides:
    """区域样式覆写"""
    radius: Optional[str] = None
    border: Optional[str] = None
    inset_shadow: Optional[str] = None


@dataclass
class ThemeRegion:
    """主题区域配置"""
    preset: RegionPreset
    solid: Optional[SolidConfig] = None
    gradient: Optional[GradientConfig] = None
    image: Optional[ImageConfig] = None
    overrides: Optional[RegionOverrides] = None

    def __post_init__(self):
        """验证配置一致性"""
        if self.preset == RegionPreset.SOLID and not self.solid:
            raise ValueError("Solid preset requires solid config")
        if self.preset == RegionPreset.GRADIENT and not self.gradient:
            raise ValueError("Gradient preset requires gradient config")
        if self.preset == RegionPreset.IMAGE and not self.image:
            raise ValueError("Image preset requires image config")


@dataclass
class ComponentOverride:
    """组件覆写配置"""
    size_density: Optional[ComponentDensity] = None
    shape: Optional[ComponentShape] = None
    intensity: Optional[ComponentIntensity] = None


@dataclass
class ComponentOverrides:
    """组件白名单覆写"""
    QPushButton: Optional[ComponentOverride] = None
    QLineEdit: Optional[ComponentOverride] = None
    QTabBar: Optional[ComponentOverride] = None
    QScrollBar: Optional[ComponentOverride] = None
    QComboBox: Optional[ComponentOverride] = None
    QSpinBox: Optional[ComponentOverride] = None


@dataclass
class PaletteTokens:
    """基础色彩令牌"""
    mode: ThemeMode
    accent: str  # 主色 HEX
    neutral_scale: List[str]  # 中性色阶 n0-n9
    elevation: Dict[str, int] = field(default_factory=lambda: {"shadow_level": 2})
    radius: Dict[str, str] = field(default_factory=lambda: {"sm": "4px", "md": "8px", "lg": "12px"})
    font: Dict[str, Union[int, float]] = field(default_factory=lambda: {"base_size": 14, "line_height": 1.5})


@dataclass
class SemanticColors:
    """语义颜色（由引擎自动生成）"""
    # 基础表面颜色
    window: str = ""
    surface: str = ""
    surface_alt: str = ""
    
    # 文本颜色
    text_primary: str = ""
    text_secondary: str = ""
    text_tertiary: str = ""
    
    # 边框和分割线
    border: str = ""
    divider: str = ""
    
    # 控件颜色
    control_bg: str = ""
    control_fg: str = ""
    
    # 状态颜色
    state_hover: str = ""
    state_pressed: str = ""
    state_selected: str = ""
    
    # 高亮颜色
    highlight: str = ""
    highlight_text: str = ""


@dataclass
class ThemeConstraints:
    """主题约束条件"""
    min_contrast: float = 4.5  # WCAG AA 标准
    min_image_px: int = 800    # 最小图片分辨率
    max_gradient_stops: int = 4  # 最大渐变色标数


@dataclass
class ThemeMeta:
    """主题元数据"""
    schema_version: str = "1.0.0"
    name: str = "Untitled Theme"
    author: str = "Unknown"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""


@dataclass
class Theme:
    """完整主题定义"""
    meta: ThemeMeta
    palette: PaletteTokens
    semantic: SemanticColors = field(default_factory=SemanticColors)
    regions: Dict[str, ThemeRegion] = field(default_factory=dict)
    component_overrides: ComponentOverrides = field(default_factory=ComponentOverrides)
    constraints: ThemeConstraints = field(default_factory=ThemeConstraints)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        def _convert_value(obj) -> Any:
            if hasattr(obj, '__dict__'):
                if isinstance(obj, Enum):
                    return obj.value
                return {k: _convert_value(v) for k, v in obj.__dict__.items()}
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
            # 确保data不为None
            if data is None:
                print("Warning: Theme data is None, using default theme")
                return create_default_light_theme()
                
            # 处理元信息
            meta_data = data.get('meta', {})
            meta = ThemeMeta(
                name=meta_data.get('name', 'Unknown Theme'),
                author=meta_data.get('author', 'Unknown'),
                schema_version=meta_data.get('schema_version', '1.0.0'),
                description=meta_data.get('description', ''),
                created_at=meta_data.get('created_at', datetime.now().isoformat())
            )
            
            # 处理调色板令牌
            palette_data = data.get('palette', {})
            palette = PaletteTokens(
                mode=ThemeMode(palette_data.get('mode', 'light')),
                accent=palette_data.get('accent', '#0066CC'),
                neutral_scale=palette_data.get('neutral_scale', [
                    "#FFFFFF", "#F5F5F5", "#E0E0E0", "#CCCCCC", "#999999", 
                    "#666666", "#404040", "#2D2D2D", "#1E1E1E", "#0F0F0F"
                ])
            )
            
            # 处理语义颜色（如果存在）
            semantic_data = data.get('semantic', {})
            semantic = SemanticColors(
                window=semantic_data.get('window', '#FFFFFF'),
                surface=semantic_data.get('surface', '#FFFFFF'),
                surface_alt=semantic_data.get('surface_alt', '#F5F5F5'),
                text_primary=semantic_data.get('text_primary', '#1E1E1E'),
                text_secondary=semantic_data.get('text_secondary', '#404040'),
                text_tertiary=semantic_data.get('text_tertiary', '#666666'),
                border=semantic_data.get('border', '#CCCCCC'),
                divider=semantic_data.get('divider', '#E0E0E0'),
                control_bg=semantic_data.get('control_bg', '#F5F5F5'),
                control_fg=semantic_data.get('control_fg', '#1E1E1E'),
                highlight=semantic_data.get('highlight', '#0066CC'),
                highlight_text=semantic_data.get('highlight_text', '#FFFFFF'),
                state_hover=semantic_data.get('state_hover', '#E8E8E8'),
                state_pressed=semantic_data.get('state_pressed', '#D0D0D0'),
                state_selected=semantic_data.get('state_selected', '#0066CC')
            )
            
            # 处理区域配置（简化处理）
            regions_data = data.get('regions', {})
            regions = {}
            for region_name, region_data in regions_data.items():
                if region_data and isinstance(region_data, dict):
                    # 简单处理，只支持纯色背景
                    solid_data = region_data.get('solid', {})
                    if solid_data:
                        regions[region_name] = ThemeRegion(
                            preset=RegionPreset.SOLID,
                            solid=SolidConfig(color=solid_data.get('color', '#FFFFFF'))
                        )
            
            # 处理组件覆盖（简化处理）
            component_overrides_data = data.get('component_overrides', {})
            component_overrides = ComponentOverrides()
            
            # 处理约束（使用默认值）
            constraints = ThemeConstraints()
            
            return cls(
                meta=meta,
                palette=palette,
                semantic=semantic,
                regions=regions,
                component_overrides=component_overrides,
                constraints=constraints
            )
            
        except Exception as e:
            print(f"Warning: Failed to deserialize theme from dict: {e}")
            # 返回默认主题作为回退
            return create_default_light_theme()
    
    def save_to_file(self, file_path: Path):
        """保存主题到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: Path) -> 'Theme':
        """从文件加载主题"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def validate(self) -> List[str]:
        """验证主题配置，返回错误列表"""
        errors = []
        
        # Schema级校验
        if not self.meta.schema_version:
            errors.append("E3: 缺少 schema_version")
        if self.palette.mode not in [ThemeMode.LIGHT, ThemeMode.DARK]:
            errors.append("E3: mode 必须是 light 或 dark")
        if not self.palette.accent or not self.palette.accent.startswith('#'):
            errors.append("E3: accent 必须是有效的 HEX 颜色值")
        
        # 中性色阶校验
        if len(self.palette.neutral_scale) < 7:
            errors.append("E2: 中性色阶至少需要7个颜色")
        else:
            # 检查亮度单调性
            for i in range(1, len(self.palette.neutral_scale)):
                curr = ColorUtils.hex_to_lch(self.palette.neutral_scale[i])
                prev = ColorUtils.hex_to_lch(self.palette.neutral_scale[i-1])
                if abs(curr[0] - prev[0]) < 2:  # 亮度差异太小
                    errors.append(f"E1: 中性色阶 {i} 与 {i-1} 亮度差异过小")
        
        # 区域配置校验
        for region_name, region in self.regions.items():
            if region.preset == RegionPreset.GRADIENT and region.gradient:
                # 渐变校验
                if len(region.gradient.stops) < 2:
                    errors.append(f"E2: 区域 {region_name} 的渐变至少需要2个色标")
                if len(region.gradient.stops) > self.constraints.max_gradient_stops:
                    errors.append(f"E1: 区域 {region_name} 的渐变色标数超过限制")
                # 检查渐变位置单调性
                positions = [stop.pos for stop in region.gradient.stops]
                if not all(positions[i] <= positions[i+1] for i in range(len(positions)-1)):
                    errors.append(f"E2: 区域 {region_name} 的渐变位置必须单调递增")
            
            elif region.preset == RegionPreset.IMAGE:
                # 图片校验
                if not region.image:
                    errors.append(f"E2: 区域 {region_name} 缺少图片配置")
                    continue
                
                if not getattr(region.image, 'path', None):
                    errors.append(f"E2: 区域 {region_name} 缺少图片路径")
                else:
                    img_path = Path(region.image.path)
                    if not img_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                        errors.append(f"E2: 区域 {region_name} 的图片格式不受支持 ({img_path.suffix})")
        
        # 组件覆写校验
        for component in ['QPushButton', 'QLineEdit', 'QTabBar', 'QScrollBar']:
            override = getattr(self.component_overrides, component, None)
            if override:
                if override.size_density and override.size_density not in ComponentDensity:
                    errors.append(f"E1: {component} 的 size_density 无效")
                if override.shape and override.shape not in ComponentShape:
                    errors.append(f"E1: {component} 的 shape 无效")
        
        # 主题约束校验
        if self.constraints.min_contrast < 4.5:  # WCAG AA 标准
            errors.append("E1: 最小对比度不应低于 4.5:1")
        
        return errors


# 预定义区域名称
class RegionNames:
    """标准区域名称常量"""
    SIDEBAR = "sidebar"
    CHAT_PANEL = "chat_panel"
    COMPOSER = "composer"
    TOOLBAR = "toolbar"
    SETTINGS_DIALOG = "settings_dialog"
    TITLEBAR = "titlebar"
    WELCOME_PAGE = "welcome_page"
    TAB_BAR = "tab_bar"
    STATUS_BAR = "status_bar"
    CONTEXT_MENU = "context_menu"


# 默认主题工厂函数
def create_default_light_theme() -> Theme:
    """创建默认亮色主题"""
    return Theme(
        meta=ThemeMeta(
            name="Default Light",
            author="System",
            description="优化的默认亮色主题：侧边栏和标签栏浅灰，其他部分白色，文字黑色"
        ),
        palette=PaletteTokens(
            mode=ThemeMode.LIGHT,
            accent="#0078D4",  # Microsoft蓝，现代的主色
            neutral_scale=[
                "#FFFFFF",  # n0 - 纯白背景
                "#FFFFFF",  # n1 - 白色内容区
                "#F0F0F0",  # n2 - 浅灰（侧边栏、标签栏）
                "#E8E8E8",  # n3 - 边框灰
                "#D0D0D0",  # n4 - 分割线
                "#A0A0A0",  # n5 - 禁用灰
                "#666666",  # n6 - 次要文本
                "#333333",  # n7 - 主要文本
                "#000000",  # n8 - 黑色文字
                "#000000"   # n9 - 纯黑
            ]
        ),
        regions={
            RegionNames.SIDEBAR: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#F0F0F0"),  # 浅灰色
                overrides=RegionOverrides(
                    border="1px solid #E8E8E8",
                    radius="0px"
                )
            ),
            RegionNames.CHAT_PANEL: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#FFFFFF"),  # 白色
                overrides=RegionOverrides(
                    border="none"
                )
            ),
            RegionNames.COMPOSER: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#FFFFFF"),  # 白色
                overrides=RegionOverrides(
                    border="2px solid #E8E8E8",
                    radius="8px"
                )
            ),
            RegionNames.TOOLBAR: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#FFFFFF"),  # 白色
                overrides=RegionOverrides(
                    border="1px solid #E8E8E8"
                )
            ),
            RegionNames.TAB_BAR: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#F0F0F0"),  # 浅灰色
                overrides=RegionOverrides(
                    border="1px solid #E8E8E8"
                )
            ),
            RegionNames.STATUS_BAR: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#F0F0F0"),  # 浅灰色
                overrides=RegionOverrides(
                    border="1px solid #E8E8E8"
                )
            ),
            RegionNames.WELCOME_PAGE: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#FFFFFF")  # 白色
            )
        }
    )


def create_default_dark_theme() -> Theme:
    """创建默认暗色主题"""
    return Theme(
        meta=ThemeMeta(
            name="Default Dark",
            author="System",
            description="优化的默认暗色主题：侧边栏和标签栏全黑，其他部分深灰色，文字白色"
        ),
        palette=PaletteTokens(
            mode=ThemeMode.DARK,
            accent="#0078D4",  # 保持一致的主色
            neutral_scale=[
                "#FFFFFF",  # n0 - 白色文字
                "#F0F0F0",  # n1 - 浅色文本
                "#E0E0E0",  # n2 - 次要文本
                "#C0C0C0",  # n3 - 禁用文本
                "#808080",  # n4 - 边框灰
                "#606060",  # n5 - 分割线
                "#404040",  # n6 - 深灰背景
                "#2A2A2A",  # n7 - 更深的灰
                "#000000",  # n8 - 全黑（侧边栏、标签栏）
                "#000000"   # n9 - 全黑
            ]
        ),
        regions={
            RegionNames.SIDEBAR: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#000000"),  # 全黑
                overrides=RegionOverrides(
                    border="1px solid #2A2A2A",
                    radius="0px"
                )
            ),
            RegionNames.CHAT_PANEL: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#404040"),  # 深灰色
                overrides=RegionOverrides(
                    border="none"
                )
            ),
            RegionNames.COMPOSER: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#404040"),  # 深灰色
                overrides=RegionOverrides(
                    border="2px solid #606060",
                    radius="8px"
                )
            ),
            RegionNames.TOOLBAR: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#404040"),  # 深灰色
                overrides=RegionOverrides(
                    border="1px solid #606060"
                )
            ),
            RegionNames.TAB_BAR: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#000000"),  # 全黑
                overrides=RegionOverrides(
                    border="1px solid #2A2A2A"
                )
            ),
            RegionNames.STATUS_BAR: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#000000"),  # 全黑
                overrides=RegionOverrides(
                    border="1px solid #2A2A2A"
                )
            ),
            RegionNames.WELCOME_PAGE: ThemeRegion(
                preset=RegionPreset.SOLID,
                solid=SolidConfig(color="#404040")  # 深灰色
            )
        }
    )
