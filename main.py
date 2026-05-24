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

    os.makedirs(base_dir, exist_ok=True)
    metadata_path = os.path.join(base_dir, "articles_metadata.json")
    save_metadata(articles, metadata_path)

    # Step 2: 下载文章内容
    logger.info("=" * 50)
    logger.info(f"Step 2/3: 下载 {len(articles)} 篇文章内容...")
    download_results = download_all_articles(articles, config)

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

    success = sum(1 for r in download_results if r["success"])
    logger.info("=" * 50)
    logger.info(f"完成! 成功 {success}/{len(articles)} 篇")
    logger.info(f"离线归档目录: {os.path.abspath(base_dir)}")
    logger.info(f"目录索引: file:///{os.path.abspath(index_path).replace(os.sep, '/')}")

    try:
        import webbrowser
        webbrowser.open(f"file:///{os.path.abspath(index_path).replace(os.sep, '/')}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
