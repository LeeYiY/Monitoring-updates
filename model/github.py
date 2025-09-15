import base64

import requests
import os
import json
import yaml
from typing import List, Dict, Optional

# ------------------- 配置文件路径（核心：指定YAML配置文件位置） -------------------
REPO_CONFIG_YAML: str = "./repo_configs.yaml"  # 单独的YAML仓库配置文件

# ------------------- 全局配置（所有仓库共用） -------------------
GITHUB_TOKEN: Optional[str] = ""  # GitHub令牌（无则设为None，避免API请求限制）
STATE_FILE: str = "./repo_states/downloaded_assets.json"  # 所有仓库共用的下载状态文件
MAX_VERSIONS: int = 5  # 默认获取最新的5个版本


# ------------------- 工具函数（新增：加载YAML仓库配置） -------------------
def load_repo_configs_from_yaml(config_file: str) -> List[Dict]:
    """
    从YAML文件加载并校验仓库配置
    :param config_file: YAML配置文件路径
    :return: 合法的仓库配置列表
    :raises FileNotFoundError: 配置文件不存在
    :raises yaml.YAMLError: YAML格式错误
    :raises ValueError: 配置缺少必要字段或格式非法
    """
    # 1. 检查配置文件是否存在
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"YAML仓库配置文件不存在：{os.path.abspath(config_file)}")

    # 2. 读取并解析YAML文件
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)  # 使用safe_load避免安全风险
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"YAML配置文件解析失败：{str(e)}")

    # 3. 校验配置根结构（必须包含"repos"字段且为列表）
    if "repos" not in config_data or not isinstance(config_data["repos"], list):
        raise ValueError("YAML配置文件必须包含『repos』字段，且值为仓库配置列表")

    # 4. 校验每个仓库的必要字段（确保配置完整）
    required_fields = ["repo_owner", "repo_name", "base_save_dir", "state_key"]  # 必选字段
    valid_repos = []
    for repo_idx, repo_config in enumerate(config_data["repos"], 1):
        # 检查是否为字典格式
        if not isinstance(repo_config, dict):
            raise ValueError(f"第{repo_idx}个仓库配置格式错误：必须为字典（键值对）")

        # 检查必选字段是否缺失
        missing_fields = [field for field in required_fields if field not in repo_config]
        if missing_fields:
            raise ValueError(f"第{repo_idx}个仓库配置缺失必要字段：{', '.join(missing_fields)}")

        # 检查字段值是否为空
        for field in required_fields:
            if not repo_config[field] or str(repo_config[field]).strip() == "":
                raise ValueError(f"第{repo_idx}个仓库的『{field}』字段不能为空")

        # 添加到合法配置列表
        valid_repos.append(repo_config)

    return valid_repos


# ------------------- 工具函数（复用逻辑：状态管理、API请求、下载） -------------------
def load_all_repos_downloaded_state() -> Dict[str, Dict[int, str]]:
    """加载所有仓库的已下载状态（从JSON状态文件）"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)  # 确保状态文件目录存在
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state_data = json.load(f)
            # 将JSON的字符串Key转为整数（与GitHub Asset ID类型一致）
            return {
                repo_key: {int(asset_id): asset_name for asset_id, asset_name in repo_state.items()}
                for repo_key, repo_state in state_data.items()
            }
    except json.JSONDecodeError:
        # 状态文件损坏时备份并返回空状态
        backup_file = f"{STATE_FILE}.bak"
        os.rename(STATE_FILE, backup_file)
        print(f"⚠️  状态文件损坏，已备份为：{os.path.basename(backup_file)}")
        return {}

def save_all_repos_downloaded_state(state: Dict[str, Dict[int, str]]) -> None:
    """保存所有仓库的已下载状态（到JSON状态文件）"""
    # 将整数Key转为字符串（JSON不支持整数Key）
    state_str_key = {
        repo_key: {str(asset_id): asset_name for asset_id, asset_name in repo_state.items()}
        for repo_key, repo_state in state.items()
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_str_key, f, ensure_ascii=False, indent=2)

def fetch_repo_releases(repo_owner: str, repo_name: str, max_versions: int = MAX_VERSIONS) -> List[Dict]:
    """
    获取仓库的Releases（包含版本信息和附件）
    :param repo_owner: 仓库所有者
    :param repo_name: 仓库名称
    :param max_versions: 最多获取的版本数量，默认为全局配置的MAX_VERSIONS
    :return: Release列表
    """
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    releases = []
    page = 1
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"

    while len(releases) < max_versions:
        try:
            response = requests.get(
                api_url,
                headers=headers,
                params={"page": page, "per_page": min(100, max_versions - len(releases))},  # 每页最多获取所需剩余数量
                timeout=30
            )
            response.raise_for_status()  # 触发HTTP错误（如403限流、404仓库不存在）
        except requests.exceptions.RequestException as e:
            raise Exception(f"GitHub API请求失败：{str(e)}")

        current_releases = response.json()
        if not current_releases:
            break  # 无更多Releases时终止分页
        
        # 添加当前页的Releases，但不超过max_versions
        remaining_slots = max_versions - len(releases)
        releases.extend(current_releases[:remaining_slots])
        page += 1

    return releases

def sanitize_version(version: str) -> str:
    """清理版本号中的非法字符，确保可以作为目录名"""
    invalid_chars = '/\\:*?"<>|'
    for char in invalid_chars:
        version = version.replace(char, '-')
    return version

def download_asset(asset: Dict, save_dir: str) -> bool:
    """下载单个Release附件，返回是否成功"""
    asset_id = asset["id"]
    asset_name = asset["name"]
    download_url = asset["browser_download_url"]
    asset_size_mb = asset["size"] / (1024 * 1024)  # 转换为MB
    save_path = os.path.join(save_dir, asset_name)

    # 检查本地是否已存在完整文件（避免重复下载）
    if os.path.exists(save_path):
        local_size_mb = os.path.getsize(save_path) / (1024 * 1024)
        if abs(local_size_mb - asset_size_mb) < 0.01:  # 误差小于0.01MB视为完整
            print(f"  ✅ 已存在：{asset_name}（{asset_size_mb:.2f}MB）")
            return True

    # 流式下载（支持大文件，避免内存占用过高）
    print(f"  📥 下载中：{asset_name}（{asset_size_mb:.2f}MB）")
    try:
        with requests.get(
                download_url,
                headers={"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {},
                stream=True,
                timeout=60
        ) as resp:
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                total_size = int(resp.headers.get("content-length", 0))
                downloaded_size = 0
                for chunk in resp.iter_content(chunk_size=8192):  # 8KB分片写入
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        # 显示下载进度（仅当能获取总大小时）
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(f"\r  进度：{progress:.1f}%", end="")
        print(f"\n  ✅ 下载完成：{asset_name}")
        return True
    except Exception as e:
        print(f"\n  ❌ 下载失败：{asset_name} - {str(e)}")
        # 清理未下载完成的文件
        if os.path.exists(save_path) and os.path.getsize(save_path) < asset["size"]:
            os.remove(save_path)
        return False


# ------------------- 核心逻辑：单仓库处理 -------------------
def process_single_repo(repo_config: Dict, all_states: Dict[str, Dict[int, str]], max_versions: int = MAX_VERSIONS) -> Dict[str, Dict[int, str]]:
    """处理单个仓库的增量下载，返回更新后的全局状态"""
    # 提取当前仓库配置
    repo_owner = repo_config["repo_owner"]
    repo_name = repo_config["repo_name"]
    base_save_dir = repo_config["base_save_dir"]
    state_key = repo_config["state_key"]
    # 最终保存目录：基础目录/仓库名/版本号（如./Releases/dnSpy/v6.2.0）
    repo_root_dir = os.path.join(base_save_dir, repo_name)

    # 打印仓库处理信息
    print(f"\n" + "=" * 70)
    print(f"📦 开始处理仓库：{repo_owner}/{repo_name}")
    print(f"  - 仓库根目录：{os.path.abspath(repo_root_dir)}")
    print(f"  - 状态文件：{os.path.abspath(STATE_FILE)}")
    print(f"  - 仅获取最新的 {max_versions} 个版本")
    print("=" * 70)

    # 1. 初始化仓库根目录
    os.makedirs(repo_root_dir, exist_ok=True)

    # 2. 加载当前仓库的已下载状态
    repo_state = all_states.get(state_key, {})
    print(f"  ℹ️  已下载文件数量：{len(repo_state)} 个")

    try:
        # 3. 获取仓库最新的Releases
        releases = fetch_repo_releases(repo_owner, repo_name, max_versions)
        if not releases:
            print(f"  ⚠️  未获取到任何Releases（可能仓库无Release或权限不足）")
            return all_states
        print(f"  ℹ️  获取到的Releases数量：{len(releases)} 个")

        # 4. 筛选未下载的附件（基于状态文件中的Asset ID）
        undownloaded_assets = []
        for release in releases:
            release_version = sanitize_version(release["tag_name"])  # 清理版本号
            for asset in release["assets"]:
                if asset["id"] not in repo_state:
                    asset["version"] = release_version  # 给附件绑定版本信息
                    undownloaded_assets.append(asset)

        if not undownloaded_assets:
            print(f"  🎉 无新文件需要更新，所有附件均已下载")
            return all_states
        print(f"  🔍 发现未下载文件：{len(undownloaded_assets)} 个")

        # 5. 下载未下载的附件并更新状态
        success_count = 0
        for asset in undownloaded_assets:
            # 为当前版本创建单独目录
            version_dir = os.path.join(repo_root_dir, asset["version"])
            os.makedirs(version_dir, exist_ok=True)

            # 下载附件并记录状态
            if download_asset(asset, version_dir):
                repo_state[asset["id"]] = asset["name"]
                success_count += 1

        # 6. 更新全局状态
        all_states[state_key] = repo_state

        # 7. 打印处理结果
        print(f"\n  📊 仓库处理完成！")
        print(f"  - 本次成功下载：{success_count} 个文件")
        print(f"  - 累计已下载：{len(repo_state)} 个文件")

    except Exception as e:
        print(f"  ❌ 仓库处理失败：{str(e)}")

    return all_states


def get_github_readme_content(repo_config: Dict):
    # 1. 构造 GitHub API 请求 URL（获取 README 信息）
    repo_owner = repo_config["repo_owner"]
    repo_name = repo_config["repo_name"]
    base_save_dir = repo_config["base_save_dir"]
    repo_root_dir = os.path.join(base_save_dir, repo_name)
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/readme"

    try:
        # 2. 发送 GET 请求（无需认证，公开仓库可直接访问）
        response = requests.get(api_url)
        # 检查请求是否成功（200 表示成功）
        response.raise_for_status()

        # 3. 解析 JSON 响应，提取 download_url 和 Base64 编码的内容
        readme_info = response.json()
        download_url = readme_info.get("download_url")  # 提取下载链接
        base64_content = readme_info.get("content")  # 提取 Base64 编码的内容

        if not download_url or not base64_content:
            print("Error: 未找到 download_url 或 README 内容")
            return None

        # 4. 解码 Base64 内容（注意去除换行符，Base64 编码不允许多余换行）
        base64_content_clean = base64_content.replace("\n", "")  # 清理编码内容
        decoded_content = base64.b64decode(base64_content_clean).decode("utf-8")  # 解码为 UTF-8 文本
        # （可选）将内容写入本地文件
        with open(f"{repo_root_dir}/ReadMe.md", "w", encoding="utf-8") as f:
            f.write(decoded_content)
        print(f"README.md 已保存到本地：{repo_root_dir}/ReadMe.md")

        return decoded_content

    except requests.exceptions.RequestException as e:
        print(f"请求失败：{e}")
        return None


# ------------------- 主函数：批量处理所有仓库 -------------------
def main():
    print("=" * 70)
    print(f"🚀 多仓库GitHub Releases增量下载工具（YAML配置版）")
    print(f"  - 仅获取最新的 {MAX_VERSIONS} 个版本")
    print("=" * 70)

    try:
        # 1. 加载YAML仓库配置
        REPOS_CONFIG = load_repo_configs_from_yaml(REPO_CONFIG_YAML)
        print(f"ℹ️  从YAML加载配置成功，共 {len(REPOS_CONFIG)} 个仓库")
    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        print(f"❌ 配置加载失败：{str(e)}")
        return

    # 2. 加载全局下载状态
    all_states = load_all_repos_downloaded_state()

    # 3. 遍历所有仓库批量处理
    for repo_idx, repo_config in enumerate(REPOS_CONFIG, 1):
        print(f"\n【{repo_idx}/{len(REPOS_CONFIG)}】")
        all_states = process_single_repo(repo_config, all_states)
        # 每处理完一个仓库保存一次状态，避免意外丢失
        save_all_repos_downloaded_state(all_states)

    # 4. 打印最终结果
    print(f"\n" + "=" * 70)
    print(f"✅ 所有仓库处理完毕！")
    print("=" * 70)


if __name__ == "__main__":
    main()