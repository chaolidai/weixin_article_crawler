import json
import time
import requests
from config import get_config
from utils import logger, retry


BASE_URL = "https://mp.weixin.qq.com/cgi-bin/appmsg"


@retry(max_attempts=3, delays=(5, 10, 20))
def fetch_page(cookie, token, fakeid, begin, count=5):
    """请求单页文章列表"""
    params = {
        "action": "list_ex",
        "begin": begin,
        "count": count,
        "fakeid": fakeid,
        "type": "9",
        "query": "",
        "token": token,
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
    }
    headers = {
        "Cookie": cookie,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": "https://mp.weixin.qq.com/",
    }

    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
    data = resp.json()

    base_resp = data.get("base_resp", {})
    if base_resp.get("ret") == -1 or "need login" in str(data).lower():
        raise PermissionError(
            "鉴权失败：Cookie 或 Token 已过期。"
            "请重新登录 mp.weixin.qq.com 获取最新的 Cookie 和 Token，"
            "更新 .env 文件后重新运行。"
        )

    if base_resp.get("ret") != 0:
        logger.warning(f"接口返回异常: {base_resp}")
        return []

    return data.get("app_msg_list", [])


def fetch_article_list(config):
    """拉取文章列表，返回 metadata 列表"""
    cookie = config["cookie"]
    token = config["token"]
    fakeid = config["fakeid"]
    max_articles = config["max_articles"]
    interval = config["request_interval"]

    all_articles = []
    begin = 0
    count = 5

    logger.info(f"开始拉取文章列表，目标数量: {max_articles}")

    while len(all_articles) < max_articles:
        logger.info(f"请求 offset={begin}, 已获取 {len(all_articles)} 篇...")

        articles = fetch_page(cookie, token, fakeid, begin, count)

        if not articles:
            logger.info("没有更多文章，拉取结束")
            break

        for article in articles:
            if len(all_articles) >= max_articles:
                break
            all_articles.append({
                "title": article.get("title", ""),
                "link": article.get("link", ""),
                "publish_time": article.get("create_time", ""),
                "digest": article.get("digest", ""),
                "cover": article.get("cover", ""),
            })

        begin += len(articles)
        time.sleep(interval)

    logger.info(f"文章列表拉取完成，共 {len(all_articles)} 篇")
    return all_articles


def save_metadata(articles, output_path):
    """保存元数据为 JSON"""
    for i, article in enumerate(articles):
        article["id"] = i + 1
        article["local_file"] = ""
        article["image_dir"] = ""

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    logger.info(f"元数据已保存: {output_path}")
