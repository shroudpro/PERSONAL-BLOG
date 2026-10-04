# AI 文章采集数据主题与数据结构

本文是新增数据源、设计爬虫和把采集结果接入 PERSONAL-BLOG 时的约定。目标是让不同来源的文章先转换成统一的资讯数据，再进入编辑和 Jekyll 发布流程。

## 1. 先看数据流

~~~text
官方 RSS / API / Sitemap / 列表页
              │
              ▼
news_pipeline/collectors/
              │ 统一输出 NewsItem
              ▼
news_pipeline/storage/inbox/*.json  ──┐
news_pipeline/state/seen.jsonl       │ 去重
                                    ▼
news_pipeline/storage/editor_drafts/*.json
                                    │ 人工或编辑流程补全中文文章
                                    ▼
_posts/YYYY-MM-DD-source-id-slug.md
news_pipeline/state/publications.jsonl
~~~

采集器只负责发现资讯和保存可核验的元数据，不直接生成正式文章，也不直接写入 <code>_posts/</code>。当前实现只保存来源提供的摘要候选和图片候选 URL，不保存整篇原文，也不自动下载图片。

## 2. 数据主题范围

### 2.1 来源主题

首选公开、可追溯的一级来源：

- 模型发布：基础模型、推理模型、多模态模型、训练方法。
- 产品更新：模型 API、聊天产品、开发工具、平台能力。
- 研究进展：论文、基准、Agent、科学 AI、机器学习方法。
- 开源项目：开放权重、数据集、框架、工具链和许可证变化。
- AI 工具：面向开发者或研究者的可实际使用工具。
- AI 基础设施：GPU、推理、训练、数据中心、部署和系统工程。
- 安全与治理：安全研究、评测、对齐、隐私、滥用防护和政策。
- 行业动态：重要合作、投资、组织变化或具有技术影响的公告。

来源的 <code>type</code> 只有两种：<code>official</code>（公司或项目官方来源）和 <code>research</code>（论文、研究机构或研究项目来源）。当前候选来源包括 OpenAI、Anthropic、Google DeepMind、Google AI、Meta AI、Microsoft Research、NVIDIA Technical Blog、Hugging Face、Mistral AI 和 arXiv。

### 2.2 文章数据主题

每条采集记录应覆盖以下主题：

| 主题 | 对应字段 | 用途 |
| --- | --- | --- |
| 来源身份 | <code>source_id</code>、<code>source_name</code>、<code>source_type</code> | 识别来源、排序和筛选权威性 |
| 文章身份 | <code>id</code>、<code>url</code>、<code>canonical_url</code> | 稳定标识文章并构建原文链接 |
| 时间 | <code>published_at</code>、<code>fetched_at</code> | 判断时效性、生成文件名和追踪采集时间 |
| 内容候选 | <code>title</code>、<code>summary_raw</code>、<code>content_text</code>、<code>author</code>、<code>language</code> | 供编辑筛选和核验 |
| 分类候选 | <code>tags_raw</code>、<code>category_raw</code> | 保留来源标签，供编辑映射到本站分类 |
| 媒体候选 | <code>image_url</code>、<code>image_alt</code>、<code>image_source</code> | 记录可能的封面来源，不代表已获得转载许可 |
| 处理状态 | <code>status</code> | 标记当前处于采集阶段；初始值为 <code>collected</code> |
| 去重指纹 | <code>content_hash</code> | 辅助判断内容重复 |

本站正式文章的分类只允许以下 8 个值：<code>模型发布</code>、<code>产品更新</code>、<code>研究进展</code>、<code>开源项目</code>、<code>AI 工具</code>、<code>AI 基础设施</code>、<code>安全与治理</code>、<code>行业动态</code>。采集器的 <code>category_raw</code> 不要求直接使用这 8 个值，它只是来源的原始分类候选；最终分类在编辑草稿中确定。

## 3. 采集层：<code>NewsItem</code> JSON

### 3.1 文件位置和命名

每条新资讯写入：

~~~text
news_pipeline/storage/inbox/YYYYMMDD-HHMM-source-id-item-id.json
~~~

文件名由 <code>InboxStore</code> 根据 <code>fetched_at</code>、<code>source_id</code> 和 <code>id</code> 自动生成。爬虫不要自行改名，也不要把结果写到 <code>_posts/</code>。

### 3.2 字段定义

建议每个 JSON 都输出完整字段集合。表中“必须”表示必须存在且有有效值；“可空”表示键应保留，但值可以是 <code>null</code>。

| 字段 | 类型 | 必填性 | 约束和说明 |
| --- | --- | --- | --- |
| <code>id</code> | string | 必须 | 由 <code>canonical_url</code> 的 SHA-256 前 16 位小写十六进制字符生成。使用 <code>build_news_item()</code>，不要用标题或随机 UUID。 |
| <code>source_id</code> | string | 必须 | 必须与 <code>sources.yml</code> 的 <code>id</code> 一致；只允许小写 ASCII 字母、数字和单个连字符，例如 <code>google-ai</code>。 |
| <code>source_name</code> | string | 必须 | 来源展示名，来自 <code>sources.yml</code> 的 <code>name</code>。 |
| <code>source_type</code> | string | 必须 | 只能是 <code>official</code> 或 <code>research</code>。 |
| <code>title</code> | string | 必须 | 清理 HTML 和多余空白后的原始标题，不能为空。 |
| <code>url</code> | string | 必须 | 采集到的文章 URL，必须是 HTTP(S)；可保留原始查询参数。 |
| <code>canonical_url</code> | string | 必须 | 用于身份和去重的规范 URL。会去除 fragment、常见追踪参数和末尾 <code>/</code>，并优先采用页面 canonical URL。 |
| <code>published_at</code> | string 或 null | 必须有键，可空 | 原文发布时间，统一为 UTC ISO 8601，例如 <code>2026-10-03T12:00:00Z</code>。来源没有日期时为 <code>null</code>。 |
| <code>fetched_at</code> | string | 必须 | 本次抓取时间，统一为 UTC ISO 8601，不能是本地时间或无时区时间。 |
| <code>author</code> | string 或 null | 可空 | 原文作者；没有可靠值时为 <code>null</code>。 |
| <code>language</code> | string 或 null | 可空 | 页面或来源语言，例如 <code>en</code>、<code>en-us</code>、<code>zh-CN</code>。 |
| <code>summary_raw</code> | string 或 null | 可空 | RSS 摘要、description、meta description 或页面结构化摘要，去除 HTML 后保存。 |
| <code>content_text</code> | string 或 null | 可空 | 当前 MVP 只要求摘要级纯文本；通常可与 <code>summary_raw</code> 相同，不要为了填充字段抓取整篇文章。 |
| <code>tags_raw</code> | string 数组 | 必须 | 来源标签与来源默认标签合并后的列表；去除空值和重复值。没有标签时使用 <code>[]</code>。 |
| <code>category_raw</code> | string 或 null | 可空 | 来源原始栏目或类别候选，不要写本站最终分类以外的占位字符串。没有值使用 <code>null</code>。 |
| <code>image_url</code> | string 或 null | 可空 | 原文结构化数据、<code>og:image</code>、Twitter Card 或 feed 提供的候选图片 URL。没有图片使用 <code>null</code>。 |
| <code>image_alt</code> | string 或 null | 可空 | 图片的 alt、title 或 description；没有值使用 <code>null</code>。 |
| <code>image_source</code> | string 或 null | 可空 | 图片来源页面或来源主页，用于追溯；它不是版权许可证明。 |
| <code>content_hash</code> | string 或 null | 必须有键，可空 | <code>build_news_item()</code> 根据规范化后的 <code>content_text</code> 或摘要计算 SHA-256。没有任何内容候选时为 <code>null</code>。 |
| <code>status</code> | string | 必须 | 采集层初始值固定为 <code>collected</code>。不要在爬虫中提前写 <code>published</code> 或 <code>approved</code>。 |

### 3.3 标准示例

下面是一个可以放入 <code>storage/inbox/</code> 的完整记录。<code>id</code> 和 <code>content_hash</code> 仅作格式示例，实际值必须由代码计算。

~~~json
{
  "id": "e8e0bfab56ba1a2c",
  "source_id": "google-ai",
  "source_name": "Google AI / Google Blog - AI",
  "source_type": "official",
  "title": "Guided Vision in Gemini Live: built for accessibility",
  "url": "https://blog.google/innovation-and-ai/products/gemini-app/guided-vision-gemini-live/?utm_source=feed",
  "canonical_url": "https://blog.google/innovation-and-ai/products/gemini-app/guided-vision-gemini-live",
  "published_at": "2026-10-01T00:00:00Z",
  "fetched_at": "2026-10-03T13:42:00Z",
  "author": "Isha Sheth",
  "language": "en-us",
  "summary_raw": "Guided Vision in Gemini Live is built alongside the blind and low-vision community and offers real-time visual assistance.",
  "content_text": "Guided Vision in Gemini Live is built alongside the blind and low-vision community and offers real-time visual assistance.",
  "tags_raw": ["AI", "Google"],
  "category_raw": "product",
  "image_url": "https://storage.googleapis.com/example/hero.png",
  "image_alt": null,
  "image_source": "https://blog.google/",
  "content_hash": "1f54ae45e1dfd80b691d2a88037ca2a266d9791e92d6f1d3c29432b324eda526",
  "status": "collected"
}
~~~

注意：不要把缺失值写成字符串 <code>"None"</code>、<code>"null"</code> 或空格。缺失值使用 <code>null</code>；标签字段使用空数组 <code>[]</code>。

### 3.4 标准化和去重规则

优先调用 <code>news_pipeline.core.models.build_news_item()</code> 构造记录，它会统一处理 URL、标题、日期、标签和内容指纹。

去重索引 <code>news_pipeline/state/seen.jsonl</code> 按以下顺序判断重复：

1. <code>canonical_url</code>。
2. 标题规范化后的值 <code>normalized_title</code>。
3. <code>content_hash</code>。
4. <code>id</code>。

<code>seen.jsonl</code> 是系统生成的状态文件，记录的是去重索引，不是新的文章数据。不要在爬虫中手工维护它；让 <code>InboxStore.save()</code> 写入即可。

## 4. 来源配置：<code>sources.yml</code>

新增来源前先在 <code>news_pipeline/config/sources.yml</code> 增加配置。配置是来源元数据和采集入口的唯一入口；采集器通过 <code>source_id</code> 读取它。

### 4.1 最小配置

~~~yaml
sources:
  - id: example-lab
    name: Example Lab
    type: official
    homepage: https://example.com/
    enabled: true
    priority: 11
    fetch_method: feed
    feed_url: https://example.com/feed.xml
    allowed_domains: [example.com]
    default_tags: [AI, Example Lab]
    language: en
    notes: 官方 RSS；仅包含新闻文章。
~~~

### 4.2 字段和采集器的关系

| 配置字段 | 适用方法 | 说明 |
| --- | --- | --- |
| <code>id</code>、<code>name</code>、<code>type</code>、<code>homepage</code>、<code>enabled</code>、<code>priority</code>、<code>allowed_domains</code> | 全部 | 来源身份、启用状态、排序和域名安全边界。 |
| <code>fetch_method</code> | 全部 | 只能是 <code>feed</code>、<code>api</code>、<code>sitemap</code>、<code>html</code>、<code>arxiv</code>。优先选择官方 RSS/Atom，其次 API、Sitemap，最后才解析 HTML。 |
| <code>feed_url</code> / <code>feed_urls</code> | <code>feed</code>、<code>arxiv</code> | 一个或多个 RSS/Atom 地址。arXiv 可配置多个分类 feed。 |
| <code>api_url</code>、<code>api_items_path</code>、<code>api_field_map</code> | <code>api</code> | <code>api_items_path</code> 指向条目数组；<code>api_field_map</code> 把 <code>title</code>、<code>url</code>、<code>published_at</code>、<code>summary</code> 等标准字段映射到响应 JSON 路径。 |
| <code>sitemap_urls</code> | <code>sitemap</code> | Sitemap 或 Sitemap index 地址；配合 <code>item_url_patterns</code> 过滤文章 URL。 |
| <code>list_url</code> | <code>html</code> | 列表页地址；<code>item_url_patterns</code> 和 <code>exclude_url_patterns</code> 控制详情页链接。 |
| <code>default_tags</code> | 全部 | 为该来源每条资讯附加的默认标签。 |
| <code>language</code> | 全部 | 页面未提供语言时使用的默认值。 |
| <code>categories</code> | 主要用于 arXiv | 来源分类，如 <code>cs.AI</code>、<code>cs.CL</code>；它不是本站文章主分类。 |
| <code>item_url_patterns</code>、<code>exclude_url_patterns</code> | <code>html</code>、<code>sitemap</code> | 正则表达式，必须只匹配允许域名下的文章链接。 |
| <code>notes</code> | 全部 | 记录端点、分页、反爬、日期或降级策略，便于后续维护。 |

每个 endpoint 必须属于 <code>allowed_domains</code>。爬虫要遵守 <code>robots.txt</code>、限速和重试策略，不绕过登录、付费墙、验证码或反爬挑战。

## 5. 编辑层：文章草稿 JSON

<code>edit</code> 从 inbox 选择候选后，会在以下目录创建草稿骨架：

~~~text
news_pipeline/storage/editor_drafts/<news_id>.json
~~~

文件名必须与 <code>news_id</code> 完全一致。草稿不是采集器的直接输出，采集器只需要保证对应的 <code>NewsItem</code> 信息足以生成草稿骨架。

### 5.1 草稿字段

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| <code>news_id</code> | string | 必须等于 inbox 的 <code>id</code>。 |
| <code>source_id</code> | string | 与来源配置一致。 |
| <code>source_name</code> | string | 来源展示名。 |
| <code>title</code> | string | 最终中文标题，不能为空。 |
| <code>slug</code> | string | 只用小写 ASCII 字母、数字和单个连字符。 |
| <code>date</code> | string | 带时区的时间，必须表示 Asia/Shanghai（<code>+08:00</code>）。 |
| <code>summary</code> | string | 非空中文摘要。 |
| <code>category</code> | string | 必须是 8 个本站分类之一。 |
| <code>tags</code> | string 数组 | 2–5 个不重复标签。 |
| <code>source_url</code> | string | 可访问的规范原文 URL。 |
| <code>source_published_at</code> | string 或 null | 原文发布时间；继承 <code>published_at</code>，未知时为 <code>null</code>。 |
| <code>body_markdown</code> | string | 非空 Markdown，必须包含指向 <code>source_url</code> 的可点击链接。 |
| <code>image</code> | string 或 null | 当前 MVP 留空；在媒体管线启用前不要填远程图片 URL。 |

示例：

~~~json
{
  "news_id": "e8e0bfab56ba1a2c",
  "source_id": "google-ai",
  "source_name": "Google AI / Google Blog - AI",
  "title": "Google 为 Gemini Live 增加面向视障用户的 Guided Vision",
  "slug": "google-gemini-live-guided-vision",
  "date": "2026-10-03T21:00:00+08:00",
  "summary": "Google 发布 Gemini Live 的 Guided Vision 功能，提供实时视觉辅助。",
  "category": "产品更新",
  "tags": ["Google", "Gemini", "无障碍", "多模态"],
  "source_url": "https://blog.google/innovation-and-ai/products/gemini-app/guided-vision-gemini-live",
  "source_published_at": "2026-10-01T00:00:00Z",
  "body_markdown": "## 发生了什么\n\n正文……\n\n## 来源\n\n[Google 官方文章](https://blog.google/innovation-and-ai/products/gemini-app/guided-vision-gemini-live)",
  "image": null
}
~~~

## 6. 发布层：Jekyll Markdown

Publisher 会把通过校验的草稿写成：

~~~text
_posts/YYYY-MM-DD-source-id-slug.md
~~~

当前实际生成的 Front Matter 字段如下：

~~~yaml
---
layout: post
title: "Google 为 Gemini Live 增加面向视障用户的 Guided Vision"
date: 2026-10-03 21:00:00 +0800
summary: "Google 发布 Gemini Live 的 Guided Vision 功能，提供实时视觉辅助。"
categories:
  - 产品更新
tags:
  - Google
  - Gemini
  - 无障碍
  - 多模态
image: ""
source_name: "Google AI / Google Blog - AI"
source_url: "https://blog.google/innovation-and-ai/products/gemini-app/guided-vision-gemini-live"
source_published_at: "2026-10-01T00:00:00Z"
ai_generated: true
reviewed: false
toc: true
---
~~~

爬虫不需要生成这部分 Markdown。它只需保证 inbox 的 <code>title</code>、规范 URL、发布时间、摘要候选和来源信息准确，编辑流程再补全中文标题、摘要、分类、标签和正文。

## 7. 爬虫应放在哪里

### 7.1 已有采集方式

如果新来源符合已有方式，优先只改配置，不新增采集器：

- RSS/Atom：<code>news_pipeline/collectors/feed.py</code>
- JSON API：<code>news_pipeline/collectors/api.py</code>
- Sitemap：<code>news_pipeline/collectors/sitemap.py</code>
- 列表页 HTML：<code>news_pipeline/collectors/html.py</code>
- arXiv 分类 feed：<code>news_pipeline/collectors/arxiv.py</code>

新增站点的推荐步骤：

1. 先验证官方 endpoint、字段、发布时间和 robots 规则。
2. 在 <code>sources.yml</code> 增加 <code>source_id</code> 和端点配置。
3. 让已有 collector 返回 <code>NewsItem</code>；不要在 collector 中返回自定义 JSON 形状。
4. 用 <code>build_news_item()</code> 传入标题、URL、日期、摘要、标签和图片候选。
5. 用 <code>collect --source &lt;source_id&gt; --dry-run</code> 检查数量，再执行正式采集。

### 7.2 需要新采集逻辑时

只有现有 <code>fetch_method</code> 无法表达来源行为时，才在 <code>news_pipeline/collectors/</code> 新增模块，并实现 <code>BaseCollector.collect()</code>。如果新增一种 <code>fetch_method</code>，还需要同步更新：

- <code>news_pipeline/core/models.py</code> 中的 <code>FetchMethod</code>。
- <code>news_pipeline/core/config.py</code> 的配置校验。
- <code>news_pipeline/cli.py</code> 的 <code>build_collector()</code> 映射。
- <code>tests/news_pipeline/</code> 中的采集器测试。

采集器必须使用 <code>HttpFetcher</code>，不要自行绕过域名校验、robots 或限速。异常应让当前来源失败并记录，不应因为一个来源导致其他来源无法采集。

## 8. 数据落盘位置总表

| 路径 | 数据内容 | 谁写入 | 是否是正式文章 |
| --- | --- | --- | --- |
| <code>news_pipeline/config/sources.yml</code> | 来源、端点、标签和抓取规则 | 开发者 | 否 |
| <code>news_pipeline/collectors/</code> | 爬虫实现 | 开发者 | 否 |
| <code>news_pipeline/storage/inbox/*.json</code> | 标准化 <code>NewsItem</code>，一条资讯一个 JSON | <code>collect</code> | 否 |
| <code>news_pipeline/storage/raw/</code> | 可选的原始响应调试缓存 | 调试代码 | 否；默认不生成，且被忽略 |
| <code>news_pipeline/state/seen.jsonl</code> | URL、标题和内容指纹去重状态 | <code>InboxStore</code> | 否 |
| <code>news_pipeline/reports/</code> | 来源发现、健康检查和编辑筛选报告 | CLI | 否 |
| <code>news_pipeline/storage/editor_drafts/*.json</code> | 待编辑文章草稿 | <code>edit</code> / 编辑者 | 否 |
| <code>_posts/*.md</code> | Jekyll 正式文章 | <code>publish</code> / 编辑者 | 是 |
| <code>news_pipeline/state/publications.jsonl</code> | 已生成文章的 <code>news_id</code>、路径和来源 URL | Publisher | 否 |
| <code>assets/news/</code> | 未来媒体管线处理后的本地封面 | 媒体管线 | 不是文章数据 |

<code>docs/</code> 和 <code>news_pipeline/</code> 已被 Jekyll 排除，不会被构建到 <code>_site/</code>。采集数据应留在 <code>news_pipeline/</code>，正式内容才进入 <code>_posts/</code>。

## 9. 接入完成检查清单

### 来源和采集

- [ ] <code>source_id</code> 符合小写 ASCII 加连字符规则，并且没有重复。
- [ ] endpoint 属于 <code>allowed_domains</code>，且已验证 HTTP 状态、robots 和访问频率。
- [ ] 能稳定提取标题和文章 URL；能提取日期时必须转换为 UTC。
- [ ] 使用 <code>build_news_item()</code>，不手写 <code>id</code>、<code>content_hash</code> 或规范化逻辑。
- [ ] 缺失值使用 <code>null</code> 或 <code>[]</code>，不使用 <code>"None"</code>、<code>"null"</code> 等占位字符串。
- [ ] <code>image_url</code> 只记录候选，不把 <code>og:image</code> 自动当作可转载图片。
- [ ] 不保存整页 HTML 或整篇原文，不写入 <code>_posts/</code>。

### 运行和验证

~~~powershell
.\\.venv\\Scripts\\python.exe -m news_pipeline.cli collect --source <source_id> --since-hours 168 --dry-run
.\\.venv\\Scripts\\python.exe -m news_pipeline.cli collect --source <source_id> --since-hours 168
.\\.venv\\Scripts\\python.exe -m news_pipeline.cli health
.\\.venv\\Scripts\\python.exe -m pytest tests\\news_pipeline -q
~~~

正式采集后检查：

1. <code>news_pipeline/storage/inbox/</code> 中每个 JSON 都能被 <code>NewsItem</code> 读取。
2. 相同来源重复运行不会产生相同 <code>canonical_url</code> 的新文件。
3. <code>seen.jsonl</code> 有对应去重记录，且没有凭手工编辑产生的脏数据。
4. 需要发布时，先运行 <code>edit --dry-run</code> 和 <code>publish --dry-run</code>，确认后再写入 <code>_posts/</code>。

## 10. 一句话原则

爬虫只负责把**可追溯的 AI 资讯元数据**转换为稳定的 <code>NewsItem</code> 并放入 <code>news_pipeline/storage/inbox/</code>；编辑流程负责中文文章，Publisher 负责 <code>_posts/</code>，媒体管线负责将来可能使用的本地封面。
