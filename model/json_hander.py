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
    def load_json(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)  # 解析后的数据赋值给self.data
            print("JSON解析成功")
        except FileNotFoundError:
            print(f"错误：文件 {self.file_path} 不存在")


    def set_value(self, key: str, value: Any) -> bool:
        """
        设置指定键的值（适用于字典类型的JSON数据）
        
        参数:
            key: 要设置的键
            value: 要设置的值
            
        返回:
            设置成功返回True，否则返回False
        """
        if isinstance(self.data, dict):
            self.data[key] = value
            return True
        print("错误: 只有字典类型的JSON数据才能使用set_value方法")
        return False
    def read_version(self,name):
        version = self.data[f"{name}"]["version"]
        return version
