import zipfile
import os
from typing import List


def create_zip_archive(source_dir: str, output_path: str) -> bool:
    """创建ZIP压缩包"""
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
        return True
    except Exception as e:
        print(f"创建压缩包失败: {e}")
        return False


def batch_create_comic_zips(comics_root: str, output_root: str) -> List[str]:
    """批量创建漫画ZIP压缩包"""
    created_zips = []
    
    if not os.path.exists(comics_root):
        print("没有发现已下载的漫画")
        return created_zips
    
    comics = [d for d in os.listdir(comics_root) 
              if os.path.isdir(os.path.join(comics_root, d))]
    
    if not comics:
        print("没有发现已下载的漫画")
        return created_zips
    
    print(f"{len(comics)}本漫画等待打包: {', '.join(comics)}")
    
    # 创建输出目录
    os.makedirs(output_root, exist_ok=True)
    
    for comic in comics:
        comic_root = os.path.join(comics_root, comic)
        episodes = [d for d in os.listdir(comic_root) 
                   if os.path.isdir(os.path.join(comic_root, d))]
        
        comic_output_dir = os.path.join(output_root, comic)
        os.makedirs(comic_output_dir, exist_ok=True)
        
        for episode in episodes:
            episode_dir = os.path.join(comic_root, episode)
            zip_path = os.path.join(comic_output_dir, f"{episode}.zip")
            
            if create_zip_archive(episode_dir, zip_path):
                created_zips.append(zip_path)
                print(f"✓ {comic} - {episode} 打包完成")
            else:
                print(f"✗ {comic} - {episode} 打包失败")
    
    print(f"打包完成，共创建 {len(created_zips)} 个压缩包")
    return created_zips


def main():
    """主函数"""
    comics_root = os.path.join(os.getcwd(), 'comics')
    output_root = os.path.join(os.getcwd(), 'comics-zip')
    
    batch_create_comic_zips(comics_root, output_root)


if __name__ == "__main__":
    main()