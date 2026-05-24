import re
import time
import logging
from functools import wraps

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def sanitize_filename(name, max_len=80):
    """将文章标题转为安全文件名，去除非法字符"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    if len(name) > max_len:
        name = name[:max_len]
    return name


def retry(max_attempts=3, delays=(5, 10, 20)):
    """重试装饰器，支持递增延迟"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        delay = delays[min(attempt, len(delays) - 1)]
                        logger.warning(f"第 {attempt+1} 次尝试失败: {e}, {delay}s 后重试...")
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
