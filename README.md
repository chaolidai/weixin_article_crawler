# 微信公众号文章爬虫 / WeChat Article Crawler

自动抓取微信公众号全部文章，下载 HTML 内容和图片到本地，生成可离线浏览的索引页。

Crawl all articles from a WeChat Official Account, download HTML content and images locally, and generate a browsable offline index page.

## 功能 / Features

- 通过微信公众平台后端 API 抓取文章列表
- 下载每篇文章的完整 HTML 并清洗排版
- 自动下载文章中的图片到本地
- 生成美观的索引页，支持按发布时间浏览
- 可配置请求间隔，避免触发反爬
- 失败自动重试（带退避策略）
- 完全离线归档，不依赖任何外部资源

## 输出结构 / Output Structure

```
output/{公众号名称}/
├── index.html                # 索引页（浏览器打开即可浏览）
├── articles_metadata.json    # 文章元数据
└── articles/
    └── {日期}_{标题}/
        ├── {日期}_{标题}.html  # 离线文章页面
        └── images/
            ├── img_001.jpg
            └── ...
```

## 快速开始 / Quick Start

### 1. 安装依赖 / Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. 获取凭证 / Get Credentials

首先在浏览器中登录[微信公众平台](https://mp.weixin.qq.com)，然后按以下步骤分别获取三个参数。

#### 2.1 获取 Cookie 和 Token

这两个参数来自同一个 API 请求，可以一起获取：

**① 打开开发者工具**

按 `F12` 打开浏览器开发者工具，切换到 **Network**（网络）标签页。

**② 触发请求**

在微信公众平台后台左侧菜单点击「素材管理」→「已发表内容」（或直接刷新已发表文章列表页面），此时 Network 面板会出现大量请求。

**③ 找到目标请求**

在 Network 面板的搜索过滤框中输入 `appmsg`，会过滤出一个名为 `appmsg?action=list_ex&...` 的请求，点击它。

**④ 复制 Cookie**

右侧面板切换到 **Headers** 标签 → 找到 **Request Headers** 部分 → 找到 `Cookie` 那一行，右键点击、全选、复制。这就是 `WEIXIN_COOKIE` 的值（很长一串字符串）。

**⑤ 复制 Token**

仍在 Headers 面板中 → 往下滚到 **Query String Parameters** 部分 → 找到 `token` 字段，复制它的值（一长串数字）。这就是 `WEIXIN_TOKEN`。

> 也可以直接看请求 URL，例如：
> `https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_ex&...&token=123456789&...`
> URL 中 `token=` 后面的数字就是 Token。

---

#### 2.2 获取 Fakeid

Fakeid 是目标公众号的内部 ID，需要从公众号文章页面获取：

**① 打开目标公众号的文章**

在浏览器中打开你想要抓取的公众号的**任意一篇文章**（手机分享链接或电脑端打开均可）。

**② 查看页面源代码**

按 `F12` 打开开发者工具 → 切换到 **Elements**（元素）标签 → 按 `Ctrl+F` 打开搜索 → 输入 `var biz` 搜索。

**③ 复制 Fakeid**

页面源代码中会找到类似 `var biz = "MzI5ODUzMDE1Mg=="` 的一行，复制引号内的 Base64 字符串（例如 `MzI5ODUzMDE1Mg==`）。这就是 `WEIXIN_FAKEID`。

---

> **提示**：如果找不到 `var biz`，也可以按 `Ctrl+U` 打开「查看网页源代码」，直接 `Ctrl+F` 搜索 `biz`。

### 3. 配置 / Configure

```bash
cp .env.example .env
```

编辑 `.env`，填入上一步获取的凭证：

```env
WEIXIN_COOKIE=你的完整Cookie字符串
WEIXIN_TOKEN=你的token
WEIXIN_FAKEID=你的fakeid
TARGET_NAME=公众号名称
MAX_ARTICLES=50
REQUEST_INTERVAL=12
OUTPUT_DIR=output
```

### 4. 运行 / Run

```bash
python main.py
```

运行完成后会自动打开索引页。所有文章保存在 `output/` 目录下。

## 配置说明 / Configuration

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `WEIXIN_COOKIE` | 是 | - | 浏览器 Cookie 完整字符串 |
| `WEIXIN_TOKEN` | 是 | - | 微信后台 token |
| `WEIXIN_FAKEID` | 是 | - | 公众号内部标识符 |
| `TARGET_NAME` | 否 | `weixin_articles` | 公众号名称（用于输出目录命名） |
| `MAX_ARTICLES` | 否 | `50` | 最多抓取文章数 |
| `REQUEST_INTERVAL` | 否 | `12` | 请求间隔（秒） |
| `OUTPUT_DIR` | 否 | `output` | 输出根目录 |

## 依赖 / Dependencies

- Python 3.8+
- requests
- beautifulsoup4
- lxml
- python-dotenv

## 注意事项 / Notes

- Cookie 和 Token 有时效性，过期后需重新从浏览器提取
- 请合理设置 `REQUEST_INTERVAL`，过短的间隔可能导致请求被拒绝
- 本工具仅供个人学习和存档使用，请遵守微信公众平台的相关规定
- **不要将 `.env` 文件提交到公开仓库**，其中包含你的登录凭证

## 项目结构 / Project Structure

```
.
├── main.py                  # 入口，编排整个流程
├── config.py                # 配置加载（读取 .env）
├── article_fetcher.py       # 文章列表抓取（调用微信后台 API）
├── article_downloader.py    # 文章下载与 HTML 清洗
├── index_builder.py         # 索引页生成
├── utils.py                 # 公共工具（日志、重试、文件名处理）
├── requirements.txt         # Python 依赖
├── .env.example             # 配置模板
└── docs/                    # 设计文档与使用指南
```

## License

MIT
