from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Comic:
    """漫画信息"""
    _id: str
    title: str
    author: str
    description: str = ""
    chineseTeam: str = ""
    created_at: str = ""
    updated_at: str = ""
    finished: bool = False
    totalViews: int = 0
    totalLikes: int = 0
    pagesCount: int = 0  # API返回的字段
    epsCount: int = 0    # API返回的字段
    leaderboardCount: int = 0  # API返回的字段
    viewsCount: int = 0  # API返回的字段
    allowDownload: bool = True
    allowComment: bool = True
    totalComments: int = 0
    likesCount: int = 0
    commentsCount: int = 0
    isFavourite: bool = False
    isLiked: bool = False
    categories: List[str] = None
    tags: List[str] = None
    thumb: Dict[str, Any] = None
    _creator: Dict[str, Any] = None
    
    def __post_init__(self):
        # 处理默认值
        if self.categories is None:
            self.categories = []
        if self.tags is None:
            self.tags = []
        if self.thumb is None:
            self.thumb = {}
        if self._creator is None:
            self._creator = {}


@dataclass
class Episode:
    """章节信息"""
    id: str
    title: str
    order: int
    updated_at: str
    _id: str = ""  # API返回的字段


@dataclass
class Picture:
    """图片信息"""
    id: str
    name: str
    path: str
    fileServer: str
    url: str
    epTitle: str
    media: Dict[str, Any]


@dataclass
class Page:
    """分页信息"""
    total: int
    limit: int
    page: int
    pages: int
    docs: List[Any]


@dataclass
class DownloadInfo:
    """下载信息"""
    title: str
    epTitle: str
    picName: str


@dataclass
class LoginResult:
    """登录结果"""
    token: str