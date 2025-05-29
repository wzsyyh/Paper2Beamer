#!/usr/bin/env python3
"""
修复 OpenAI 客户端初始化时的 proxies 参数问题
"""
import os
import sys
import logging
import importlib.util
import inspect
from types import FunctionType, MethodType

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def patch_openai_client():
    """
    修补 OpenAI 客户端，移除 proxies 参数
    """
    try:
        # 尝试导入 OpenAI 客户端
        import openai
        from openai import OpenAI
        
        # 获取原始的 __init__ 方法
        original_init = OpenAI.__init__
        
        # 定义新的 __init__ 方法
        def patched_init(self, *args, **kwargs):
            # 移除 proxies 参数（如果存在）
            if 'proxies' in kwargs:
                logging.info("移除了 'proxies' 参数")
                del kwargs['proxies']
            
            # 调用原始的 __init__ 方法
            return original_init(self, *args, **kwargs)
        
        # 替换 __init__ 方法
        OpenAI.__init__ = patched_init
        logging.info("成功修补 OpenAI 客户端")
        
        return True
    except Exception as e:
        logging.error(f"修补 OpenAI 客户端失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def patch_langchain_openai():
    """
    修补 LangChain OpenAI 集成
    """
    try:
        # 尝试导入 LangChain OpenAI
        import langchain_openai
        from langchain_openai.chat_models import ChatOpenAI
        
        # 获取原始的 __init__ 方法
        original_init = ChatOpenAI.__init__
        
        # 定义新的 __init__ 方法
        def patched_init(self, *args, **kwargs):
            # 移除 proxies 参数（如果存在）
            if 'proxies' in kwargs:
                logging.info("从 ChatOpenAI 移除了 'proxies' 参数")
                del kwargs['proxies']
            
            # 调用原始的 __init__ 方法
            return original_init(self, *args, **kwargs)
        
        # 替换 __init__ 方法
        ChatOpenAI.__init__ = patched_init
        logging.info("成功修补 LangChain ChatOpenAI")
        
        return True
    except Exception as e:
        logging.error(f"修补 LangChain ChatOpenAI 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# 当作为脚本运行时，应用补丁
if __name__ == "__main__":
    success1 = patch_openai_client()
    success2 = patch_langchain_openai()
    
    if success1 and success2:
        logging.info("所有补丁都已成功应用")
    else:
        logging.warning("一些补丁未能应用")
    
    sys.exit(0 if (success1 or success2) else 1) 