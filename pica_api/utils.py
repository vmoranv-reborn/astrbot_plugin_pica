import asyncio
import os
import re
import pathlib
from typing import List

from .types import Episode, Picture


def select_chapters_by_input(input_str: str, episodes: List[Episode]) -> List[Episode]:
    """根据输入选择章节"""
    input_str = input_str.strip()
    
    if input_str in ['all', '全部', '所有']:
        return episodes
    
    # 解析输入，支持 "1,3,5-20" 格式
    indices = []
    for part in re.split(r'[,，]', input_str):
        if not part.strip():
            continue
        
        if '-' in part:
            # 处理范围
            start, end = part.split('-')
            try:
                start_idx = int(start.strip())
                end_idx = int(end.strip())
                indices.extend(range(start_idx, end_idx + 1))
            except ValueError:
                continue
        else:
            # 处理单个数字
            try:
                indices.append(int(part.strip()))
            except ValueError:
                continue
    
    # 过滤有效索引并转换为Episode列表
    valid_indices = [i for i in indices if i > 0]
    if not valid_indices:
        return episodes
    
    return [episodes[i-1] for i in valid_indices if i-1 < len(episodes)]


def is_valid_comic_id(comic_id: str) -> bool:
    """检查是否为有效的漫画ID"""
    return bool(re.match(r'^[0-9a-zA-Z]{24}$', comic_id))


def mark_downloaded(comic_id: str, episode_id: str):
    """标记章节已下载"""
    # 使用插件数据目录
    plugin_data_dir = pathlib.Path("data/plugin_data/astrbot_plugin_pica")
    plugin_data_dir.mkdir(parents=True, exist_ok=True)
    
    done_file = plugin_data_dir / 'done.txt'
    with open(done_file, 'a', encoding='utf-8') as f:
        f.write(f"{comic_id}/{episode_id}\n")


def filter_downloaded_episodes(episodes: List[Episode], comic_id: str) -> List[Episode]:
    """过滤已下载的章节"""
    # 使用插件数据目录
    plugin_data_dir = pathlib.Path("data/plugin_data/astrbot_plugin_pica")
    done_file = plugin_data_dir / 'done.txt'
    
    if not done_file.exists():
        return episodes
    
    try:
        with open(done_file, 'r', encoding='utf-8') as f:
            done_content = f.read()
        
        done_episodes = set()
        for line in done_content.splitlines():
            line = line.strip()
            if line:
                done_episodes.add(line)
        
        return [ep for ep in episodes if f"{comic_id}/{ep.id}" not in done_episodes]
    except Exception:
        return episodes


def filter_downloaded_pictures(pictures: List[Picture], title: str, episode_title: str) -> List[Picture]:
    """过滤已下载的图片"""
    # 使用插件数据目录
    episode_dir = pathlib.Path("data/plugin_data/astrbot_plugin_pica") / normalize_name(title) / normalize_name(episode_title)
    
    if not episode_dir.exists():
        return pictures
    
    try:
        existing_files = set(os.listdir(episode_dir))
        return [pic for pic in pictures if pic.name not in existing_files]
    except Exception:
        return pictures


def normalize_name(name: str) -> str:
    """规范化文件名"""
    # 替换Windows不允许的字符
    name = re.sub(r'[\\/]', '／', name)
    name = re.sub(r'[?]', '？', name)
    name = re.sub(r'[|]', '︱', name)
    name = re.sub(r'["]', '＂', name)
    name = re.sub(r'[*]', '＊', name)
    name = re.sub(r'[<]', '＜', name)
    name = re.sub(r'[>]', '＞', name)
    name = re.sub(r'[:]', '-', name)
    
    # 限制长度
    return name.strip()[:85]


def format_comic_list(comics: List, max_items: int = 10) -> str:
    """格式化漫画列表显示"""
    if not comics:
        return "没有找到漫画"
    
    lines = ["找到以下漫画："]
    for i, comic in enumerate(comics[:max_items], 1):
        lines.append(f"{i}. {comic.title} (ID: {comic._id})")
    
    if len(comics) > max_items:
        lines.append(f"... 还有 {len(comics) - max_items} 部漫画")
    
    return "\n".join(lines)


def format_episode_list(episodes: List[Episode], max_items: int = 20) -> str:
    """格式化章节列表显示"""
    if not episodes:
        return "没有找到章节"
    
    lines = [f"共 {len(episodes)} 个章节："]
    for i, episode in enumerate(episodes[:max_items], 1):
        lines.append(f"{i}. {episode.title}")
    
    if len(episodes) > max_items:
        lines.append(f"... 还有 {len(episodes) - max_items} 个章节")
    
    return "\n".join(lines)


async def safe_download_with_retry(pica_api, picture, info, max_retries: int = 3):
    """安全下载图片，带重试机制"""
    for attempt in range(max_retries):
        try:
            return await pica_api.download_image(picture.url, info)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(1)  # 等待1秒后重试


def create_download_progress_bar(total: int, title: str, episode_title: str) -> str:
    """创建下载进度显示"""
    return f"正在下载 {title} - {episode_title} [0/{total}]"


def update_download_progress(current: int, total: int, title: str, episode_title: str) -> str:
    """更新下载进度显示"""
    progress = current / total if total > 0 else 0
    bar_length = 20
    filled_length = int(bar_length * progress)
    bar = '█' * filled_length + ' ' * (bar_length - filled_length)
    
    return f"正在下载 {title} - {episode_title} [{bar}] {current}/{total} ({progress:.1%})"