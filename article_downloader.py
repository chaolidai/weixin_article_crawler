import os
import re
import time
import requests
from bs4 import BeautifulSoup
from utils import logger, sanitize_filename, retry

CONTENT_SELECTOR = "#js_content"
REMOVE_SELECTORS = [
    "script", "style",
    ".rich_media_meta_list",
    ".rich_media_tool",
    ".reward_area",
    ".rich_media_area_extra",
    ".comment_area",
    ".like_comment_wrp",
    ".qr_code_pc_outer",
    ".original_area_primary",
    "#js_pc_qr_code",
]
ALLOWED_TAGS = [
    "p", "div", "span", "section",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "br", "hr",
    "img", "a", "table", "tr", "td", "th", "thead", "tbody",
]
ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ max-width: 680px; margin: 0 auto; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.8; color: #333; }}
  .article-header {{ border-bottom: 2px solid #07c160; padding-bottom: 16px; margin-bottom: 24px; }}
  .article-header h1 {{ font-size: 22px; margin: 0 0 8px 0; }}
  .article-meta {{ color: #999; font-size: 14px; }}
  .article-meta a {{ color: #07c160; text-decoration: none; }}
  .article-meta span {{ margin-right: 16px; }}
  img {{ max-width: 100%; height: auto; }}
  blockquote {{ border-left: 4px solid #ddd; padding-left: 16px; color: #666; margin: 16px 0; }}
  pre, code {{ background: #f5f5f5; border-radius: 4px; }}
  pre {{ padding: 12px; overflow-x: auto; }}
</style>
</head>
<body>
<div class="article-header">
  <h1>{title}</h1>
  <div class="article-meta">
    <span>发布时间: {publish_time}</span><br>
    <span>原文链接: <a href="{original_link}" target="_blank">{original_link}</a></span>
  </div>
</div>
<div class="article-content">
{body}
</div>
</body>
</html>"""


def convert_timestamp(ts):
    """将 Unix 时间戳转为可读日期 (UTC+8)"""
    if not ts:
        return "未知"
    try:
        from datetime import datetime, timezone, timedelta
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        dt = dt + timedelta(hours=8)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


def clean_content(html, article_dir, title):
    """清洗文章 HTML，下载图片到本地，返回清洗后的 body HTML"""
    soup = BeautifulSoup(html, "lxml")

    # 移除不需要的元素
    for selector in REMOVE_SELECTORS:
        for el in soup.select(selector):
            el.decompose()

    # 提取正文
    content = soup.select_one(CONTENT_SELECTOR)
    if not content:
        content = soup.select_one("body") or soup
    else:
        # 移除微信的隐藏样式（visibility: hidden; opacity: 0）
        content.attrs.pop("style", None)

    # 清洗属性，只保留白名单标签
    for el in content.find_all(True):
        if el.name not in ALLOWED_TAGS:
            el.unwrap()
            continue
        allowed_attrs = []
        if el.name == "img":
            allowed_attrs = ["src", "alt", "data-src"]
        elif el.name == "a":
            allowed_attrs = ["href"]
        for attr in list(el.attrs.keys()):
            if attr not in allowed_attrs:
                del el[attr]

    # 下载图片并替换链接
    images_dir = os.path.join(article_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    for i, img in enumerate(content.find_all("img")):
        src = img.get("data-src") or img.get("src")
        if not src:
            continue

        try:
            img_filename = f"img_{i + 1:03d}.{get_image_ext(src)}"
            img_path = os.path.join(images_dir, img_filename)
            download_image(src, img_path)
            img["src"] = f"images/{img_filename}"
            if img.get("data-src"):
                del img["data-src"]
        except Exception as e:
            logger.warning(f"图片下载失败: {src[:80]}... - {e}")
            img["src"] = src

    return str(content)


def get_image_ext(url):
    """从 URL 猜测图片扩展名"""
    url_no_query = url.split("?")[0]
    ext_match = re.search(r"\.(jpg|jpeg|png|gif|webp|bmp|svg)", url_no_query, re.I)
    return ext_match.group(1).lower() if ext_match else "jpg"


@retry(max_attempts=3, delays=(3, 6, 10))
def download_image(url, save_path):
    """下载单张图片"""
    if os.path.exists(save_path):
        return
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://mp.weixin.qq.com/",
    }
    resp = requests.get(url, headers=headers, timeout=30, stream=True)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def build_article_html(title, publish_time_str, original_link, body_html):
    """组装完整文章 HTML"""
    return ARTICLE_TEMPLATE.format(
        title=title,
        publish_time=publish_time_str,
        original_link=original_link,
        body=body_html,
    )


def download_article(article, articles_dir):
    """下载单篇文章，返回 (local_file, image_dir)"""
    pub_ts = convert_timestamp(article.get("publish_time", ""))
    pub_date = pub_ts[:10] if len(pub_ts) >= 10 else "unknown"
    safe_title = sanitize_filename(article["title"])
    filename = f"{pub_date}_{safe_title}.html"

    article_dir = os.path.join(articles_dir, os.path.splitext(filename)[0])
    os.makedirs(article_dir, exist_ok=True)

    logger.info(f"  下载: {article['title'][:40]}...")

    resp = requests.get(article["link"], headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }, timeout=30)
    resp.raise_for_status()

    body_html = clean_content(resp.text, article_dir, article["title"])
    full_html = build_article_html(
        title=article["title"],
        publish_time_str=pub_ts,
        original_link=article["link"],
        body_html=body_html,
    )

    html_path = os.path.join(article_dir, filename)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    local_file = f"articles/{os.path.splitext(filename)[0]}/{filename}"
    image_dir = f"articles/{os.path.splitext(filename)[0]}/images/"
    return local_file, image_dir


def download_all_articles(articles, config):
    """逐篇下载所有文章"""
    output_dir = config["output_dir"]
    target_name = sanitize_filename(config["target_name"])
    articles_dir = os.path.join(output_dir, target_name, "articles")
    os.makedirs(articles_dir, exist_ok=True)

    interval = config["request_interval"]
    results = []

    for i, article in enumerate(articles):
        try:
            local_file, image_dir = download_article(article, articles_dir)
            results.append({
                "local_file": local_file,
                "image_dir": image_dir,
                "success": True,
            })
        except Exception as e:
            logger.error(f"  文章下载失败: {article.get('title', '')[:40]} - {e}")
            results.append({
                "local_file": "",
                "image_dir": "",
                "success": False,
            })

        if i < len(articles) - 1:
            time.sleep(interval)

    logger.info(f"文章下载完成: 成功 {sum(1 for r in results if r['success'])}/{len(results)}")
    return results
