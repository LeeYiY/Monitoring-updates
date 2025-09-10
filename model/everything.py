
import re
import os
import sys
import random
import time

import requests
from lxml import html
from json_hander import JSONHandler
from download import download_file
# 添加项目根目录到sys.path
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_path not in sys.path:
    sys.path.append(root_path)
from config import browser_headers_list, everything_version_option_list
def getVersion(url):
    headers = random.choice(browser_headers_list)
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    if(response.status_code==200):
        print("-" * 50)
        print("🎉获取网站信息成功")
        response.encoding = response.apparent_encoding
        tree = html.fromstring(response.text)
        try:
            h2_tag = tree.xpath('//h2[@id="dl"]')
            if h2_tag:
                tag_text = h2_tag[0].text.strip()
                version_pattern = re.compile(r'\d+\.\d+\.\d+\.\d+')
                version_match = version_pattern.search(tag_text)
                hander = JSONHandler(f"{root_path}/software.json")
                version = hander.read_version("Everything")
                print("-" * 50)
                if version==version_match.group():
                    print(f"😒无更新,当前版本：{version}")
                else:
                    hander.set_version("Everything",version_match.group(),"version")
                    # hander.set_version("Everything",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),"updateTime")
                    print(f"🎉检查到更新,{version}  -->  {version_match.group()}")
                    # 检查到更新才修改链接
                    download_urls = get_download_url(version_match.group())
                    hander.update_url("Everything",download_urls)
                    print("更新下载链接成功")
                return version_match.group()

        except Exception as e:
            return {
                    'status': 'error',
                    'message': f'解析HTML时出错: {str(e)}',
                }
        

def get_download_url(version):
    base_url = "https://www.voidtools.com/"
    download_urls = {}
    for option in everything_version_option_list:
        key = option.replace(".", "_").replace("-", "_")
        download_urls[key] = f"{base_url}Everything-{version}.{option}"
        print(download_urls[key])
        download_file(download_urls[key], f"{root_path}/download/")
    return download_urls

if __name__ == '__main__':
    url = "https://www.voidtools.com/"
    getVersion(url)