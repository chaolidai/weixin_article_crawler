import os
from dotenv import load_dotenv

load_dotenv()


def get_config():
    """加载并校验配置，返回配置字典"""
    cookie = os.getenv("WEIXIN_COOKIE", "").strip()
    token = os.getenv("WEIXIN_TOKEN", "").strip()
    fakeid = os.getenv("WEIXIN_FAKEID", "").strip()
    target_name = os.getenv("TARGET_NAME", "").strip()
    max_articles = int(os.getenv("MAX_ARTICLES", "50"))
    request_interval = int(os.getenv("REQUEST_INTERVAL", "12"))
    output_dir = os.getenv("OUTPUT_DIR", "output").strip()

    missing = []
    if not cookie:
        missing.append("WEIXIN_COOKIE")
    if not token:
        missing.append("WEIXIN_TOKEN")
    if not fakeid:
        missing.append("WEIXIN_FAKEID")
    if missing:
        raise ValueError(
            f"缺少必要配置: {', '.join(missing)}。"
            f"请检查 .env 文件，参考 .env.example 填写。"
        )

    return {
        "cookie": cookie,
        "token": token,
        "fakeid": fakeid,
        "target_name": target_name or "weixin_articles",
        "max_articles": max_articles,
        "request_interval": request_interval,
        "output_dir": output_dir,
    }
