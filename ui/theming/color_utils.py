"""
颜色工具模块 - 处理颜色计算、对比度校正和语义颜色推导
"""
import re
import math
from typing import Tuple, List, Optional
from colorsys import rgb_to_hls, hls_to_rgb


class ColorUtils:
    """颜色工具类"""
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """将十六进制颜色转换为RGB"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        if len(hex_color) != 6:
            raise ValueError(f"Invalid hex color: {hex_color}")
        rgb_values = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (rgb_values[0], rgb_values[1], rgb_values[2])
    
    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """将RGB转换为十六进制颜色"""
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def hex_to_lch(hex_color: str) -> Tuple[float, float, float]:
        """将十六进制颜色转换为LCH（亮度、色度、色相）"""
        r, g, b = ColorUtils.hex_to_rgb(hex_color)
        # 简化的RGB到LCH转换
        # 这里我们用一个近似值：亮度用相对亮度，色度用RGB标准差，色相用RGB到HSL转换
        l = ContrastCalculator.relative_luminance(hex_color) * 100
        h, s, _ = ColorUtils.rgb_to_hsl(r, g, b)
        c = s  # 简化：用HSL的饱和度作为色度近似值
        return l, c, h

    @staticmethod
    def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
        """RGB转HSL"""
        r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
        h, l, s = rgb_to_hls(r_norm, g_norm, b_norm)
        return h * 360, s * 100, l * 100
    
    @staticmethod
    def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
        """HSL转RGB"""
        h, s, l = h / 360.0, s / 100.0, l / 100.0
        r, g, b = hls_to_rgb(h, l, s)
        return int(r * 255), int(g * 255), int(b * 255)
    
    @staticmethod
    def adjust_lightness(hex_color: str, delta: float) -> str:
        """调整颜色亮度，delta范围-100到100"""
        r, g, b = ColorUtils.hex_to_rgb(hex_color)
        h, s, l = ColorUtils.rgb_to_hsl(r, g, b)
        l = max(0, min(100, l + delta))
        r, g, b = ColorUtils.hsl_to_rgb(h, s, l)
        return ColorUtils.rgb_to_hex(r, g, b)
    
    @staticmethod
    def adjust_saturation(hex_color: str, delta: float) -> str:
        """调整颜色饱和度，delta范围-100到100"""
        r, g, b = ColorUtils.hex_to_rgb(hex_color)
        h, s, l = ColorUtils.rgb_to_hsl(r, g, b)
        s = max(0, min(100, s + delta))
        r, g, b = ColorUtils.hsl_to_rgb(h, s, l)
        return ColorUtils.rgb_to_hex(r, g, b)
    
    @staticmethod
    def blend_colors(color1: str, color2: str, ratio: float = 0.5) -> str:
        """混合两种颜色，ratio为color2的比例（0-1）"""
        r1, g1, b1 = ColorUtils.hex_to_rgb(color1)
        r2, g2, b2 = ColorUtils.hex_to_rgb(color2)
        
        r = int(r1 * (1 - ratio) + r2 * ratio)
        g = int(g1 * (1 - ratio) + g2 * ratio)
        b = int(b1 * (1 - ratio) + b2 * ratio)
        
        return ColorUtils.rgb_to_hex(r, g, b)
    
    @staticmethod
    def get_complementary_color(hex_color: str) -> str:
        """获取互补色"""
        r, g, b = ColorUtils.hex_to_rgb(hex_color)
        h, s, l = ColorUtils.rgb_to_hsl(r, g, b)
        h = (h + 180) % 360  # 色相偏移180度
        r, g, b = ColorUtils.hsl_to_rgb(h, s, l)
        return ColorUtils.rgb_to_hex(r, g, b)
    
    @staticmethod
    def generate_color_scale(base_color: str, steps: int = 10) -> List[str]:
        """基于基色生成颜色阶"""
        colors = []
        for i in range(steps):
            # 从最亮到最暗
            lightness_delta = 50 - (100 / (steps - 1)) * i
            color = ColorUtils.adjust_lightness(base_color, lightness_delta)
            colors.append(color)
        return colors


class ContrastCalculator:
    """对比度计算器"""
    
    @staticmethod
    def relative_luminance(hex_color: str) -> float:
        """计算相对亮度（WCAG标准）"""
        r, g, b = ColorUtils.hex_to_rgb(hex_color)
        
        # 转换为sRGB
        def srgb_to_linear(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        
        r_linear = srgb_to_linear(r)
        g_linear = srgb_to_linear(g)
        b_linear = srgb_to_linear(b)
        
        # WCAG相对亮度公式
        return 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear
    
    @staticmethod
    def contrast_ratio(color1: str, color2: str) -> float:
        """计算两种颜色的对比度（WCAG标准）"""
        l1 = ContrastCalculator.relative_luminance(color1)
        l2 = ContrastCalculator.relative_luminance(color2)
        
        # 确保较亮的颜色在分子
        if l1 < l2:
            l1, l2 = l2, l1
        
        return (l1 + 0.05) / (l2 + 0.05)
    
    @staticmethod
    def meets_wcag_aa(color1: str, color2: str) -> bool:
        """检查是否满足WCAG AA标准（4.5:1）"""
        return ContrastCalculator.contrast_ratio(color1, color2) >= 4.5
    
    @staticmethod
    def meets_wcag_aaa(color1: str, color2: str) -> bool:
        """检查是否满足WCAG AAA标准（7:1）"""
        return ContrastCalculator.contrast_ratio(color1, color2) >= 7.0
    
    @staticmethod
    def adjust_for_contrast(foreground: str, background: str, 
                           target_ratio: float = 4.5) -> str:
        """调整前景色以达到目标对比度"""
        current_ratio = ContrastCalculator.contrast_ratio(foreground, background)
        
        if current_ratio >= target_ratio:
            return foreground
        
        # 尝试调整亮度
        bg_luminance = ContrastCalculator.relative_luminance(background)
        
        # 决定是调亮还是调暗
        max_attempts = 100
        step = 5 if bg_luminance > 0.5 else -5  # 亮背景用暗文字，暗背景用亮文字
        
        adjusted_color = foreground
        for _ in range(max_attempts):
            adjusted_color = ColorUtils.adjust_lightness(adjusted_color, step)
            if ContrastCalculator.contrast_ratio(adjusted_color, background) >= target_ratio:
                break
        
        return adjusted_color


class SemanticColorDeriver:
    """语义颜色推导器"""
    
    @staticmethod
    def derive_semantic_colors(palette_tokens) -> dict:
        """从基础令牌推导语义颜色"""
        from .theme_schema import ThemeMode, PaletteTokens
        
        # 处理字典类型的palette_tokens
        if isinstance(palette_tokens, dict):
            mode = ThemeMode(palette_tokens.get('mode', 'light'))
            accent = palette_tokens.get('accent', '#0066CC')
            neutral_scale = palette_tokens.get('neutral_scale', [
                "#FFFFFF", "#F5F5F5", "#E0E0E0", "#CCCCCC", "#999999", 
                "#666666", "#404040", "#2D2D2D", "#1E1E1E", "#0F0F0F"
            ])
        else:
            # PaletteTokens 对象
            mode = palette_tokens.mode
            accent = palette_tokens.accent
            neutral_scale = palette_tokens.neutral_scale
        
        if mode == ThemeMode.LIGHT:
            return SemanticColorDeriver._derive_light_colors(accent, neutral_scale)
        else:
            return SemanticColorDeriver._derive_dark_colors(accent, neutral_scale)
    
    @staticmethod
    def _derive_light_colors(accent: str, neutral_scale: List[str]) -> dict:
        """推导亮色主题的语义颜色"""
        return {
            # 基础表面颜色
            'window': neutral_scale[0],      # 最亮 - 窗口背景
            'surface': neutral_scale[0],     # 最亮 - 表面背景
            'surface_alt': neutral_scale[1], # 稍暗 - 交替背景
            
            # 文本颜色
            'text_primary': neutral_scale[8],   # 很暗 - 主要文本
            'text_secondary': neutral_scale[7], # 中暗 - 次要文本
            'text_tertiary': neutral_scale[6],  # 中等 - 第三级文本
            
            # 边框和分割线
            'border': neutral_scale[3],    # 浅灰 - 边框
            'divider': neutral_scale[2],   # 更浅 - 分割线
            
            # 控件颜色
            'control_bg': neutral_scale[1],    # 浅背景
            'control_fg': neutral_scale[8],    # 深前景
            
            # 状态颜色
            'state_hover': ColorUtils.adjust_lightness(neutral_scale[2], -10),
            'state_pressed': ColorUtils.adjust_lightness(neutral_scale[2], -20),
            'state_selected': ColorUtils.adjust_lightness(accent, 20),
            
            # 高亮颜色
            'highlight': accent,
            'highlight_text': ContrastCalculator.adjust_for_contrast(
                neutral_scale[0], accent, 4.5
            )
        }
    
    @staticmethod
    def _derive_dark_colors(accent: str, neutral_scale: List[str]) -> dict:
        """推导暗色主题的语义颜色"""
        return {
            # 基础表面颜色
            'window': neutral_scale[8],      # 很暗 - 窗口背景
            'surface': neutral_scale[8],     # 很暗 - 表面背景
            'surface_alt': neutral_scale[7], # 稍亮 - 交替背景
            
            # 文本颜色
            'text_primary': neutral_scale[0],   # 最亮 - 主要文本
            'text_secondary': neutral_scale[1], # 稍暗 - 次要文本
            'text_tertiary': neutral_scale[2],  # 中等 - 第三级文本
            
            # 边框和分割线
            'border': neutral_scale[6],    # 中灰 - 边框
            'divider': neutral_scale[7],   # 深灰 - 分割线
            
            # 控件颜色
            'control_bg': neutral_scale[7],    # 深背景
            'control_fg': neutral_scale[0],    # 亮前景
            
            # 状态颜色
            'state_hover': ColorUtils.adjust_lightness(neutral_scale[7], 10),
            'state_pressed': ColorUtils.adjust_lightness(neutral_scale[7], 20),
            'state_selected': ColorUtils.adjust_lightness(accent, -20),
            
            # 高亮颜色
            'highlight': ColorUtils.adjust_lightness(accent, 10),
            'highlight_text': ContrastCalculator.adjust_for_contrast(
                neutral_scale[8], accent, 4.5
            )
        }
