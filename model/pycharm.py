from collections.abc import dict_items
from enum import verify

import requests
import json
from datetime import datetime

from model.download import download_file


def get_pycharm_professional_versions():
    """
    爬取 PyCharm 专业版所有版本及下载地址
    返回格式：列表，每个元素为字典，包含 version, release_date, os_type, download_url
    """
    # 目标接口 URL
    url = "https://data.services.jetbrains.com/products?code=PCP%2CPCC&release.type=release&_=1757503463371"

    try:
        # 发送 GET 请求（模拟浏览器 headers 避免被拦截）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 若请求失败（如 404/500），抛出异常

        # 解析 JSON 数据
        data = response.json()

        # 存储结果的列表
        result = []

        # 遍历数据（只处理 "PyCharm" 产品，且过滤专业版相关版本）
        for product in data:
            if product.get("name") == "PyCharm":
                # 遍历所有版本发布记录
                for release in product.get("releases", []):
                    version = release.get("version")
                    release_date = release.get("date")
                    downloads = release.get("downloads", {})

                    # 跳过无版本号或无下载地址的记录
                    if not version or not downloads:
                        continue

                    # 定义系统类型与下载地址的映射（覆盖所有支持的系统）
                    os_mappings = [
                        ("Linux ARM64", downloads.get("linuxARM64", {}).get("link")),
                        ("Linux", downloads.get("linux", {}).get("link")),
                        ("Windows", downloads.get("windows", {}).get("link")),
                        ("Windows Zip", downloads.get("windowsZip", {}).get("link")),
                        ("Windows ARM64", downloads.get("windowsARM64", {}).get("link")),
                        ("macOS", downloads.get("mac", {}).get("link")),
                        ("macOS M1", downloads.get("macM1", {}).get("link")),
                        ("Windows Zip ARM64", downloads.get("windowsZipARM64", {}).get("link"))
                    ]

                    # 遍历系统映射，添加有效记录
                    for os_type, download_url in os_mappings:
                        if download_url:  # 只保留有有效下载地址的记录
                            result.append({
                                "version": version,
                                "release_date": release_date,
                                "os_type": os_type,
                                "download_url": download_url
                            })

        # 按发布时间倒序排序（最新版本在前）
        result.sort(key=lambda x: datetime.strptime(x["release_date"], "%Y-%m-%d"), reverse=True)
        return result

    except requests.exceptions.RequestException as e:
        print(f"请求失败：{e}")
        return []
    except json.JSONDecodeError:
        print("JSON 解析失败")
        return []


def print_pycharm_versions(versions):
    """格式化输出版本信息"""
    if not versions:
        print("未获取到 PyCharm 专业版版本信息")
        return

    # 按版本分组输出（避免重复版本号多次显示）
    current_version = None

    for item in versions:
        if item["version"] != current_version:
            current_version = item["version"]
            print(f"\n=== 版本：{current_version}（发布时间：{item['release_date']}）===")


        download_file(f"{item['download_url']}",f"./download/Pycharm/{current_version}/")
        print(f"  {item['os_type']}: {item['download_url']}")


if __name__ == "__main__":
    print("正在获取 PyCharm 专业版所有版本及下载地址...")
    pycharm_versions = get_pycharm_professional_versions()
    print_pycharm_versions(pycharm_versions)