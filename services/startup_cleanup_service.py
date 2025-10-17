"""
启动清理服务
自动清理空的"新聊天"记录
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

# 需要跳过的特殊文件
SKIP_FILES = {'folders.json'}


def is_conversation_file(file_path: Path) -> bool:
    """判断是否为有效的对话文件"""
    return file_path.suffix == '.json' and file_path.name not in SKIP_FILES


def get_chat_history_folders() -> List[Path]:
    """获取聊天历史文件夹路径列表"""
    chat_folders = [
        Path("geminichat/chat_history")
    ]
    project_root = Path(__file__).parent.parent
    return [project_root / folder for folder in chat_folders if (project_root / folder).exists()]

def is_empty_ephemeral_chat(file_path: Path, startup_time: Optional[datetime] = None) -> Tuple[bool, str]:
    """
    检查是否是空的临时会话记录
    
    Args:
        file_path: 文件路径
        startup_time: 应用启动时间，用于避免删除刚创建的会话
        
    Returns:
        (is_empty_ephemeral, reason)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 检查是否为临时会话
        is_ephemeral = data.get('is_ephemeral', False)
        if not is_ephemeral:
            return False, "不是临时会话"
            
        # 检查消息列表
        messages = data.get('messages', [])
        if len(messages) > 0:
            return False, f"存在 {len(messages)} 条消息"
            
        # 检查附件列表
        attachments = data.get('attachments', [])
        if len(attachments) > 0:
            return False, f"存在 {len(attachments)} 个附件"
            
        # 检查创建时间（避免删除刚创建的会话）
        if startup_time:
            try:
                created_at_str = data.get('created_at', '')
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    time_diff = (startup_time - created_at.replace(tzinfo=None)).total_seconds()
                    if abs(time_diff) < 5:  # 5秒内创建的不删除
                        return False, "刚创建的临时会话（启动时间内）"
            except:
                pass  # 时间解析失败，继续检查其他条件
                
        return True, "空的临时会话记录"
        
    except Exception as e:
        return False, f"检查失败: {e}"

def auto_clean_empty_new_chats(startup_time: Optional[datetime] = None, silent: bool = True) -> int:
    """
    清理空的旧版"新聊天"记录（已弃用，因为旧版本数据已清理）
    
    Args:
        startup_time: 应用启动时间（未使用）
        silent: 是否静默执行（未使用）
        
    Returns:
        0 (始终返回0，因为旧版本数据已被清理)
    """
    return 0

def auto_clean_empty_chats(startup_time: Optional[datetime] = None, silent: bool = True) -> int:
    """
    自动清理空的临时会话和旧的"新聊天"记录
    
    Args:
        startup_time: 应用启动时间
        silent: 是否静默执行
        
    Returns:
        删除的文件数量
    """
    deleted_count = 0
    folders = get_chat_history_folders()
    
    if not folders:
        if not silent:
            print("没有找到聊天历史文件夹")
        return 0
        
    empty_chats = []
    
    for folder in folders:
        json_files = list(folder.glob("*.json"))
        for file_path in json_files:
            # 使用通用过滤函数跳过特殊文件
            if not is_conversation_file(file_path):
                continue
                
            # 检查是否为空的临时会话
            is_empty_ephemeral, reason = is_empty_ephemeral_chat(file_path, startup_time)
            if is_empty_ephemeral:
                empty_chats.append((file_path, f"空的临时会话: {reason}"))
    
    # 删除找到的空聊天文件
    for file_path, reason in empty_chats:
        try:
            file_path.unlink()
            deleted_count += 1
            if not silent:
                print(f"已删除: {file_path.name} ({reason})")
        except Exception as e:
            if not silent:
                print(f"删除失败 {file_path.name}: {e}")
    
    return deleted_count

def perform_startup_cleanup(silent: bool = True) -> int:
    """
    执行启动清理（包括临时会话和旧的新聊天）
    
    Args:
        silent: 是否静默模式
        
    Returns:
        删除的文件数量
    """
    try:
        startup_time = datetime.now()
        return auto_clean_empty_chats(startup_time, silent)
    except Exception as e:
        if not silent:
            print(f"启动清理失败: {e}")
        return 0
