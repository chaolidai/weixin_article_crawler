# 微信公众号文章抓取工具 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 UA 伪装方案抓取指定微信公众号"银河系漫游客"最新 50 篇文章，按发布时间排序并生成离线 HTML 归档。

**Architecture:** 纯 Python 脚本，分 4 个模块——配置加载、文章列表获取、文章内容下载清洗、索引生成，由 main.py 编排串联。使用 requests + BeautifulSoup 进行 HTTP 请求和 HTML 清洗。

**Tech Stack:** Python 3.10+, requests, beautifulsoup4, python-dotenv

**Spec:** `docs/2026-05-22-weixin-article-crawler-design.md`

---

## File Structure

```
weixin_article_crawler/
├── config.py              # 配置加载（从 .env 读取）
├── article_fetcher.py     # 文章列表获取（调用 appmsg 接口）
├── article_downloader.py  # 文章内容下载与清洗
├── index_builder.py       # 目录索引生成（index.html）
├── main.py                # 编排入口
├── .env.example           # 配置模板（供用户参考）
├── requirements.txt       # 依赖声明
└── utils.py               # 通用工具（日志、文件名清理、重试）
```

---

### Task 1: 项目基础设施

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `utils.py`

- [ ] **Step 1: 创建 requirements.txt**

```
requests>=2.31.0
beautifulsoup4>=4.12.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: 创建 .env.example 模板**

```
WEIXIN_COOKIE=your_cookie_here
WEIXIN_TOKEN=your_token_here
WEIXIN_FAKEID=your_fakeid_here
TARGET_NAME=银河系漫游客
MAX_ARTICLES=50
REQUEST_INTERVAL=12
OUTPUT_DIR=output
```

- [ ] **Step 3: 创建 utils.py 通用工具**

```python
import re
import time
import logging
from functools import wraps

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def sanitize_filename(name, max_len=80):
    """将文章标题转为安全文件名，去除非法字符"""
    # 去除 Windows/Mac/Linux 非法文件名字符
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # 压缩空白
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
```

- [ ] **Step 4: 安装依赖验证**

```bash
pip install -r requirements.txt
```

---

### Task 2: 配置加载模块 config.py

**Files:**
- Create: `config.py`

- [ ] **Step 1: 创建 config.py**

```python
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

    # 必填项校验
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
```

- [ ] **Step 2: 验证配置加载**

```bash
python -c "from config import get_config; print('config module OK')"
```

---

### Task 3: 文章列表获取 article_fetcher.py

**Files:**
- Create: `article_fetcher.py`

- [ ] **Step 1: 创建 article_fetcher.py**

```python
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

    # 检查鉴权错误
    if data.get("base_resp", {}).get("ret") == -1 or "need login" in str(data).lower():
        raise PermissionError(
            "鉴权失败：Cookie 或 Token 已过期。"
            "请重新登录 mp.weixin.qq.com 获取最新的 Cookie 和 Token，"
            "更新 .env 文件后重新运行。"
        )

    if data.get("base_resp", {}).get("ret") != 0:
        logger.warning(f"接口返回异常: {data.get('base_resp', {})}")
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
    # 添加序号和本地文件路径
    for i, article in enumerate(articles):
        article["id"] = i + 1
        article["local_file"] = ""
        article["image_dir"] = ""

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    logger.info(f"元数据已保存: {output_path}")
```

---

### Task 4: 文章内容下载与清洗 article_downloader.py

**Files:**
- Create: `article_downloader.py`

- [ ] **Step 1: 创建 article_downloader.py**

```python
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from config import get_config
from utils import logger, sanitize_filename, retry

# 微信文章正文容器 ID
CONTENT_SELECTOR = "#js_content"
# 需要移除的元素选择器
REMOVE_SELECTORS = [
    "script", "style",
    ".rich_media_meta_list",        # 顶部元信息栏
    ".rich_media_tool",             # 工具栏
    ".reward_area",                 # 赞赏区
    ".rich_media_area_extra",       # 底部推荐
    ".comment_area",                # 评论区
    ".like_comment_wrp",
    ".qr_code_pc_outer",            # 二维码
    ".original_area_primary",
    "#js_pc_qr_code",
    ".rich_media_area_primary ~ *", # 正文之后的所有元素
]
# 允许的标签白名单
ALLOWED_TAGS = [
    "p", "div", "span", "section",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "br", "hr",
    "img", "a", "table", "tr", "td", "th", "thead", "tbody",
]
# HTML 模板
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
    """将 Unix 时间戳转为可读日期"""
    if not ts:
        return "未知"
    try:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        # 微信时间戳为 UTC+8
        from datetime import timedelta
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

    # 清洗属性，只保留白名单标签
    for el in content.find_all(True):
        if el.name not in ALLOWED_TAGS:
            el.unwrap()
            continue
        # 只保留 img 的 src 和 a 的 href
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
            img_filename = f"img_{i+1:03d}.{get_image_ext(src)}"
            img_path = os.path.join(images_dir, img_filename)
            download_image(src, img_path)
            img["src"] = f"images/{img_filename}"
            if img.get("data-src"):
                del img["data-src"]
        except Exception as e:
            logger.warning(f"图片下载失败: {src[:80]}... - {e}")
            img["src"] = src  # fallback 保留原始链接

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


def download_article(article, articles_dir, index):
    """下载单篇文章，返回 (local_file, image_dir)"""
    # 构建文件名
    pub_ts = convert_timestamp(article.get("publish_time", ""))
    pub_date = pub_ts[:10] if len(pub_ts) >= 10 else "unknown"
    safe_title = sanitize_filename(article["title"])
    filename = f"{pub_date}_{safe_title}.html"

    # 每篇文章的子目录
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

    return filename, article_dir


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
            filename, article_dir = download_article(article, articles_dir, i)
            results.append({
                "local_file": f"articles/{os.path.splitext(filename)[0]}/{filename}",
                "image_dir": f"articles/{os.path.splitext(filename)[0]}/images/",
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
```

---

### Task 5: 索引生成 index_builder.py

**Files:**
- Create: `index_builder.py`

- [ ] **Step 1: 创建 index_builder.py**

```python
import os
from datetime import datetime
from utils import logger, sanitize_filename

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{target_name} - 文章归档</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; background: #f8f9fa; }}
  .header {{ text-align: center; padding: 30px 0; border-bottom: 3px solid #07c160; margin-bottom: 24px; }}
  .header h1 {{ font-size: 24px; color: #07c160; margin-bottom: 8px; }}
  .header .stats {{ color: #999; font-size: 14px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  th, td {{ padding: 12px 16px; text-align: left; }}
  th {{ background: #07c160; color: #fff; font-weight: 500; font-size: 14px; }}
  td {{ border-bottom: 1px solid #eee; font-size: 14px; }}
  tr:hover td {{ background: #f0fff4; }}
  .col-id {{ width: 50px; text-align: center; }}
  .col-time {{ width: 160px; white-space: nowrap; }}
  .col-title {{ }}
  .col-link {{ width: 80px; text-align: center; }}
  a {{ color: #07c160; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  a.original {{ color: #999; font-size: 12px; }}
  .error {{ color: #e74c3c; }}
  @media (max-width: 640px) {{
    .col-time {{ width: auto; }}
    .col-link {{ width: auto; }}
    th, td {{ padding: 8px 10px; font-size: 13px; }}
  }}
</style>
</head>
<body>
<div class="header">
  <h1>{target_name}</h1>
  <div class="stats">共 {total} 篇文章 | 抓取时间: {fetch_time}</div>
</div>
<table>
<thead>
  <tr>
    <th class="col-id">#</th>
    <th class="col-time">发布时间</th>
    <th class="col-title">文章标题</th>
    <th class="col-link">原文链接</th>
  </tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</body>
</html>"""


def build_index(articles, download_results, config):
    """生成 index.html"""
    target_name = config["target_name"]
    output_dir = config["output_dir"]
    safe_name = sanitize_filename(target_name)
    base_dir = os.path.join(output_dir, safe_name)

    os.makedirs(base_dir, exist_ok=True)

    # 过滤下载成功的文章
    rows = []
    for i, article in enumerate(articles):
        result = download_results[i] if i < len(download_results) else {}
        local_file = result.get("local_file", "")
        link_cell = ""

        if local_file:
            # 本地文件链接
            local_path = os.path.join(base_dir, local_file).replace("\\", "/")
            link_cell = f'<a href="{local_file}">阅读</a>'

        original_link = article.get("link", "")
        original_cell = (
            f'<a class="original" href="{original_link}" target="_blank">原文</a>'
            if original_link else ""
        )

        pub_ts = article.get("publish_time", "")
        pub_str = _format_pub_time(pub_ts)

        title = article.get("title", "(无标题)")
        if local_file:
            title_cell = f'<a href="{local_file}">{title}</a>'
        else:
            title_cell = f'<span class="error">{title}</span> (下载失败)'

        rows.append(
            f'<tr>'
            f'<td class="col-id">{i + 1}</td>'
            f'<td class="col-time">{pub_str}</td>'
            f'<td class="col-title">{title_cell}</td>'
            f'<td class="col-link">{original_cell}</td>'
            f'</tr>'
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = INDEX_TEMPLATE.format(
        target_name=target_name,
        total=len(articles),
        fetch_time=now,
        rows="\n".join(rows),
    )

    index_path = os.path.join(base_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"索引已生成: {index_path}")
    return index_path


def _format_pub_time(ts):
    """格式化发布时间"""
    if not ts:
        return "未知"
    try:
        from datetime import datetime, timezone, timedelta
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        dt = dt + timedelta(hours=8)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)
```

---

### Task 6: 编排入口 main.py

**Files:**
- Create: `main.py`

- [ ] **Step 1: 创建 main.py**

```python
import os
import json
import sys
from config import get_config
from article_fetcher import fetch_article_list, save_metadata
from article_downloader import download_all_articles
from index_builder import build_index
from utils import logger, sanitize_filename


def main():
    try:
        config = get_config()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    target_name = config["target_name"]
    output_dir = config["output_dir"]
    safe_name = sanitize_filename(target_name)
    base_dir = os.path.join(output_dir, safe_name)

    logger.info(f"目标公众号: {target_name}")
    logger.info(f"输出目录: {base_dir}")

    # Step 1: 拉取文章列表
    logger.info("=" * 50)
    logger.info("Step 1/3: 拉取文章列表...")
    articles = fetch_article_list(config)

    if not articles:
        logger.error("未获取到任何文章，请检查 Fakeid/Token/Cookie 是否正确。")
        sys.exit(1)

    # 保存元数据
    os.makedirs(base_dir, exist_ok=True)
    metadata_path = os.path.join(base_dir, "articles_metadata.json")
    save_metadata(articles, metadata_path)

    # Step 2: 下载文章内容
    logger.info("=" * 50)
    logger.info(f"Step 2/3: 下载 {len(articles)} 篇文章内容...")
    download_results = download_all_articles(articles, config)

    # 更新元数据中的本地路径
    for i, result in enumerate(download_results):
        if i < len(articles):
            articles[i]["local_file"] = result["local_file"]
            articles[i]["image_dir"] = result["image_dir"]

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    # Step 3: 生成索引
    logger.info("=" * 50)
    logger.info("Step 3/3: 生成索引页...")
    index_path = build_index(articles, download_results, config)

    # 完成
    success = sum(1 for r in download_results if r["success"])
    logger.info("=" * 50)
    logger.info(f"完成! 成功 {success}/{len(articles)} 篇")
    logger.info(f"离线归档目录: {os.path.abspath(base_dir)}")
    logger.info(f"目录索引: file:///{os.path.abspath(index_path).replace(os.sep, '/')}")

    # 尝试自动打开索引页
    try:
        import webbrowser
        webbrowser.open(f"file:///{os.path.abspath(index_path).replace(os.sep, '/')}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证整体流程**

```bash
python main.py
```

期望：按顺序执行 Step 1/2/3，输出目录包含 index.html、articles_metadata.json、articles/、images/。

---

### Task 7: 端到端验证

- [ ] **Step 1: 检查输出文件完整性**

确认 `output/银河系漫游客/` 目录下：
- `index.html` 存在，浏览器可正常打开
- `articles_metadata.json` 存在，JSON 格式正确
- `articles/` 目录下有对应数量的 HTML 文件
- 每个 HTML 文件可独立打开，图片正常显示

- [ ] **Step 2: 验证边界情况处理**

- 删除 `.env` 中某个必填项，运行应提示缺少配置
- 填入错误的 Token，运行应提示鉴权失败
- 检查 index.html 的排序是否为发布时间倒序
