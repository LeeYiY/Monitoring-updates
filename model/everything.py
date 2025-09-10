
import random
from lxml import html
import re
import requests
browser_headers_list = [
    # Chrome (Windows)
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "identity",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    },
    # Firefox (macOS)
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7",
        "Accept-Encoding": "identity",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
]
version_option_list = {
    'x86.msi',
    'x64.msi',
    'x86-Setup.exe',
    'x64-Setup.exe',
    'x86.Lite-Setup.exe',
    'x64.Lite-Setup.exe',
    'x86.zip',
    'x64.zip',
    'x64.ARM.exe',
    'x64.ARM64.exe',
}
def getVersion(url):
    headers = random.choice(browser_headers_list)
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    if(response.status_code==200):
        print("✔获取网站信息成功")
        response.encoding = response.apparent_encoding
        tree = html.fromstring(response.text)
        try:
            h2_tag = tree.xpath('//h2[@id="dl"]')
            if h2_tag:
                tag_text = h2_tag[0].text.strip()
                version_pattern = re.compile(r'\d+\.\d+\.\d+\.\d+')
                version_match = version_pattern.search(tag_text)

                return version_match.group()

        except Exception as e:
            return {
                    'status': 'error',
                    'message': f'解析HTML时出错: {str(e)}',
                }
if __name__ == '__main__':
    
    version = getVersion('https://www.voidtools.com/')
    print(version)