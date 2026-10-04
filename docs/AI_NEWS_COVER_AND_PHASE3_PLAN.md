# PERSONAL-BLOG：封面图片修复与下一阶段开发方案

> 基于当前 HANDOFF 状态制定。当前已完成 10 源 Collector、AI Editor、Jekyll Publisher、7 篇文章、45 项测试和 Jekyll strict build。  
> 当前主要视觉问题：文章卡片顶部仍显示纯色占位区域，没有真实封面。  
> 本方案先完成 **Phase 2.5：Cover Image Pipeline（封面图片管线）**，然后进入 **Phase 3：半自动内容运营**。

## 1. 当前问题判断

当前截图中的紫色区域不是 Netlify 图片加载故障，而是文章没有可用封面图。Phase 2 为避免版权风险，没有给 7 篇文章加入未经授权的图片；Phase 1 Collector 也只保存候选图片元数据，不下载图片。

当前状态：

```text
资讯采集           已完成
文章编辑           已完成
Jekyll 发布        已完成
封面候选采集       部分具备
图片下载           未实现
图片标准化         未实现
图片写入 assets    未实现
Front Matter image 未实现
卡片真实封面       未实现
```

所以下一步应补齐独立的媒体处理链，而不是继续改 Netlify。

## 2. Phase 2.5 总目标

建立：

```text
NewsItem
→ Image Candidate
→ 来源与安全校验
→ 下载
→ 图片规范化
→ 本地缓存
→ 写入 Jekyll Front Matter
→ 首页卡片显示
```

最终要求：

- 现有 7 篇文章全部拥有封面。
- 有合适官方图片时优先使用官方图片。
- 没有合适图片时自动生成统一风格的本地资讯封面。
- 不直接 hotlink 外站图片。
- Netlify Build 不联网抓图片。
- `_posts` 中只引用本地静态资源。

## 3. 推荐新增目录

```text
news_pipeline/
├── media/
│   ├── __init__.py
│   ├── resolver.py
│   ├── downloader.py
│   ├── validator.py
│   ├── processor.py
│   ├── fallback.py
│   └── manifest.py
│
assets/
└── news/
    ├── 2026/
    │   └── 10/
    └── manifest.json
```

正式封面统一进入：

```text
assets/news/YYYY/MM/
```

例如：

```text
assets/news/2026/10/anthropic-claude-frontier-academy.webp
```

不要把最终图片放进 `news_pipeline/storage/`，因为 `news_pipeline/` 被 Jekyll exclude。

## 4. T1：图片候选解析

实现 `news_pipeline/media/resolver.py`。

候选优先级：

```text
1. 官方文章 structured data 中的主图
2. 官方页面 og:image
3. 官方页面 twitter:image
4. Feed media
5. 官方 Press / Media Kit
6. 本站自动生成 fallback cover
```

规则：

- 只接受来源官方域名或官方 CDN。
- 不从二级媒体直接搬图。
- 不从搜索引擎图片结果直接下载。
- 不把任意 `og:image` 自动视为可自由转载。
- 每个候选记录 source page 和原图 URL。

## 5. T2：图片下载与验证

实现：

```text
news_pipeline/media/downloader.py
news_pipeline/media/validator.py
```

下载前检查：

```text
HTTP 200
Content-Type 为 image/*
文件不是 HTML 错误页
文件大小合理
URL 仍属于允许域名 / 官方 CDN
重定向链合法
```

建议：

```text
单图最大 10 MB
timeout 15 秒
最多 2 次重试
```

下载失败不得阻塞文章发布，直接进入 fallback。

## 6. T3：图片统一处理

实现 `news_pipeline/media/processor.py`。

先读取当前文章卡片 CSS 的实际比例，再确定输出尺寸。若当前卡片适配 16:9，可统一：

```text
WebP
1280 × 720
质量 82～88
```

处理：

```text
自动 EXIF 旋转
转换 RGB
保持主体比例
按前端比例裁切
去 EXIF / GPS
输出 WebP
```

不要机械固定尺寸，最终比例必须服从现有主题。

## 7. T4：文件命名与缓存

使用稳定 slug：

```text
<post-slug>.webp
```

建立：

```text
assets/news/manifest.json
```

记录：

```json
{
  "post_slug": "...",
  "local_path": "...",
  "original_url": "...",
  "source_page": "...",
  "sha256": "...",
  "width": 1280,
  "height": 720,
  "generated": false
}
```

相同 SHA256 不重复保存。

## 8. T5：Fallback Cover

这是必须实现的能力。

不是每篇官方资讯都有适合转载的图片，所以系统必须能自动生成统一封面。

实现：

```text
news_pipeline/media/fallback.py
```

封面建议包含：

```text
来源名称
文章短标题
主分类
发布日期
PERSONAL-BLOG / AI NEWS 标识
```

视觉：

```text
Material Design 3 渐变
简单几何图形
稳定的来源 accent
```

建议用 Pillow 本地生成，不依赖在线图片生成 API。

目标：没有官方图时仍然 100% 有封面。

## 9. T6：Publisher 接入图片

扩展：

```text
news_pipeline/publisher/jekyll.py
```

为文章写入：

```yaml
image: "/assets/news/2026/10/example.webp"
image_alt: "..."
image_source_url: "..."
```

如果现有模板字段不是 `image`，以实际模板为准，不要为了 Pipeline 大改主题。

## 10. T7：给现有 7 篇文章补图

处理当前 7 篇：

```text
Anthropic Claude Frontier Academy
Google Gemini 4 Argon
Google Project Suncatcher
Google DeepMind SynthID Bio
Microsoft Research Quine
H Company Holo4
AllenAI AstaBrief
```

流程：

```text
检查 inbox image candidate
↓
检查官方页面
↓
选择可用官方图
↓
无法明确使用
↓
生成 fallback cover
↓
写 assets/news
↓
更新 _posts Front Matter
```

目标是：

```text
7 / 7 有封面
```

不是强求 7 / 7 都使用官方原图。

## 11. T8：前端显示验收

检查：

```text
首页 Grid
首页 List
文章详情页
搜索结果
移动端
暗色模式
```

要求：

- 图片不拉伸。
- 不严重裁掉主体。
- 有固定 aspect-ratio。
- 列表图 lazy loading。
- 图片失败时保留 CSS fallback。
- 当前紫色占位区可以继续作为最终 fallback。

## 12. T9：媒体测试

新增：

```text
test_media_resolver
test_media_validator
test_image_processor
test_fallback_cover
test_manifest
test_publisher_image_frontmatter
```

至少覆盖：

```text
无图片 → fallback
远程图片失败 → fallback
重复图片 → 不重复下载
生成后路径存在
WebP 可读取
尺寸符合主题
Front Matter 路径正确
不存在远程 hotlink
```

## 13. T10：Jekyll 验收

运行：

```bash
bundle exec jekyll build --strict_front_matter
```

检查：

```text
_site/assets/news/
```

必须包含封面。

生成 HTML 中不得直接引用外站图片作为文章封面，生产页面应使用：

```text
/assets/news/...
```

## 14. Phase 2.5 完成门槛

只有全部满足才算完成：

```text
7 篇现有文章全部有封面
官方图和 fallback 两条路径都可用
没有图片 hotlink
图片进入 assets/news
存在 manifest
图片处理可重复执行
Jekyll strict build 通过
Grid / List 显示正常
文章页正常
移动端无明显问题
```

完成后暂停，不自动 push。

# 15. 下一阶段：Phase 3 半自动 AI 资讯运营

Phase 2.5 完成后，完整链路应成为：

```text
互联网
→ Collector
→ inbox
→ Editor
→ Media Pipeline
→ Publisher
→ Jekyll
→ GitHub
→ Netlify
```

下一阶段重点是稳定运营，而不是继续增加前端功能。

## 16. Phase 3.1：统一内容状态机

建议状态：

```text
collected
↓
selected
↓
edited
↓
media_ready
↓
review_ready
↓
approved
↓
published
↓
archived
```

建议建立统一索引：

```text
news_pipeline/state/items.jsonl
```

避免以后从多个 JSON 文件隐式推断状态。

## 17. Phase 3.2：人工审核队列

增加：

```bash
python -m news_pipeline.cli review
```

展示：

```text
标题
来源
原链接
摘要
正文
分类
标签
封面
```

支持：

```text
approve
reject
skip
edit
```

第一版用 CLI 即可，不急着开发 CMS。

## 18. Phase 3.3：定时采集

稳定后再接 Codex Scheduled Task 或操作系统任务。

推荐：

```text
08:00 collect
12:00 collect
18:00 collect
22:00 collect
```

每次只做：

```text
Collect
→ dedupe
→ inbox
```

不要每次采集都自动发布。

## 19. Phase 3.4：每日编辑批次

推荐每天两批：

```text
12:30
20:30
```

执行：

```text
select
→ edit
→ media
→ review_ready
```

每批控制在：

```text
3～8 条
```

优先质量，不追求数量。

## 20. Phase 3.5：发布策略

前期推荐：

```text
自动采集
+
自动生成待审核稿
+
人工确认
+
Publisher
```

不要直接：

```text
互联网
→ AI
→ git push
```

推荐最终链路：

```text
Scheduled Collector
       ↓
AI Editor
       ↓
Media Pipeline
       ↓
Review Queue
       ↓
人工 Approve
       ↓
Publisher
       ↓
git commit
       ↓
git push
       ↓
Netlify
```

## 21. Phase 3.6：Git 自动提交

审核流程稳定后再加入。

一次发布批次一个 commit：

```text
news: publish YYYY-MM-DD evening digest
```

自动化提交前必须执行：

```text
Pipeline tests
Jekyll strict build
git status
```

全部通过才能 commit。

前期建议 push 仍由用户显式触发。

## 22. Phase 3.7：资讯质量评分

为候选增加内部评分：

```text
authority
freshness
novelty
technical_value
general_interest
duplication
```

可形成：

```text
importance_score: 0～100
```

只用于内部筛选，不需要显示给网站用户。

## 23. Phase 3.8：第二批数据源

暂时不要马上增加。

等当前 10 个一级源稳定运营若干批次后，再考虑：

```text
Reuters
TechCrunch
The Verge
Hacker News
GitHub Trending
Reddit
```

这些更适合作为 Discovery Source。发现新闻后优先回溯官方博客、GitHub、论文或项目主页，再写正式文章。

## 24. 推荐开发优先级

```text
P0  封面图片 Pipeline
P0  给现有 7 篇补图
P0  Grid / List 图片验收

P1  内容状态机
P1  Review CLI
P1  图片 provenance / manifest

P2  定时 collect
P2  定时生成 review-ready 草稿
P2  一键 publish

P3  Git 自动 commit
P3  自动 push
P3  扩大数据源
```

## 25. 当前不建议投入的方向

暂时不要优先做：

```text
更多数据源
数据库
CMS
Netlify Functions
Cloudflare Worker
实时服务
用户系统
评论系统
```

当前最值得投入的是：

```text
内容质量
+
封面视觉质量
+
稳定审核
+
稳定自动化
```

## 26. 可直接给 Codex / Agent 的总任务

```text
读取当前 HANDOFF 和项目实际代码。在不改变现有 Jekyll + GitHub + Netlify 静态架构的前提下，实现 Phase 2.5 Cover Image Pipeline。

首先分析当前文章卡片实际读取的封面字段和 CSS 比例。为 news_pipeline 新增独立 media 模块，实现官方图片候选解析、allowed-domain 校验、图片下载验证、格式转换、本地 WebP 存储、SHA256 去重、manifest 记录和 fallback cover 自动生成。

图片优先使用官方文章或官方 CDN 的可用视觉素材，但不要把 og:image 自动视为可自由转载；无法明确使用时自动生成本站统一风格 fallback cover。最终生产文章不得直接 hotlink 外站图片。

将最终封面写入 assets/news/YYYY/MM/，并给当前 7 篇 Jekyll 文章补齐 Front Matter 图片字段。目标是 7/7 都有本地封面，其中没有合适官方图的文章使用 fallback。

补充媒体 Pipeline 单元测试，随后运行全部 news_pipeline tests 和 Jekyll strict build，并检查生成的 _site 中所有文章卡片和文章页都使用本地 assets/news 路径。

不要创建定时任务，不自动 git commit，不自动 git push，不操作 Netlify。完成后输出 7 篇文章各自采用的图片来源、官方图/fallback 状态、本地文件路径、测试结果、Jekyll build 结果和下一阶段建议。
```
