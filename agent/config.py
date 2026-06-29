"""
配置文件
从环境变量读取所有配置
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# LLM配置
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4")

# Agent配置 - 高性能模式
MAX_ITERATIONS = int(os.environ.get("MAX_ITERATIONS", "50"))
MAX_FIX_ATTEMPTS = int(os.environ.get("MAX_FIX_ATTEMPTS", "20"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "16000"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.3"))
TIMEOUT_PER_COMMAND = int(os.environ.get("TIMEOUT_PER_COMMAND", "120"))
WORK_DIR = os.environ.get("WORK_DIR", "./work")
CHECKPOINT_INTERVAL = int(os.environ.get("CHECKPOINT_INTERVAL", "5"))

# 工具调用轮数限制 - 大幅提高
MAX_ROUNDS_ANALYZE = int(os.environ.get("MAX_ROUNDS_ANALYZE", "50"))
MAX_ROUNDS_GENERATE = int(os.environ.get("MAX_ROUNDS_GENERATE", "80"))
MAX_ROUNDS_FIX = int(os.environ.get("MAX_ROUNDS_FIX", "50"))

# 请求频率控制
REQUEST_INTERVAL = int(os.environ.get("REQUEST_INTERVAL", "2"))  # 请求间隔（秒）
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))  # 最大重试次数

# GitHub配置
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = os.environ.get("GITHUB_USER", "")
