import json
from typing import Any, Optional, Dict, List

class JSONHandler:
    """JSON文件处理接口类，提供读写JSON文件的各种操作"""
    
    def __init__(self, file_path: str):
        """
        初始化JSON处理器
        
        参数:
            file_path: JSON文件路径
        """
        self.file_path = file_path
        self.data: Optional[Dict[str, Any] | List[Any]] = None
        self.load_json()
    def load_json(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)  # 解析后的数据赋值给self.data
            # print("JSON解析成功")
        except FileNotFoundError:
            print(f"错误：文件 {self.file_path} 不存在")


    def set_version(self, key: str, value: Any) -> bool:
        self.data[key]["version"] = value
        with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        return True
    def read_version(self,name):
        version = self.data[f"{name}"].get("version")
        return version
    
    # 更新URL
    def update_url(self, key: str, url_dict: Dict[str, str]) -> bool:
        if key in self.data:
            self.data[key]["url"] = url_dict
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            return True
        return False
