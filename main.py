import os
import sys
from typing import Optional

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hashlib
import os

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from astrbot.api.message_components import Plain, File

from pica_api.sdk import PicaAPI
from pica_api.types import Comic, Episode, DownloadInfo
from pica_api.utils import (
    select_chapters_by_input, is_valid_comic_id,
    mark_downloaded, filter_downloaded_episodes,
    filter_downloaded_pictures, format_comic_list, format_episode_list
)
from pica_api.zip import batch_create_comic_zips, create_zip_archive


class Main(Star):
    """哔咔漫画下载器插件"""
    
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        # 正确接收AstrBotConfig
        self.config = config if config else AstrBotConfig()
        self.pica_api: Optional[PicaAPI] = None
        self.logged_in = False
        self.current_download_session = None  # 当前下载会话
        
        # 获取插件数据目录
        data_path = get_astrbot_data_path()
        if isinstance(data_path, str):
            import os
            self.plugin_data_path = os.path.join(data_path, "plugin_data", "astrbot_plugin_pica")
            os.makedirs(self.plugin_data_path, exist_ok=True)
        else:
            self.plugin_data_path = data_path / "plugin_data" / "astrbot_plugin_pica"
            self.plugin_data_path.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """插件初始化 - 与TypeScript版本环境变量保持一致"""
        logger.info("哔咔漫画插件初始化中...")
        
        # 直接使用传入的配置对象
        config = self.config
        
        # 设置环境变量，确保与pica_api模块兼容
        account = config.get("account", "")
        password = config.get("password", "")
        proxy = config.get("proxy", "")
        secret_key = config.get("secret_key", "~d}$Q7$eIni=V)9\\RK/P.RM4;9[7|@/CA}b~OW!3?EV`:<>M7pddUBL5n|0/*Cn")
        concurrency = config.get("download_settings", {}).get("concurrency", 5)
        
        # 设置环境变量（对应TypeScript的PICA_*环境变量）
        if account:
            os.environ["PICA_ACCOUNT"] = account
        if password:
            os.environ["PICA_PASSWORD"] = password
        if proxy:
            os.environ["PICA_PROXY"] = proxy
        if secret_key:
            os.environ["PICA_SECRET_KEY"] = secret_key
        if concurrency:
            os.environ["PICA_DL_CONCURRENCY"] = str(concurrency)
        
        # 调试信息
        logger.info(f"配置状态 - 账号: {'已配置' if account else '未配置'}, 密码: {'已配置' if password else '未配置'}")
        
        if not account or not password:
            logger.warning("账号或密码未配置，请在管理面板中配置登录信息")
            logger.info("插件初始化完成，但需要配置登录信息后才能使用完整功能")
            return
        
        # 尝试自动登录
        logger.info("检测到已配置的登录信息，正在自动登录...")
        success = await self.login(account, password)
        if success:
            logger.info("自动登录成功，插件已准备就绪")
        else:
            logger.error("自动登录失败，请在管理面板中检查配置")
    
    async def login(self, account: str, password: str) -> bool:
        """登录哔咔 - 与TypeScript版本保持一致"""
        try:
            if not self.pica_api:
                self.pica_api = PicaAPI()
                
                # 配置已通过环境变量设置，无需重复设置
                logger.info("PicaAPI已初始化，使用环境变量配置")
            
            self.pica_api.login(account, password)
            self.logged_in = True
            logger.info(f"哔咔登录成功: {account}")
            return True
        except Exception as e:
            logger.error(f"哔咔登录失败: {str(e)}")
            return False
    
    def check_login(self) -> bool:
        """检查是否已登录"""
        if not self.logged_in or not self.pica_api:
            return False
        return True
    
    @filter.command("pica_search")
    async def cmd_search(self, event: AstrMessageEvent, keyword: str = ""):
        """搜索漫画
        
        Args:
            keyword: 搜索关键词或漫画ID
        """
        if not self.check_login():
            yield event.plain_result("插件未登录，请在管理面板中配置登录信息")
            return
        
        if not keyword:
            yield event.plain_result("请提供搜索关键词：\n/pica_search <关键词>")
            return
        
        yield event.plain_result(f"正在搜索: {keyword}...")
        
        try:
            # 检查是否为漫画ID
            if is_valid_comic_id(keyword):
                comic = self.pica_api.get_comic_info(keyword)
                result = f"找到漫画：\n标题: {comic.title}\n作者: {comic.author}\nID: {comic._id}\n简介: {comic.description[:100]}..."
                yield event.plain_result(result)
            else:
                # 关键词搜索
                yield event.plain_result(f"正在使用关键词搜索: {keyword}")
                comics = self.pica_api.search_comics_all(keyword)
                yield event.plain_result(f"搜索完成，找到 {len(comics)} 个结果")
                if comics:
                    result = format_comic_list(comics[:10])
                    yield event.plain_result(result)
                else:
                    yield event.plain_result("没有找到相关漫画")
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            yield event.plain_result(f"搜索失败: {str(e)}")
    
    @filter.command("pica_favorites")
    async def cmd_favorites(self, event: AstrMessageEvent, page: int = 1):
        """查看收藏夹
        
        Args:
            page: 页码，默认为1
        """
        if not self.check_login():
            yield event.plain_result("插件未登录，请在管理面板中配置登录信息")
            return
        
        try:
            yield event.plain_result(f"正在获取收藏夹第{page}页...")
            
            if page and str(page).isdigit():
                # 获取指定页
                page_result = self.pica_api.get_favorites(int(page))
                comics = page_result.docs
                total_pages = page_result.pages
            else:
                # 获取所有收藏
                comics = self.pica_api.get_all_favorites()
                total_pages = 1  # 简化处理
            
            if comics:
                comic_list = format_comic_list(comics[:10])
                yield event.plain_result(f"{comic_list}\n\n第{page}页，共{total_pages}页")
            else:
                yield event.plain_result("收藏夹为空")
        except Exception as e:
            logger.error(f"获取收藏夹失败: {str(e)}")
            yield event.plain_result(f"获取收藏夹失败: {str(e)}")
    
    @filter.command("pica_leaderboard")
    async def cmd_leaderboard(self, event: AstrMessageEvent):
        """查看排行榜"""
        if not self.check_login():
            yield event.plain_result("插件未登录，请在管理面板中配置登录信息")
            return
        
        try:
            yield event.plain_result("正在获取排行榜...")
            
            comics = self.pica_api.get_leaderboard()
            if comics:
                result = format_comic_list(comics[:10])
                yield event.plain_result(f"24小时排行榜:\n{result}")
            else:
                yield event.plain_result("排行榜为空")
        except Exception as e:
            logger.error(f"获取排行榜失败: {str(e)}")
            yield event.plain_result(f"获取排行榜失败: {str(e)}")
    
    @filter.command("pica_info")
    async def cmd_info(self, event: AstrMessageEvent, comic_id: str = ""):
        """查看漫画详细信息
        
        Args:
            comic_id: 漫画ID
        """
        if not self.check_login():
            yield event.plain_result("插件未登录，请在管理面板中配置登录信息")
            return
        
        if not comic_id:
            yield event.plain_result("请提供漫画ID：\n/pica_info <漫画ID>")
            return
        
        if not is_valid_comic_id(comic_id):
            yield event.plain_result("无效的漫画ID格式")
            return
        
        try:
            yield event.plain_result("正在获取漫画信息...")
            
            comic = self.pica_api.get_comic_info(comic_id)
            episodes = self.pica_api.get_all_episodes(comic_id)
            
            info = f"""📖 漫画信息
标题: {comic.title}
作者: {comic.author}
分类: {', '.join(comic.categories)}
标签: {', '.join(comic.tags)}
状态: {'已完结' if comic.finished else '连载中'}
总章节数: {len(episodes)}
简介: {comic.description}
ID: {comic._id}"""
            
            yield event.plain_result(info)
        except Exception as e:
            logger.error(f"获取漫画信息失败: {str(e)}")
            yield event.plain_result(f"获取漫画信息失败: {str(e)}")
    
    @filter.command("pica_episodes")
    async def cmd_episodes(self, event: AstrMessageEvent, comic_id: str = ""):
        """查看漫画章节列表
        
        Args:
            comic_id: 漫画ID
        """
        if not self.check_login():
            yield event.plain_result("插件未登录，请在管理面板中配置登录信息")
            return
        
        if not comic_id:
            yield event.plain_result("请提供漫画ID：\n/pica_episodes <漫画ID>")
            return
        
        if not is_valid_comic_id(comic_id):
            yield event.plain_result("无效的漫画ID格式")
            return
        
        try:
            yield event.plain_result("正在获取章节列表...")
            
            episodes = self.pica_api.get_all_episodes(comic_id)
            if episodes:
                result = format_episode_list(episodes[:20])
                yield event.plain_result(result)
            else:
                yield event.plain_result("该漫画没有章节")
        except Exception as e:
            logger.error(f"获取章节列表失败: {str(e)}")
            yield event.plain_result(f"获取章节列表失败: {str(e)}")
    
    @filter.command("pica_download")
    async def cmd_download(self, event: AstrMessageEvent, comic_id: str = "", chapters: str = "all"):
        """下载漫画
        
        Args:
            comic_id: 漫画ID
            chapters: 章节选择，默认为all（全部），支持格式如 "1,3,5-10"
        """
        if not self.check_login():
            yield event.plain_result("插件未登录，请在管理面板中配置登录信息")
            return
        
        if not comic_id:
            yield event.plain_result("请提供漫画ID：\n/pica_download <漫画ID> [章节]")
            return
        
        if not is_valid_comic_id(comic_id):
            yield event.plain_result("无效的漫画ID格式")
            return
        
        # 检查是否有其他下载正在进行
        if self.current_download_session:
            yield event.plain_result(f"⚠️ 当前有下载任务正在进行：{self.current_download_session}")
            return
        
        try:
            # 创建新的下载会话
            import uuid
            session_id = str(uuid.uuid4())[:8]
            self.current_download_session = f"{comic_id}_{session_id}"
            
            # 清理上一次的下载文件
            await self._cleanup_previous_files()
            
            # 获取漫画信息
            yield event.plain_result("正在获取漫画信息...")
            comic = self.pica_api.get_comic_info(comic_id)
            
            # 获取章节列表
            yield event.plain_result("正在获取章节列表...")
            all_episodes = self.pica_api.get_all_episodes(comic_id)
            
            # 过滤已下载的章节
            episodes = filter_downloaded_episodes(all_episodes, comic_id)
            
            if not episodes:
                yield event.plain_result("没有未下载的章节")
                self.current_download_session = None
                return
            
            # 选择要下载的章节
            selected_episodes = select_chapters_by_input(chapters, episodes)
            
            if not selected_episodes:
                yield event.plain_result("没有找到指定的章节")
                self.current_download_session = None
                return
            
            yield event.plain_result(f"开始下载 {comic.title}，共 {len(selected_episodes)} 个章节")
            
            # 下载每个章节（带并发控制）
            for episode in selected_episodes:
                # 直接调用生成器函数，不使用await
                self._download_episode(event, comic, episode)
            
            yield event.plain_result(f"✅ {comic.title} 下载完成")
            
        except Exception as e:
            logger.error(f"下载失败: {str(e)}")
            yield event.plain_result(f"下载失败: {str(e)}")
        finally:
            # 清理下载会话
            self.current_download_session = None
    
    async def _download_episode(self, event: AstrMessageEvent, comic: Comic, episode: Episode):
        """下载单个章节并打包发送"""
        try:
            yield event.plain_result(f"正在下载章节: {episode.title}")
            
            # 获取图片列表
            pictures = self.pica_api.get_pictures_all(comic._id, episode)
            
            # 过滤已下载的图片
            pictures = filter_downloaded_pictures(pictures, comic.title, episode.title)
            
            if not pictures:
                yield event.plain_result(f"章节 {episode.title} 没有未下载的图片")
                mark_downloaded(comic._id, episode.id)
                return
            
            yield event.plain_result(f"章节 {episode.title} 共 {len(pictures)} 张图片")
            
            # 获取下载配置
            download_settings = self.config.get("download_settings", {})
            concurrency = download_settings.get("concurrency", 5)
            timeout = download_settings.get("timeout", 30)
            retry_count = download_settings.get("retry_count", 3)
            
            # 设置下载超时和重试
            self.pica_api.max_retry = retry_count
            
            # 使用并发控制下载图片
            import asyncio
            semaphore = asyncio.Semaphore(concurrency)
            
            async def download_single_picture(picture, index):
                try:
                    info = DownloadInfo(
                        title=comic.title,
                        epTitle=episode.title,
                        picName=picture.name
                    )
                    
                    async with semaphore:
                        self.pica_api.download_image(picture.url, info)
                        return True, index
                except Exception as e:
                    logger.error(f"下载图片失败 {picture.url}: {str(e)}")
                    return False, index
            
            # 创建下载任务
            tasks = [download_single_picture(picture, i) for i, picture in enumerate(pictures)]
            
            # 执行并发下载
            downloaded = 0
            # 将asyncio.as_completed的结果转换为列表，避免异步生成器问题
            completed_tasks = list(asyncio.as_completed(tasks))
            for coro in completed_tasks:
                try:
                    success, index = await coro
                    if success:
                        downloaded += 1
                    
                    # 每下载5张图片或完成时更新进度
                    if (downloaded % 5 == 0) or (downloaded == len(pictures)):
                        progress = f"章节 {episode.title} 下载进度: {downloaded}/{len(pictures)}"
                        yield event.plain_result(progress)
                except Exception as e:
                    logger.error(f"下载任务执行失败: {str(e)}")
                    continue
            
            # 标记章节已下载
            mark_downloaded(comic._id, episode.id)
            yield event.plain_result(f"✅ 章节 {episode.title} 下载完成 ({downloaded}/{len(pictures)})")
            
            # 打包章节为ZIP并发送
            self._pack_and_send_episode(event, comic, episode)
            
        except Exception as e:
            logger.error(f"下载章节失败 {episode.title}: {str(e)}")
            yield event.plain_result(f"❌ 章节 {episode.title} 下载失败: {str(e)}")
            
    async def _pack_and_send_episode(self, event: AstrMessageEvent, comic: Comic, episode: Episode):
        """打包章节为ZIP并发送"""
        try:
            yield event.plain_result(f"正在打包章节: {episode.title}")
            
            # 创建临时目录
            import tempfile
            import shutil
            
            episode_dir = None
            zip_path = None
            
            try:
                # 创建临时目录
                episode_dir = tempfile.mkdtemp(prefix=f"pica_{episode.id}_")
                zip_filename = f"{comic.title}_{episode.title}.zip"
                zip_path = os.path.join(episode_dir, zip_filename)
                
                # 复制章节文件到临时目录
                if isinstance(self.plugin_data_path, str):
                    import os
                    source_dir = os.path.join(self.plugin_data_path, comic.title, episode.title)
                else:
                    source_dir = self.plugin_data_path / comic.title / episode.title
                    
                if os.path.exists(source_dir):
                    temp_episode_dir = os.path.join(episode_dir, episode.title)
                    shutil.copytree(source_dir, temp_episode_dir)
                    
                    # 创建ZIP文件
                    if create_zip_archive(temp_episode_dir, zip_path):
                        # 生成密码（文件MD5后12位）
                        zip_password = self._generate_zip_password(zip_path)
                        
                        # 发送文件
                        if os.path.exists(zip_path):
                            yield event.file_result(File(file=zip_path, name=zip_filename))
                            yield event.plain_result(f"📦 {episode.title} 已打包发送")
                            yield event.plain_result(f"🔐 解压密码: {zip_password}")
                        else:
                            yield event.plain_result(f"❌ 打包失败: 文件不存在")
                    else:
                        yield event.plain_result(f"❌ 打包失败: 创建ZIP失败")
                    
                else:
                    yield event.plain_result(f"❌ 打包失败: 章节目录不存在")
                    
            except Exception as e:
                logger.error(f"打包章节失败: {str(e)}")
                yield event.plain_result(f"❌ 打包失败: {str(e)}")
                
        except Exception as e:
            logger.error(f"打包发送章节失败: {str(e)}")
            yield event.plain_result(f"❌ 打包发送失败: {str(e)}")
            
    async def _cleanup_previous_files(self):
        """清理上一次的下载文件以节省空间"""
        try:
            import os
            import shutil
            
            # 遍历所有漫画目录
            if os.path.exists(self.plugin_data_path):
                for comic_dir in os.listdir(self.plugin_data_path):
                    comic_path = os.path.join(self.plugin_data_path, comic_dir)
                    if os.path.isdir(comic_path):
                        # 删除整个漫画目录
                        shutil.rmtree(comic_path)
                        logger.info(f"已清理上一次下载的漫画: {comic_dir}")
                        
                # 清空done.txt文件
                done_file = os.path.join(self.plugin_data_path, 'done.txt')
                if os.path.exists(done_file):
                    os.remove(done_file)
                    
        except Exception as e:
            logger.error(f"清理文件失败: {str(e)}")
    
    def _generate_zip_password(self, file_path: str) -> str:
        """生成ZIP密码（文件MD5后12位）"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash[-12:]  # 取后12位
        except Exception as e:
            logger.error(f"生成密码失败: {str(e)}")
            return "default123"  # 默认密码
    
    @filter.command("pica_help")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """📚 哔咔漫画下载器帮助
        
基础命令：
/pica_help - 显示此帮助信息
/pica_status - 查看配置和登录状态
        
搜索功能：
/pica_search <关键词> - 搜索漫画
/pica_leaderboard - 查看排行榜
/pica_favorites [页码] - 查看收藏夹
        
信息查看：
/pica_info <漫画ID> - 查看漫画详细信息
/pica_episodes <漫画ID> - 查看漫画章节列表
        
下载功能：
/pica_download <漫画ID> [章节] - 下载漫画
  章节参数: all(全部)，1,3,5-10 等
        
配置说明：
- 插件初始化时会自动使用已配置的账号登录
- 请在管理面板中配置账号密码和其他参数
- 配置项对应TypeScript版本的环境变量：
  * account → PICA_ACCOUNT（账号邮箱）
  * password → PICA_PASSWORD（账号密码）
  * proxy → PICA_PROXY（代理地址）
  * secret_key → PICA_SECRET_KEY（API密钥）
  * concurrency → PICA_DL_CONCURRENCY（下载并发数）
- 下载的文件自动打包为ZIP格式并直接发送
- ZIP文件密码为文件MD5后12位
- 每次下载会自动清理上一次的文件以节省空间
        
数据目录: {self.plugin_data_path}
        
提示：
- 请在管理面板中配置登录信息
- 配置保存后会自动登录
- 下载文件保存在插件数据目录中"""
        
        yield event.plain_result(help_text)
    
    @filter.command("pica_status")
    async def cmd_status(self, event: AstrMessageEvent):
        """查看配置和登录状态"""
        # 使用正确的配置对象
        account = self.config.get("account")
        password = self.config.get("password")
        proxy = self.config.get("proxy")
        secret_key = self.config.get("secret_key")
        
        download_settings = self.config.get("download_settings", {})
        concurrency = download_settings.get("concurrency", 5)
        timeout = download_settings.get("timeout", 30)
        retry_count = download_settings.get("retry_count", 3)
        
        status_text = f"""📊 哔咔漫画插件状态

登录状态: {'✅ 已登录' if self.logged_in else '❌ 未登录'}
账号配置: {'✅ 已配置' if account else '❌ 未配置'}
密码配置: {'✅ 已保存' if password else '❌ 未保存'}
代理配置: {'✅ 已配置' if proxy else '❌ 未配置'}
密钥配置: {'✅ 已配置' if secret_key else '❌ 未配置'}

下载设置:
- 并发数: {concurrency}
- 超时时间: {timeout}秒
- 重试次数: {retry_count}

数据目录: {self.plugin_data_path}

环境变量状态:
- PICA_ACCOUNT: {'已设置' if os.getenv('PICA_ACCOUNT') else '未设置'}
- PICA_PASSWORD: {'已设置' if os.getenv('PICA_PASSWORD') else '未设置'}
- PICA_PROXY: {'已设置' if os.getenv('PICA_PROXY') else '未设置'}
- PICA_SECRET_KEY: {'已设置' if os.getenv('PICA_SECRET_KEY') else '未设置'}

提示：
- 请在管理面板中配置登录信息
- 配置保存后会自动登录
- 下载文件保存在插件数据目录中"""
        
        yield event.plain_result(status_text)
    
    
    async def terminate(self):
        """插件销毁时的清理工作"""
        logger.info("哔咔漫画插件正在关闭...")
