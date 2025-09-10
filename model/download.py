import os
import requests
from tqdm import tqdm
from urllib.parse import urlparse


def download_file(url, save_dir=None, filename=None, chunk_size=1024 * 1024, timeout=10):
    """
    下载文件并显示进度条，优化了路径处理逻辑

    参数:
        url (str): 要下载的文件URL
        save_dir (str, optional): 保存文件的目录，默认为当前目录
        filename (str, optional): 保存的文件名，默认为从URL提取
        chunk_size (int, optional): 下载块大小，默认为1MB
        timeout (int, optional): 连接超时时间，默认为10秒

    返回:
        str: 下载成功返回保存的文件路径，失败返回None
    """
    try:
        # 从URL提取文件名
        parsed_url = urlparse(url)
        default_filename = os.path.basename(parsed_url.path)
        if not default_filename:  # 如果URL以/结尾，没有文件名
            default_filename = "downloaded_file"

        # 确定最终文件名
        final_filename = filename if filename else default_filename

        # 确定保存目录
        if save_dir:
            # 标准化目录路径
            save_dir = os.path.normpath(save_dir)
            # 确保目录存在
            os.makedirs(save_dir, exist_ok=True)
        else:
            # 使用当前工作目录
            save_dir = os.getcwd()

        # 构建完整文件路径
        save_path = os.path.join(save_dir, final_filename)
        save_path = os.path.normpath(save_path)  # 确保路径格式正确

        # 检查文件是否已存在及大小
        resume_byte_pos = 0
        if os.path.exists(save_path):
            resume_byte_pos = os.path.getsize(save_path)
            print(f"发现已存在文件，尝试从 {resume_byte_pos} 字节处继续下载...")

        # 设置请求头，支持断点续传
        headers = {}
        if resume_byte_pos > 0:
            headers['Range'] = f'bytes={resume_byte_pos}-'

        # 发送请求
        response = requests.get(url, headers=headers, stream=True, timeout=timeout)
        response.raise_for_status()  # 检查请求是否成功

        # 获取文件总大小
        total_size = int(response.headers.get('content-length', 0)) + resume_byte_pos

        # 显示友好的文件大小
        def format_size(size_bytes):
            """将字节大小转换为人类可读的格式"""
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} PB"

        print(f"文件总大小: {format_size(total_size)}")
        print(f"保存路径: {save_path}")

        # 打开文件，以追加模式写入
        mode = 'ab' if resume_byte_pos > 0 else 'wb'
        with open(save_path, mode) as file, tqdm(
                desc=final_filename,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
                initial=resume_byte_pos,
                ascii=True,
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        ) as progress_bar:

            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # 过滤掉保持连接的空块
                    file.write(chunk)
                    progress_bar.update(len(chunk))

        print(f"文件下载完成，已保存至: {save_path}")
        return save_path

    except requests.exceptions.RequestException as e:
        print(f"下载请求错误: {str(e)}")
    except Exception as e:
        print(f"下载过程中发生错误: {str(e)}")

    return None
