from json_hander import JSONHandler
if __name__ == '__main__':
    handler = JSONHandler('./data/software.json')
    print(handler.file_path)  # 输出: tool_config.json（已绑定路径）
    version = handler.read_version("Everything")
    print(version)    
