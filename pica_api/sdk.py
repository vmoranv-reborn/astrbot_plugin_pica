import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional, Any
import requests
import urllib3
from urllib.parse import urlencode

from .types import Comic, Episode, Picture, Page, DownloadInfo, LoginResult

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PicaAPI:
    """哔咔漫画API客户端 - 基于src-python成功实现"""
    
    def __init__(self, account: str = "", password: str = "", proxy: str = ""):
        self.account = account
        self.password = password
        self.proxy = proxy
        self.token: Optional[str] = None
        self.max_retry = 3
        self.secret_key = "~d}$Q7$eIni=V)9\\RK/P.RM4;9[7|@/CA}b~OW!3?EV`:<>M7pddUBL5n|0/*Cn"
        self.base_url = "https://picaapi.picacomic.com/"
        
        # 创建HTTP会话 - 基于src-python的成功实现
        self.session = requests.Session()
        self.session.verify = False
        
        # 请求头模板 - 基于src-python的成功实现
        self.headers = {
            "api-key": "C69BAF41DA5ABD1FFEDC6D2FEA56B",
            "accept": "application/vnd.picacomic.com.v1+json",
            "app-channel": "2",
            "nonce": "b1ab87b4800d4d4590a11701b8551afa",
            "app-version": "2.2.1.2.3.3",
            "app-uuid": "defaultUuid",
            "app-platform": "android",
            "app-build-version": "45",
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "okhttp/3.8.1",
            "image-quality": "original"
        }
        
        # 设置代理
        if self.proxy:
            self.session.proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
    
    def _generate_signature(self, url: str, timestamp: str, method: str) -> str:
        """生成请求签名 - 基于src-python的成功实现"""
        # 移除base URL部分
        url = url.replace(self.base_url, "")
        # 构建签名字符串
        raw = f"{url}{timestamp}{self.headers['nonce']}{method}{self.headers['api-key']}"
        # 生成HMAC-SHA256签名
        hc = hmac.new(self.secret_key.encode(), digestmod=hashlib.sha256)
        hc.update(raw.lower().encode())
        return hc.hexdigest()
    
    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求 - 基于src-python的成功实现"""
        # 生成时间戳和签名 - 关键差异：使用str(int(time.time()))
        timestamp = str(int(time.time()))
        signature = self._generate_signature(url, timestamp, method.upper())
        
        # 设置请求头
        headers = self.headers.copy()
        headers['time'] = timestamp
        headers['signature'] = signature
        
        if self.token:
            headers['authorization'] = self.token
        
        # 设置代理
        proxies = None
        if self.proxy:
            proxies = {'http': self.proxy, 'https': self.proxy}
        
        print(f"请求URL: {url}")
        print(f"请求方法: {method}")
        print(f"请求头: {headers}")
        print(f"请求体: {kwargs.get('json', kwargs.get('data', ''))}")
        
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                proxies=proxies,
                verify=False,
                timeout=30,
                **kwargs
            )
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                # 直接使用response.text，然后解析JSON - 关键差异
                response_text = response.text
                print(f"响应文本: {response_text}")
                
                try:
                    result = json.loads(response_text)
                    return result
                except json.JSONDecodeError as e:
                    print(f"JSON解析失败: {e}")
                    return {"success": True, "data": response_text}
            else:
                error_text = response.text
                print(f"请求失败: {response.status_code} - {error_text}")
                raise Exception(f"HTTP {response.status_code}: {error_text}")
                
        except requests.RequestException as e:
            print(f"网络请求错误: {e}")
            raise Exception(f"网络请求失败: {e}")
        except Exception as e:
            print(f"请求处理错误: {e}")
            raise Exception(f"请求处理失败: {e}")
    
    def login(self, account: str = "", password: str = "") -> LoginResult:
        """用户登录 - 基于src-python的成功实现"""
        if not account:
            account = self.account
        if not password:
            password = self.password
            
        if not account or not password:
            raise ValueError("账号和密码不能为空")
        
        url = f"{self.base_url}auth/sign-in"
        data = {
            "email": account,
            "password": password
        }
        
        try:
            response_text = self._make_request("POST", url, json=data)
            
            # 检查响应格式
            if isinstance(response_text, str):
                result = json.loads(response_text)
            else:
                result = response_text
            
            print(f"登录响应: {result}")
            
            if result.get("code") == 200 and "data" in result and "token" in result["data"]:
                self.token = result["data"]["token"]
                print("登录成功，获取到token")
                return LoginResult(token=result["data"]["token"])
            else:
                print(f"登录失败: {result}")
                raise Exception(f"登录失败: {result}")
                
        except Exception as e:
            print(f"登录异常: {e}")
            raise Exception(f"登录失败: {e}")
    
    def search_comics(self, keyword: str, page: int = 1, sort: str = "dd") -> Page:
        """搜索漫画"""
        url = f"{self.base_url}comics/advanced-search?page={page}"
        data = {
            "keyword": keyword,
            "sort": sort
        }
        
        result = self._make_request("POST", url, json=data)
        
        print(f"搜索结果: {result}")
        
        if result.get("code") == 200 and "data" in result:
            # 检查data的结构
            data_section = result["data"]
            print(f"数据结构: {type(data_section)}, 内容: {data_section}")
            
            # 处理不同的数据结构
            if isinstance(data_section, dict) and "comics" in data_section:
                comics_data = data_section["comics"]
            elif isinstance(data_section, dict) and "docs" in data_section:
                comics_data = data_section["docs"]
            elif isinstance(data_section, list):
                comics_data = data_section
            else:
                print(f"未知的数据结构: {type(data_section)}")
                return Page(total=0, limit=40, page=page, pages=0, docs=[])
            
            print(f"漫画数据: {comics_data}")
            
            # 处理漫画数据，确保所有必需字段都有值
            processed_comics = []
            for comic_data in comics_data:
                # 确保comic_data是字典
                if not isinstance(comic_data, dict):
                    print(f"跳过非字典数据: {comic_data}")
                    continue
                
                # 使用setdefault的安全方式
                if "categories" not in comic_data:
                    comic_data["categories"] = []
                if "tags" not in comic_data:
                    comic_data["tags"] = []
                if "thumb" not in comic_data:
                    comic_data["thumb"] = {}
                if "_creator" not in comic_data:
                    comic_data["_creator"] = {}
                
                try:
                    processed_comics.append(Comic(**comic_data))
                except Exception as e:
                    print(f"创建Comic对象失败: {e}, 数据: {comic_data}")
                    continue
            
            # 计算分页信息
            total_pages = data_section.get("pages", 1) if isinstance(data_section, dict) else 1
            total_items = data_section.get("total", len(comics_data)) if isinstance(data_section, dict) else len(comics_data)
            
            return Page(
                total=total_items,
                limit=40,
                page=page,
                pages=total_pages,
                docs=processed_comics
            )
        else:
            print(f"搜索失败: {result}")
            return Page(total=0, limit=40, page=page, pages=0, docs=[])
    
    def search_comics_all(self, keyword: str) -> List[Comic]:
        """搜索所有漫画"""
        if not keyword:
            return []
        
        comics = []
        first_page = self.search_comics(keyword, 1)
        if not first_page or not first_page.docs:
            return comics
        
        comics.extend(first_page.docs)
        
        # 获取剩余页面的漫画
        for page in range(2, first_page.pages + 1):
            page_data = self.search_comics(keyword, page)
            if page_data and page_data.docs:
                comics.extend(page_data.docs)
        
        return comics
    
    def get_comic_info(self, comic_id: str) -> Comic:
        """获取漫画详细信息"""
        url = f"{self.base_url}comics/{comic_id}"
        
        result = self._make_request("GET", url)
        
        if result.get("code") == 200 and "data" in result:
            comic_data = result["data"]["comic"]
            # 确保所有必需字段都有值
            comic_data.setdefault("categories", [])
            comic_data.setdefault("tags", [])
            comic_data.setdefault("thumb", {})
            comic_data.setdefault("_creator", {})
            return Comic(**comic_data)
        else:
            raise Exception(f"获取漫画信息失败: {result}")
    
    def get_episodes(self, comic_id: str, page: int = 1) -> Page:
        """获取漫画章节列表"""
        url = f"{self.base_url}comics/{comic_id}/eps?page={page}"
        
        result = self._make_request("GET", url)
        
        if result.get("code") == 200 and "data" in result:
            eps_data = result["data"]["eps"]
            return Page(
                total=eps_data.get("total", 0),
                limit=40,
                page=page,
                pages=eps_data.get("pages", 0),
                docs=[Episode(**ep) for ep in eps_data.get("docs", [])]
            )
        else:
            return Page(total=0, limit=40, page=page, pages=0, docs=[])
    
    def get_all_episodes(self, comic_id: str) -> List[Episode]:
        """获取漫画所有章节"""
        first_page = self.get_episodes(comic_id, 1)
        if not first_page or not first_page.docs:
            return []
        
        episodes = first_page.docs
        total_pages = first_page.pages
        
        # 获取剩余页面的章节
        for page in range(2, total_pages + 1):
            page_data = self.get_episodes(comic_id, page)
            if page_data and page_data.docs:
                episodes.extend(page_data.docs)
        
        # 按顺序排序
        episodes.sort(key=lambda x: x.order)
        return episodes
    
    def get_pictures(self, comic_id: str, episode_id: str, page: int = 1) -> Page:
        """获取章节图片列表"""
        url = f"{self.base_url}comics/{comic_id}/order/{episode_id}/pages?page={page}"
        
        result = self._make_request("GET", url)
        
        if result.get("code") == 200 and "data" in result:
            pages_data = result["data"]["pages"]
            pictures = []
            for doc in pages_data.get("docs", []):
                media = doc.get("media", {})
                picture = Picture(
                    id=doc.get("id", ""),
                    name=media.get("originalName", ""),
                    path=media.get("path", ""),
                    fileServer=media.get("fileServer", ""),
                    url=f"{media.get('fileServer', '')}/static/{media.get('path', '')}",
                    epTitle="",  # 将在调用方设置
                    media=media
                )
                pictures.append(picture)
            
            return Page(
                total=pages_data.get("total", 0),
                limit=40,
                page=page,
                pages=pages_data.get("pages", 0),
                docs=pictures
            )
        else:
            return Page(total=0, limit=40, page=page, pages=0, docs=[])
    
    def get_all_pictures(self, comic_id: str, episode: Episode) -> List[Picture]:
        """获取章节所有图片"""
        first_page = self.get_pictures(comic_id, episode.id, 1)
        if not first_page or not first_page.docs:
            return []
        
        pictures = first_page.docs
        total_pages = first_page.pages
        
        # 获取剩余页面的图片
        for page in range(2, total_pages + 1):
            page_data = self.get_pictures(comic_id, episode.id, page)
            if page_data and page_data.docs:
                pictures.extend(page_data.docs)
        
        # 处理图片URL和信息
        for i, pic in enumerate(pictures):
            pic.epTitle = episode.title
            # 生成文件名
            ext = pic.name.split('.')[-1] if '.' in pic.name else 'jpg'
            pic.name = f"{i+1:04d}.{ext}"
        
        return pictures
    
    def get_favorites(self, page: int = 1, sort: str = "dd") -> Page:
        """获取收藏夹"""
        url = f"{self.base_url}users/favourite?page={page}&s={sort}"
        
        result = self._make_request("GET", url)
        
        if result.get("code") == 200 and "data" in result:
            comics_data = result["data"]["comics"]
            # 处理漫画数据，确保所有必需字段都有值
            processed_comics = []
            for comic_data in comics_data:
                comic_data.setdefault("categories", [])
                comic_data.setdefault("tags", [])
                comic_data.setdefault("thumb", {})
                comic_data.setdefault("_creator", {})
                processed_comics.append(Comic(**comic_data))
            
            return Page(
                total=len(comics_data),
                limit=40,
                page=page,
                pages=1,  # 简化处理
                docs=processed_comics
            )
        else:
            return Page(total=0, limit=40, page=page, pages=0, docs=[])
    
    def get_all_favorites(self) -> List[Comic]:
        """获取所有收藏"""
        first_page = self.get_favorites(1)
        if not first_page or not first_page.docs:
            return []
        
        comics = first_page.docs
        total_pages = first_page.pages
        
        # 获取剩余页面的收藏
        for page in range(2, total_pages + 1):
            page_data = self.get_favorites(page)
            if page_data and page_data.docs:
                comics.extend(page_data.docs)
        
        return comics
    
    def get_leaderboard(self) -> List[Comic]:
        """获取排行榜"""
        url = f"{self.base_url}comics/leaderboard?tt=H24&ct=VC"
        
        result = self._make_request("GET", url)
        
        if result.get("code") == 200 and "data" in result:
            # 处理漫画数据，确保所有必需字段都有值
            processed_comics = []
            for comic_data in result["data"]["comics"]:
                comic_data.setdefault("categories", [])
                comic_data.setdefault("tags", [])
                comic_data.setdefault("thumb", {})
                comic_data.setdefault("_creator", {})
                processed_comics.append(Comic(**comic_data))
            return processed_comics
        else:
            return []
    
    def download_image(self, url: str, info: DownloadInfo) -> str:
        """下载图片 - 基于src-python的成功实现"""
        try:
            # 处理重定向和HTTPS问题
            if url.startswith("https://"):
                # 哔咔的某些文件服务器安全证书不可用，改为HTTP
                url = url.replace("https://", "http://", 1)
            
            # 设置请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://picacomic.com/"
            }
            
            # 设置代理
            proxies = None
            if self.proxy:
                proxies = {'http': self.proxy, 'https': self.proxy}
            
            print(f"下载图片: {url}")
            
            response = self.session.get(
                url, 
                headers=headers, 
                proxies=proxies,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                # 确保目录存在
                import os
                import pathlib
                download_dir = pathlib.Path('data/plugin_data/astrbot_plugin_pica') / self._normalize_name(info.title) / self._normalize_name(info.epTitle)
                download_dir.mkdir(parents=True, exist_ok=True)
                
                # 保存文件
                file_path = download_dir / info.picName
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"图片下载成功: {file_path}")
                return str(file_path)
            elif response.status_code in [301, 302, 303, 307, 308]:
                # 处理重定向
                location = response.headers.get('location', '')
                if location:
                    print(f"重定向到: {location}")
                    return self.download_image(location, info)
                else:
                    print(f"重定向失败，状态码: {response.status_code}")
                    raise Exception(f"重定向失败: {response.status_code}")
            else:
                print(f"图片下载失败，状态码: {response.status_code}")
                raise Exception(f"下载失败: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"图片下载异常: {e}")
            raise Exception(f"下载图片失败: {e}")
    
    def _normalize_name(self, name: str) -> str:
        """规范化文件名"""
        import re
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
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()