# 微信公众号文章抓取工具 — 设计文档

> 目标：抓取指定微信公众号"银河系漫游客"文章（首期最新 50 篇），制作时间排序目录 + 离线 HTML 归档。

## 1. 技术方案

### 1.1 方案选择：UA 伪装 + Cookie/Token 请求模拟

通过登录微信公众号后台（mp.weixin.qq.com），从浏览器提取 Cookie、Token、Fakeid 三个关键参数，模拟后台请求调用文章列表接口。无需认证公众号即可使用。

### 1.2 核心接口

```
GET https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_ex
    &begin=0
    &count=5
    &fakeid=<FAKEID>
    &type=9
    &query=
    &token=<TOKEN>
    &lang=zh_CN
    &f=json
    &ajax=1
```

- 每次返回 5 条（一次发布），翻页时 `begin` 递增
- 需要 Cookie 和 Token 维持登录态，二者有较短时效性

### 1.3 关键参数获取方式

| 参数 | 获取方式 |
|------|----------|
| Cookie | 登录 mp.weixin.qq.com → F12 → Network → 任意请求 Headers → 复制完整 Cookie |
| Token | 同上，URL Query String 中 `token=` 后面的数字串 |
| Fakeid | 打开目标公众号任意文章 → F12 → 搜索 `var biz` → 复制引号内值 |

### 1.4 技术栈

- Python 3.10+
- `requests` — HTTP 请求
- `beautifulsoup4` — HTML 解析与清洗
- `python-dotenv` — 配置管理

---

## 2. 架构设计

```
用户浏览器（手动提取参数）
    │
    ▼
.env 配置文件 (Cookie / Token / Fakeid)
    │
    ▼
┌─────────────────────────────────────────────┐
│                main.py（编排入口）             │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ article_fetcher.py                   │   │
│  │ - 分页拉取文章列表                     │   │
│  │ - 输出 articles_metadata.json         │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼                            │
│  ┌──────────────────────────────────────┐   │
│  │ article_downloader.py                │   │
│  │ - 逐篇下载文章 HTML                   │   │
│  │ - 清洗内容，下载图片到本地             │   │
│  │ - 替换图片链接为本地相对路径            │   │
│  └──────────────┬───────────────────────┘   │
│                 ▼                            │
│  ┌──────────────────────────────────────┐   │
│  │ index_builder.py                     │   │
│  │ - 读取 metadata 生成 index.html       │   │
│  │ - 按发布时间倒序排列                   │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
    │
    ▼
output/银河系漫游客/
```

---

## 3. 输出文件结构

```
output/银河系漫游客/
├── index.html                 # 目录索引页（可离线浏览）
├── articles_metadata.json    # 文章元数据（供二次利用）
├── articles/                 # 独立 HTML 文章文件
│   ├── 2025-05-20_标题A.html
│   ├── 2025-05-15_标题B.html
│   └── ...
└── images/                   # 文章内图片本地存档
    └── 2025-05-20_标题A/
        ├── img001.jpg
        └── img002.png
```

### 3.1 index.html（目录索引页）

- 表格列：序号 | 发布时间 | 文章标题（点击跳转本地文件） | 原文链接
- 顶部统计区：公众号名称、文章总数、抓取时间
- 纯 CSS 样式，响应式，无外部依赖
- 所有文章链接指向本地 `articles/` 目录，完全离线可用

### 3.2 每篇文章 HTML（articles/ 目录）

- 文件名格式：`YYYY-MM-DD_文章标题.html`
- 内容清洗：
  - 保留原文完整格式（段落、加粗、引用、列表等）
  - 下载文章内图片到 `images/` 目录，链接替换为相对路径
  - 去除微信隐藏样式、JS 脚本、广告/推荐内容
  - 顶部元信息区：文章标题、发布时间、作者、原文链接
- 自包含：无网络环境也可独立打开阅读

### 3.3 articles_metadata.json

```json
[
  {
    "id": 1,
    "title": "文章标题",
    "publish_time": "2025-01-15 10:30:00",
    "link": "https://mp.weixin.qq.com/s/xxxx",
    "local_file": "articles/2025-01-15_文章标题.html",
    "image_dir": "images/2025-01-15_文章标题/"
  }
]
```

---

## 4. 配置设计

### .env 文件

```
WEIXIN_COOKIE=your_cookie_here
WEIXIN_TOKEN=1234567890
WEIXIN_FAKEID=MzU1MDk0ODI0Mw==
TARGET_NAME=银河系漫游客
MAX_ARTICLES=50
REQUEST_INTERVAL=12
OUTPUT_DIR=output
```

### 配置说明

| 参数 | 说明 |
|------|------|
| WEIXIN_COOKIE | 登录后的浏览器 Cookie 字符串 |
| WEIXIN_TOKEN | 后台 URL 中的 token 参数 |
| WEIXIN_FAKEID | 目标公众号的内部标识 |
| TARGET_NAME | 公众号名称（用于输出目录命名） |
| MAX_ARTICLES | 本次抓取上限（首期 50） |
| REQUEST_INTERVAL | 请求间隔秒数，防止风控（建议 ≥ 10） |
| OUTPUT_DIR | 输出根目录 |

---

## 5. 运行流程

### 5.1 首次配置

1. 注册个人订阅号：mp.weixin.qq.com（免费，无需企业认证）
2. 登录后台，在目标公众号任意文章中，F12 搜索 `var biz` 获取 Fakeid
3. 在 Network 面板任意 XHR 请求中提取 Cookie（Headers）和 Token（Query String）
4. 填入 `.env` 文件

### 5.2 运行

```bash
pip install requests beautifulsoup4 python-dotenv
python main.py
```

- 按 `REQUEST_INTERVAL` 间隔发送请求
- 终端输出实时进度（当前篇数 / 总篇数）
- 完成后提示输出路径，可手动打开 `index.html`

### 5.3 Cookie/Token 过期处理

Cookie/Token 失效时（接口返回鉴权错误），脚本提示：

> 鉴权失败：Cookie 或 Token 已过期。
> 请重新登录 mp.weixin.qq.com，从浏览器开发者工具提取最新的 Cookie 和 Token，
> 更新 .env 文件后重新运行。

---

## 6. 错误处理

| 场景 | 处理策略 |
|------|----------|
| 网络超时 | 重试 3 次，间隔递增（5s / 10s / 20s），超过后跳过该篇 |
| Cookie 过期 | 终止运行，提示更新凭证 |
| 文章已被删除 | 标记跳过，记录到日志，继续下一篇 |
| 图片下载失败 | 保留原始链接作为 fallback，继续执行 |
| 请求频率限制（429 或验证码） | 暂停 5 分钟，提示用户 |

---

## 7. 项目文件清单

```
weixin_article_crawler/
├── main.py                  # 编排入口
├── article_fetcher.py       # 文章列表获取
├── article_downloader.py    # 文章内容下载与清洗
├── index_builder.py         # 目录索引生成
├── config.py                # 配置加载
├── .env                     # 用户配置（不入 git）
├── .env.example             # 配置模板
├── requirements.txt         # 依赖声明
└── docs/
    └── 2026-05-22-weixin-article-crawler-design.md  # 本设计文档
```

---

## 8. 后续扩展方向（不在首期范围）

- 全量抓取（移除 MAX_ARTICLES 限制）
- 文章全文搜索功能
- 转 PDF/EPUB 导出
- 自动化 Cookie 刷新（Playwright 模拟登录）
- 增量更新（仅抓取新文章）
