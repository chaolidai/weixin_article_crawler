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

    rows = []
    for i, article in enumerate(articles):
        result = download_results[i] if i < len(download_results) else {}
        local_file = result.get("local_file", "")

        original_link = article.get("link", "")
        original_cell = (
            f'<a class="original" href="{original_link}" target="_blank">原文</a>'
            if original_link else ""
        )

        pub_str = _format_pub_time(article.get("publish_time", ""))
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
