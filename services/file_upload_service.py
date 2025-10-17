"""
多模态文件上传服务
支持文档/图片/视频/音频理解，以及URL采集功能
遵循Gemini API规范，提供拖拽/上传/URL采集→即时预览→一键调用→可追溯历史的流畅体验
"""
import os
import re
import io
import mimetypes
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Union
from datetime import datetime
from urllib.parse import urlparse, urljoin
import asyncio
from dataclasses import dataclass, asdict

try:
    import httpx
    from google import genai
    from google.genai import types
except ImportError as e:
    print(f"导入库失败: {e}")
    httpx = None
    genai = None
    types = None

from geminichat.domain.attachment import Attachment, AttachmentType


@dataclass
class UploadLimits:
    """上传限制配置"""
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    max_total_size: int = 200 * 1024 * 1024  # 200MB
    max_file_count: int = 100
    max_request_size: int = 20 * 1024 * 1024  # 20MB (使用File API的阈值)


@dataclass 
class URLInfo:
    """URL信息"""
    url: str
    url_type: str  # 'pdf', 'image', 'video', 'audio', 'youtube', 'html'
    estimated_size: Optional[int] = None
    mime_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ProcessedFile:
    """处理后的文件信息"""
    file_path: str
    original_name: str
    file_size: int
    mime_type: str
    attachment_type: AttachmentType
    gemini_file: Optional[Any] = None  # Gemini File API上传的文件引用
    content_hash: Optional[str] = None
    metadata: Optional[Dict] = None


class FileUploadService:
    """多模态文件上传服务"""
    
    # 支持的MIME类型映射
    SUPPORTED_FORMATS = {
        # 文档
        'application/pdf': AttachmentType.DOCUMENT,
        'text/plain': AttachmentType.DOCUMENT,
        'text/markdown': AttachmentType.DOCUMENT,
        'text/html': AttachmentType.DOCUMENT,
        'application/xml': AttachmentType.DOCUMENT,
        
        # 图片
        'image/png': AttachmentType.IMAGE,
        'image/jpeg': AttachmentType.IMAGE,
        'image/webp': AttachmentType.IMAGE,
        'image/heic': AttachmentType.IMAGE,
        'image/heif': AttachmentType.IMAGE,
        'image/gif': AttachmentType.IMAGE,
        
        # 视频
        'video/mp4': AttachmentType.VIDEO,
        'video/mpeg': AttachmentType.VIDEO,
        'video/mov': AttachmentType.VIDEO,
        'video/avi': AttachmentType.VIDEO,
        'video/x-flv': AttachmentType.VIDEO,
        'video/mpg': AttachmentType.VIDEO,
        'video/webm': AttachmentType.VIDEO,
        'video/wmv': AttachmentType.VIDEO,
        'video/3gpp': AttachmentType.VIDEO,
        
        # 音频
        'audio/wav': AttachmentType.AUDIO,
        'audio/mp3': AttachmentType.AUDIO,
        'audio/aiff': AttachmentType.AUDIO,
        'audio/aac': AttachmentType.AUDIO,
        'audio/ogg': AttachmentType.AUDIO,
        'audio/flac': AttachmentType.AUDIO,
    }
    
    def __init__(self, api_key: Optional[str] = None, upload_limits: Optional[UploadLimits] = None):
        """初始化文件上传服务"""
        self.api_key = api_key
        self.limits = upload_limits or UploadLimits()
        self.client = None
        
        # 初始化Gemini客户端
        if api_key and genai:
            try:
                self.client = genai.Client(api_key=api_key)
                print("Gemini File API客户端初始化成功")
            except Exception as e:
                print(f"Gemini客户端初始化失败: {e}")
                self.client = None
        elif not api_key:
            print("未提供API密钥，将使用模拟模式")
        else:
            print("缺少必要依赖，将使用模拟模式")
    
    def validate_files(self, file_paths: List[str]) -> Tuple[bool, str, List[str]]:
        """
        验证文件列表
        返回: (是否通过验证, 错误信息, 有效文件列表)
        """
        valid_files = []
        total_size = 0
        
        # 检查文件数量
        if len(file_paths) > self.limits.max_file_count:
            return False, f"文件数量超出限制 (最多{self.limits.max_file_count}个)", []
        
        for file_path in file_paths:
            path = Path(file_path)
            
            # 检查文件是否存在
            if not path.exists():
                continue
            
            # 检查是否为文件
            if not path.is_file():
                continue
            
            # 检查文件大小
            file_size = path.stat().st_size
            if file_size > self.limits.max_file_size:
                return False, f"文件 {path.name} 超出大小限制 ({file_size/1024/1024:.1f}MB > {self.limits.max_file_size/1024/1024:.1f}MB)", []
            
            # 检查MIME类型
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type or mime_type not in self.SUPPORTED_FORMATS:
                continue
            
            valid_files.append(file_path)
            total_size += file_size
        
        # 检查总大小
        if total_size > self.limits.max_total_size:
            return False, f"文件总大小超出限制 ({total_size/1024/1024:.1f}MB > {self.limits.max_total_size/1024/1024:.1f}MB)", []
        
        return True, "", valid_files
    
    def analyze_urls(self, urls: List[str]) -> List[URLInfo]:
        """
        分析URL列表，识别类型和预估大小
        """
        url_infos = []
        
        for url in urls:
            url = url.strip()
            if not url:
                continue
            
            # 确保URL有协议前缀
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            try:
                parsed = urlparse(url)
                if not parsed.netloc:
                    continue
                
                url_type = self._detect_url_type(url)
                url_info = URLInfo(
                    url=url,
                    url_type=url_type,
                    title=self._extract_title_from_url(url)
                )
                
                # 尝试获取内容大小和MIME类型
                if httpx:
                    try:
                        head_response = httpx.head(url, timeout=5.0)
                        if head_response.status_code == 200:
                            content_length = head_response.headers.get('content-length')
                            if content_length:
                                url_info.estimated_size = int(content_length)
                            url_info.mime_type = head_response.headers.get('content-type', '').split(';')[0]
                    except:
                        pass
                
                url_infos.append(url_info)
                
            except Exception as e:
                print(f"URL分析失败 {url}: {e}")
                continue
        
        return url_infos
    
    def _detect_url_type(self, url: str) -> str:
        """检测URL类型"""
        url_lower = url.lower()
        
        # YouTube检测
        if 'youtube.com/watch' in url_lower or 'youtu.be/' in url_lower:
            return 'youtube'
        
        # 基于文件扩展名检测
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        if path.endswith(('.pdf',)):
            return 'pdf'
        elif path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
            return 'image'
        elif path.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')):
            return 'video'
        elif path.endswith(('.mp3', '.wav', '.aac', '.ogg', '.flac')):
            return 'audio'
        else:
            return 'html'
    
    def _extract_title_from_url(self, url: str) -> str:
        """从URL提取标题"""
        try:
            parsed = urlparse(url)
            # 简单的标题提取逻辑
            path_parts = parsed.path.strip('/').split('/')
            if path_parts and path_parts[-1]:
                return path_parts[-1]
            return parsed.netloc
        except:
            return url
    
    async def process_files(self, file_paths: List[str]) -> List[ProcessedFile]:
        """
        处理文件列表，上传到Gemini File API或准备内联数据
        """
        processed_files = []
        
        for file_path in file_paths:
            try:
                processed_file = await self._process_single_file(file_path)
                if processed_file:
                    processed_files.append(processed_file)
            except Exception as e:
                print(f"处理文件失败 {file_path}: {e}")
                continue
        
        return processed_files
    
    async def _process_single_file(self, file_path: str) -> Optional[ProcessedFile]:
        """处理单个文件"""
        path = Path(file_path)
        
        if not path.exists() or not path.is_file():
            return None
        
        # 获取文件信息
        file_size = path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(path))
        
        if not mime_type or mime_type not in self.SUPPORTED_FORMATS:
            return None
        
        attachment_type = self.SUPPORTED_FORMATS[mime_type]
        
        # 计算文件哈希
        content_hash = self._calculate_file_hash(file_path)
        
        # 创建处理后的文件对象
        processed_file = ProcessedFile(
            file_path=str(path),
            original_name=path.name,
            file_size=file_size,
            mime_type=mime_type,
            attachment_type=attachment_type,
            content_hash=content_hash
        )
        
        # 决定是否使用File API
        if file_size > self.limits.max_request_size or self.client:
            # 使用File API上传
            if self.client:
                try:
                    uploaded_file = await self._upload_to_file_api(file_path, mime_type)
                    processed_file.gemini_file = uploaded_file
                    print(f"文件已上传到File API: {path.name}")
                except Exception as e:
                    print(f"File API上传失败 {path.name}: {e}")
            else:
                print(f"文件过大但无API客户端: {path.name}")
        
        return processed_file
    
    async def _upload_to_file_api(self, file_path: str, mime_type: str):
        """上传文件到Gemini File API"""
        if not self.client:
            raise ValueError("Gemini客户端未初始化")
        
        # 确保client不为None（类型检查）
        client = self.client
        assert client is not None
        
        # 在异步函数中运行同步的上传操作
        loop = asyncio.get_event_loop()
        uploaded_file = await loop.run_in_executor(
            None,
            lambda: client.files.upload(
                file=file_path,
                config={"mime_type": mime_type}
            )
        )
        
        return uploaded_file
    
    async def process_urls(self, urls: List[str]) -> List[ProcessedFile]:
        """处理URL列表，下载并处理内容"""
        processed_files = []
        
        for url in urls:
            try:
                url = url.strip()
                if not url:
                    continue
                
                processed_file = await self._process_single_url(url)
                if processed_file:
                    processed_files.append(processed_file)
            except Exception as e:
                print(f"处理URL失败 {url}: {e}")
                continue
        
        return processed_files
    
    async def _process_single_url(self, url: str) -> Optional[ProcessedFile]:
        """处理单个URL"""
        if not httpx:
            print("httpx库未安装，无法处理URL")
            return None
        
        # 确保URL有协议前缀
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        url_type = self._detect_url_type(url)
        
        # 对于YouTube视频，直接创建文件引用
        if url_type == 'youtube':
            return await self._process_youtube_url(url)
        
        # 对于其他URL，下载内容
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                content = response.content
                mime_type = response.headers.get('content-type', '').split(';')[0]
                
                if not mime_type or mime_type not in self.SUPPORTED_FORMATS:
                    # 尝试根据URL推测MIME类型
                    mime_type, _ = mimetypes.guess_type(url)
                    if not mime_type or mime_type not in self.SUPPORTED_FORMATS:
                        return None
                
                attachment_type = self.SUPPORTED_FORMATS[mime_type]
                
                # 计算内容哈希
                content_hash = hashlib.md5(content).hexdigest()
                
                # 创建临时文件
                temp_file = await self._create_temp_file(content, url, mime_type)
                
                processed_file = ProcessedFile(
                    file_path=temp_file,
                    original_name=self._extract_filename_from_url(url),
                    file_size=len(content),
                    mime_type=mime_type,
                    attachment_type=attachment_type,
                    content_hash=content_hash,
                    metadata={'source_url': url}
                )
                
                # 如果内容较大，上传到File API
                if len(content) > self.limits.max_request_size and self.client:
                    try:
                        uploaded_file = await self._upload_content_to_file_api(content, mime_type)
                        processed_file.gemini_file = uploaded_file
                    except Exception as e:
                        print(f"URL内容File API上传失败: {e}")
                
                return processed_file
                
        except Exception as e:
            print(f"下载URL内容失败 {url}: {e}")
            return None
    
    async def _process_youtube_url(self, url: str) -> ProcessedFile:
        """处理YouTube URL"""
        return ProcessedFile(
            file_path=url,
            original_name=f"YouTube视频_{datetime.now().strftime('%H%M%S')}",
            file_size=0,  # YouTube视频大小未知
            mime_type="video/youtube",
            attachment_type=AttachmentType.VIDEO,
            content_hash=hashlib.md5(url.encode()).hexdigest(),
            metadata={'source_url': url, 'is_youtube': True}
        )
    
    async def _upload_content_to_file_api(self, content: bytes, mime_type: str):
        """上传内容到Gemini File API"""
        if not self.client:
            raise ValueError("Gemini客户端未初始化")
        
        # 确保client不为None（类型检查）
        client = self.client
        assert client is not None
        
        content_io = io.BytesIO(content)
        
        loop = asyncio.get_event_loop()
        uploaded_file = await loop.run_in_executor(
            None,
            lambda: client.files.upload(
                file=content_io,
                config={"mime_type": mime_type}
            )
        )
        
        return uploaded_file
    
    async def _create_temp_file(self, content: bytes, url: str, mime_type: str) -> str:
        """创建临时文件"""
        temp_dir = Path("./temp")  # 使用相对路径
        temp_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        filename = self._extract_filename_from_url(url)
        if not filename or '.' not in filename:
            ext = mimetypes.guess_extension(mime_type) or '.tmp'
            filename = f"url_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        
        temp_path = temp_dir / filename
        
        # 写入内容
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, temp_path.write_bytes, content)
        
        return str(temp_path)
    
    def _extract_filename_from_url(self, url: str) -> str:
        """从URL提取文件名"""
        try:
            parsed = urlparse(url)
            path = parsed.path
            if path and '/' in path:
                filename = path.split('/')[-1]
                if filename and '.' in filename:
                    return filename
        except:
            pass
        
        return f"url_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件MD5哈希"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def create_gemini_parts(self, processed_files: List[ProcessedFile]) -> List[Any]:
        """为Gemini API创建内容部分"""
        if not types:
            return []
        
        parts = []
        
        for processed_file in processed_files:
            try:
                if processed_file.gemini_file:
                    # 使用File API引用
                    parts.append(processed_file.gemini_file)
                elif processed_file.metadata and processed_file.metadata.get('is_youtube'):
                    # YouTube URL
                    parts.append(
                        types.Part(
                            file_data=types.FileData(file_uri=processed_file.file_path)
                        )
                    )
                else:
                    # 内联数据
                    with open(processed_file.file_path, 'rb') as f:
                        content = f.read()
                    
                    parts.append(
                        types.Part.from_bytes(
                            data=content,
                            mime_type=processed_file.mime_type
                        )
                    )
            except Exception as e:
                print(f"创建Gemini部分失败 {processed_file.original_name}: {e}")
                continue
        
        return parts





def get_file_upload_service(api_key: Optional[str] = None) -> FileUploadService:
    """获取文件上传服务实例"""
    if not api_key:
        raise ValueError("需要提供 API 密钥")
    if not genai or not httpx:
        raise ImportError("需要安装 google.generativeai 和 httpx 包")
    return FileUploadService(api_key)


def parse_urls_from_text(text: str) -> List[str]:
    """从文本中解析URL列表"""
    if not text.strip():
        return []
    
    urls = []
    
    # 按换行符分割
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 按空格、逗号、中文逗号分割
        parts = re.split(r'[,，\s]+', line)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 检查是否包含URL模式
            if re.match(r'^https?://', part) or '.' in part:
                urls.append(part)
    
    return urls
