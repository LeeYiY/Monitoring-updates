import re
import os
import sys
import random
import time
import requests
from lxml import html
from pathlib import Path
ROOT_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if str(ROOT_PATH) not in sys.path:
    sys.path.append(str(ROOT_PATH))
from typing import Dict, Optional, Union
from config import browser_headers_list, everything_version_option_list
from json_hander import JSONHandler
from download import download_file
# 常量定义
SOFTWARE_NAME = "Everything"
SOFTWARE_JSON_PATH = ROOT_PATH / "software.json"
BASE_DOWNLOAD_URL = "https://www.voidtools.com/"
VERSION_PATTERN = re.compile(r'\d+\.\d+\.\d+\.\d+')


def get_version(url: str) -> Union[str, Dict[str, str]]:
    """
    从指定URL获取软件版本信息并检查更新

    Args:
        url: 要检查的软件官网URL

    Returns:
        如果成功获取版本号则返回版本字符串，否则返回错误信息字典
    """
    headers = random.choice(browser_headers_list)

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 抛出HTTP错误状态码异常

        print("-" * 50)
        print("🎉获取网站信息成功")

        response.encoding = response.apparent_encoding
        tree = html.fromstring(response.text)

        # 提取版本信息
        h2_tag = tree.xpath('//h2[@id="dl"]')
        if not h2_tag:
            return {'status': 'error', 'message': '未找到版本信息标签'}

        tag_text = h2_tag[0].text.strip()
        version_match = VERSION_PATTERN.search(tag_text)

        if not version_match:
            return {'status': 'error', 'message': '未找到版本号'}

        current_version = version_match.group()
        json_handler = JSONHandler(str(SOFTWARE_JSON_PATH))
        stored_version = json_handler.read_version(SOFTWARE_NAME)

        print("-" * 50)

        # 检查是否有更新
        if current_version == stored_version:
            print(f"😒无更新,当前版本：{stored_version}")
        else:
            # 更新版本信息
            json_handler.set_version(SOFTWARE_NAME, current_version, "version")
            json_handler.set_version(
                SOFTWARE_NAME,
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                "updateTime"
            )
            print(f"🎉检查到更新,{stored_version}  -->  {current_version}")

            # 更新下载链接
            download_urls = get_download_url(current_version)
            json_handler.update_url(SOFTWARE_NAME, download_urls)
            print("更新下载链接成功")

        return current_version

    except requests.exceptions.RequestException as e:
        return {'status': 'error', 'message': f'网络请求错误: {str(e)}'}
    except Exception as e:
        return {'status': 'error', 'message': f'解析HTML时出错: {str(e)}'}


def get_download_url(version: str) -> Dict[str, str]:
    """
    生成不同版本的下载链接

    Args:
        version: 软件版本号

    Returns:
        包含不同版本下载链接的字典
    """
    download_urls = {}
    download_path = ROOT_PATH / "download" / SOFTWARE_NAME / version

    for option in everything_version_option_list:
        key = option.replace(".", "_").replace("-", "_")
        download_url = f"{BASE_DOWNLOAD_URL}Everything-{version}.{option}"
        download_urls[key] = download_url

        print(download_url)
        download_file(download_url, str(download_path))

    return download_urls


if __name__ == '__main__':
    url = "https://www.voidtools.com/"
    get_version(url)
