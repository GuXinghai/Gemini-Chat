# domain/model_type.py

from enum import Enum # 引入标准库中的枚举基类，定义一组有名字的常量

class ModelType(str, Enum):
    # —— Gemini 2.5 系列 —— 
    GEMINI_2_5_PRO        = "gemini-2.5-pro"                             # Stable :contentReference[oaicite:25]{index=25}
    GEMINI_2_5_FLASH      = "gemini-2.5-flash"                           # Stable :contentReference[oaicite:26]{index=26}
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"                      # Stable :contentReference[oaicite:27]{index=27}

    GEMINI_2_5_FLASH_PREVIEW               = "gemini-2.5-flash-preview-05-20"              
    GEMINI_2_5_FLASH_LITE_PREVIEW          = "gemini-2.5-flash-lite-06-17"
    GEMINI_2_5_FLASH_PREVIEW_NATIVE_AUDIO  = "gemini-2.5-flash-preview-native-audio-dialog"
    GEMINI_2_5_FLASH_EXP_NATIVE_AUDIO      = "gemini-2.5-flash-exp-native-audio-thinking-dialog"
    GEMINI_2_5_FLASH_PREVIEW_TTS           = "gemini-2.5-flash-preview-tts"
    GEMINI_2_5_PRO_PREVIEW_TTS             = "gemini-2.5-pro-preview-tts"

    GEMINI_2_5_FLASH_LIVE_PREVIEW = "gemini-live-2.5-flash-preview"
    
    # —— Gemini 2.0 系列 —— 
    GEMINI_2_0_FLASH         = "gemini-2.0-flash"                             # Stable :contentReference[oaicite:28]{index=28}
    GEMINI_2_0_FLASH_LITE    = "gemini-2.0-flash-lite"                       # Stable :contentReference[oaicite:29]{index=29}
    GEMINI_2_0_FLASH_EXP     = "gemini-2.0-flash-exp"
    GEMINI_2_0_FLASH_PREVIEW_IMAGE = "gemini-2.0-flash-preview-image-generation"
    GEMINI_2_0_FLASH_LIVE    = "gemini-2.0-flash-live-001"
    
    # —— Gemini 1.5 系列 —— 
    GEMINI_1_5_FLASH      = "gemini-1.5-flash"                             # Stable :contentReference[oaicite:30]{index=30}
    GEMINI_1_5_FLASH_8B   = "gemini-1.5-flash-8b"                          # Stable :contentReference[oaicite:31]{index=31}
    GEMINI_1_5_PRO        = "gemini-1.5-pro"                              # Stable :contentReference[oaicite:32]{index=32}

    # —— Embedding —— 
    GEMINI_EMBEDDING           = "gemini-embedding-001"                       # Stable :contentReference[oaicite:33]{index=33}
    GEMINI_EMBEDDING_EXP        = "gemini-embedding-exp-03-07"

    # —— Imagen 图像生成 —— 
    IMAGEN_4_PREVIEW           = "imagen-4.0-generate-preview-06-06"          # Stable :contentReference[oaicite:34]{index=34}
    IMAGEN_4_ULTRA_PREVIEW     = "imagen-4.0-ultra-generate-preview-06-06"    # Stable :contentReference[oaicite:35]{index=35}
    IMAGEN_3                    = "imagen-3.0-generate-002"                  # Stable :contentReference[oaicite:36]{index=36}

    # —— Veo 视频生成 —— 
    VEO_3_PREVIEW              = "veo-3.0-generate-preview"                   # Stable :contentReference[oaicite:37]{index=37}
    VEO_2                      = "veo-2.0-generate-001"                      # Stable :contentReference[oaicite:38]{index=38}
    
    @classmethod
    def get_all_models(cls):
        """获取所有可用模型"""
        return [model.value for model in cls]
