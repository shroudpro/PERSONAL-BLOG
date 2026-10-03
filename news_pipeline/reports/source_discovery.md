# 来源发现与端点探测报告

- 探测记录日期：2026-10-03（本机时区 Asia/Shanghai）。
- 证据范围：本报告先记录候选端点的直接请求探测，再单列采集器实测结果；两类证据分别注明，不把端点可访问等同于解析成功。
- 验收边界：下文“本机采集器实测”记录了 live CLI 解析、持久化采集、二次去重和字段审计结果。Jekyll strict build 因本地 Bundler 原生扩展构建失败而未能运行，仍未验证。
- 字段说明：URL 指端点中可见的文章 URL 或 sitemap URL 项；标题、日期和图片说明区分端点探测和采集器实际输出。端点探测未逐篇记录的字段不视为已观测。
- 合规边界：遇到 robots.txt 禁止或 HTTP 403 时不绕过限制、不伪装请求、不切换到被禁止的 API。

采集器实现层面，HTTP fetcher 会先读取目标主机的 robots.txt 并遵守其允许规则和 crawl-delay；同一主机默认至少间隔 1 秒，遇到 429 或 5xx 时按 Retry-After 或退避重试。以上是当前实现配置，不代表探测期间逐源测出了服务端限速值。探测记录没有给出各站的稳定请求配额。

## OpenAI

- Source：OpenAI（官方来源）。
- Homepage：`https://openai.com/`。
- Chosen method：Sitemap；配置直接请求四个 robots 公布的子 sitemap。
- Actual endpoint：`https://openai.com/sitemap.xml/product/`、`https://openai.com/sitemap.xml/research/`、`https://openai.com/sitemap.xml/safety/`、`https://openai.com/sitemap.xml/company/`。探测记录还确认 robots 公布的 sitemap index 可取；本配置不直接请求 index。记录未提供 index 的精确 URL。
- Can fetch：Homepage 返回 HTTP 403；sitemap index 与上述四个子表均返回 HTTP 200。未将首页 403 作为绕过限制的理由。
- Title / URL / date / image：配置按 `/index/` 路径筛选 sitemap URL。探测记录指出文章页面结构化元数据可作为字段来源；当前解析器会尝试 Open Graph、JSON-LD 等页面元数据。各字段逐篇是否存在、日期覆盖率和图片覆盖率尚未由采集器验收。
- Pagination：sitemap 发现路径，无列表页页码参数；是否存在未探测的额外子表不作推断。
- Rate or anti-bot：首页 403 是已观察到的访问限制信号；robots 和 sitemap 可以访问。没有绕过 403，也没有测得服务端限速数值。
- Fallback：未配置自动回退。使用已可访问的 sitemap；没有把受限首页改写成其他访问路径。

## Anthropic

- Source：Anthropic（官方来源）。
- Homepage：`https://www.anthropic.com/news`。
- Chosen method：Sitemap。
- Actual endpoint：`https://www.anthropic.com/sitemap.xml`。
- Can fetch：Sitemap 返回 HTTP 200，共 544 个 URL，其中 262 个路径属于 `/news/`。`/news` 列表 HTML 返回 HTTP 200。
- Title / URL / date / image：URL 来自 sitemap 的文章路径；sitemap 的日期提示及文章页面元数据可供当前解析器使用。端点探测没有逐篇记录字段覆盖率；本机 live 采集解析到 2 条，health 确认标题、URL、日期可解析且存在图片候选，见下方验收表。
- Pagination：当前走 sitemap；列表 HTML 的分页形式和覆盖范围未确认，也没有纳入当前配置。
- Rate or anti-bot：已记录端点均返回 200；没有记录数值限速或拦截信号。采集时仍遵守 robots 和通用主机间隔。
- Fallback：`/news` HTML 是已探测的候选回退入口，但当前配置没有自动 fallback；该 HTML 路径的采集解析尚未验收。

## Google DeepMind

- Source：Google DeepMind（官方来源）。
- Homepage：`https://deepmind.google/blog/`。
- Chosen method：Sitemap。
- Actual endpoint：`https://deepmind.google/sitemap.xml`。
- Can fetch：Sitemap 返回 HTTP 200，共 738 个 URL，约 350 个为 blog 路径。`/blog/` 列表 HTML 返回 HTTP 200，探测到 25 个文章卡片。
- Title / URL / date / image：当前配置仅保留匹配文章路径的 sitemap URL；日期提示和文章页面元数据是当前解析器的候选字段来源。25 张卡片是否代表完整列表未确认；本机 live 采集解析到 1 条，health 确认标题、URL、日期可解析且存在图片候选，见下方验收表。
- Pagination：25 个卡片是一次列表页探测结果；是否有后续分页未确认。当前选用 sitemap，不依赖列表页翻页。
- Rate or anti-bot：已记录端点返回 200；没有已知服务端限速数值或反爬拦截信号。采集时遵守 robots 和通用主机间隔。
- Fallback：`/blog/` HTML 列表是候选回退入口，当前配置不自动切换到该入口，HTML 解析尚未验收。

## Google Blog / Google AI

- Source：Google AI / Google Blog - AI（官方来源）。
- Homepage：`https://blog.google/`。
- Chosen method：Sitemap。
- Actual endpoint：`https://blog.google/en-us/sitemap.xml`（当前配置直接使用英文 sitemap；探测阶段从 sitemap index 确认英文表）。
- Can fetch：英文 sitemap 返回 HTTP 200，共 11,699 个 URL；按 innovation-and-ai 路径筛选约有 1,593 个条目。`/feed` 返回 HTML，不是 RSS/Atom feed。
- Title / URL / date / image：URL 由 sitemap 提供，当前只保留匹配 `/innovation-and-ai/` 的路径；日期提示和文章页面元数据是解析器候选来源。标题、日期、图片字段的单篇读取及覆盖率未验收。
- Pagination：使用 sitemap，不依赖列表翻页；未记录该 sitemap 是否还有未配置的分页或子表。
- Rate or anti-bot：英文 sitemap HTTP 200；未记录限速或反爬信号。错误类型的 `/feed` 内容不作为 feed 解析；采集时遵守 robots 和通用主机间隔。
- Fallback：没有可用 feed fallback；`/feed` 已确认是 HTML，当前不作为 RSS 端点。未配置自动 HTML fallback。

## Meta AI

- Source：Meta AI（官方来源）。
- Homepage：`https://ai.meta.com/blog/`。
- Chosen method：HTML 列表页及文章页。
- Actual endpoint：列表 `https://ai.meta.com/blog/`；robots 列出的 sitemap 为 `https://ai.meta.com/sitemap/ai_meta_com_sitemap.xml.gz`，但当前不使用该 sitemap。
- Can fetch：`/blog/` 返回 HTTP 200。探测确认文章页面可读取 title 与 `og:image`。robots 列出的 gzip sitemap 返回 HTTP 403。
- Title / URL / date / image：已观察到文章页面 title 与 `og:image` 可读；URL 由列表中的文章链接发现。本机 live 采集解析到的列表条目均缺少可解析发布日期，且有图片候选；Health 因日期缺失返回 WARN，见下方验收表。
- Pagination：列表页分页/无限滚动情况未确认；当前 HTML collector 只从所配置的列表页提取链接，没有已记录的翻页端点。
- Rate or anti-bot：robots sitemap 返回 403；没有请求或解压绕过该拒绝。公开 HTML 页面可取；没有测得数值限速。
- Fallback：当前主方法就是公开 HTML。403 sitemap 不是可用 fallback，也没有自动重试或绕过路径。

## Microsoft Research

- Source：Microsoft Research（研究来源）。
- Homepage：`https://www.microsoft.com/en-us/research/`。
- Chosen method：RSS。
- Actual endpoint：`https://www.microsoft.com/en-us/research/feed/`，Homepage 声明该 URL 为 alternate RSS。
- Can fetch：Feed 返回 HTTP 200，记录到 10 个 entries。
- Title / URL / date / image：端点探测确认 entries 数量，未逐项记录字段；本机 live 采集解析到 3 条，health 确认标题、URL、日期可解析，7 天结果没有图片候选，见下方验收表。Feed parser 从 `published`/`updated` 取日期；图片仅在 feed 提供媒体项或 enclosure 时读取。
- Pagination：单一 feed 端点；分页或分页参数未确认，未配置翻页。
- Rate or anti-bot：Homepage 和 feed 的本次探测没有记录访问限制或数值限速。采集时遵守 robots 和通用主机间隔。
- Fallback：没有记录或配置 HTML fallback；当前 RSS/Atom feed 已通过本机 live 解析。

## NVIDIA Technical Blog

- Source：NVIDIA Technical Blog（官方来源）。
- Homepage：`https://developer.nvidia.com/blog/`。
- Chosen method：两个 sitemap endpoint 合并候选 URL，并由路径规则筛选 blog posts。
- Actual endpoint：`https://developer.nvidia.com/blog/sitemap-news.xml`（Google News sitemap）；`https://developer.nvidia.com/blog/wp-sitemap.xml`（WordPress sitemap，含 8 个子表）。robots 公布的 sitemap index 也已探测。
- Can fetch：robots sitemap index、WordPress blog sitemap 和 Google News sitemap 均返回 HTTP 200；Google News sitemap 当时有 2 个 entries。`/blog/` HTML 返回 HTTP 200。
- Title / URL / date / image：URL 来自两个 sitemap；Google News 项和 WordPress sitemap 中的日期提示可能用于候选排序/日期字段，文章页面元数据用于标题、日期和图片候选。本机 health 在 30 天窗口解析到 2 条，标题、URL、日期和图片候选均可用；WARN 仅表示 7 天窗口没有更新，见下方验收表。
- Pagination：WordPress sitemap 展开 8 个子表；采集器按 sitemap 子表读取，不依赖 HTML 列表页翻页。两组 sitemap 的文章重合情况尚待采集器去重验收。
- Rate or anti-bot：已记录端点返回 200；无数值限速或反爬信号记录。采集时遵守 robots 和通用主机间隔。
- Fallback：`/blog/` HTML 列表已探测可取，但当前配置使用上述两个 sitemap endpoint，没有配置自动 HTML fallback。

## Hugging Face Blog

- Source：Hugging Face Blog（官方来源）。
- Homepage：`https://huggingface.co/blog`。
- Chosen method：RSS。
- Actual endpoint：`https://huggingface.co/blog/feed.xml`；Homepage 声明该 alternate feed。
- Can fetch：RSS 返回 HTTP 200，记录到 872 个 entries。
- Title / URL / date / image：端点探测给出 entry 数量，没有逐项字段审计；本机 live 采集解析到 6 条，health 确认标题、URL、日期可解析，7 天结果没有图片候选，见下方验收表。图片仅在 feed 提供媒体项或 enclosure 时读取。
- Pagination：使用 feed 快照；分页方式、窗口和是否存在继续加载机制未确认，当前没有额外分页参数。
- Rate or anti-bot：本次探测未记录访问限制或数值限速。采集时遵守 robots 和通用主机间隔。
- Fallback：未记录或配置 HTML fallback；当前 RSS/Atom feed 已通过本机 live 解析。

## Mistral AI News

- Source：Mistral AI News（官方来源）。
- Homepage：`https://mistral.ai/news/`。
- Chosen method：RSS。
- Actual endpoint：`https://mistral.ai/news/rss`；Homepage 声明该 alternate feed。
- Can fetch：RSS 返回 HTTP 200，记录到 88 个 entries。
- Title / URL / date / image：端点探测给出 entry 数量，没有逐项字段审计；本机 live 采集解析到 1 条，health 确认标题、URL、日期可解析，7 天结果没有图片候选，见下方验收表。图片字段需 feed 提供图片媒体项或 enclosure。
- Pagination：使用 feed 快照；分页方式和条目窗口未确认，当前没有额外分页参数。
- Rate or anti-bot：本次探测未记录访问限制或数值限速。采集时遵守 robots 和通用主机间隔。
- Fallback：未记录或配置 HTML fallback；当前 RSS/Atom feed 已通过本机 live 解析。

## arXiv AI Research

- Source：arXiv AI Research（研究来源）。
- Homepage：`https://arxiv.org/`。
- Chosen method：官方 arXiv RSS 分类 feed，当前配置五个分类。
- Actual endpoint：`https://rss.arxiv.org/rss/cs.AI`、`https://rss.arxiv.org/rss/cs.CL`、`https://rss.arxiv.org/rss/cs.LG`、`https://rss.arxiv.org/rss/cs.CV`、`https://rss.arxiv.org/rss/cs.RO`。
- Can fetch：五个 feed 均返回 HTTP 200，内容为合法 RSS。2026-10-03 是周六，五个 feed 当时为空；feed 声明跳过周六和周日。`rss.arxiv.org/robots.txt` 返回 HTTP 404。classic API 所在 `arxiv.org` 的相关路径被 robots.txt disallow，因此没有请求该 API。
- Title / URL / date / image：因探测日 feeds 为空，没有条目可验证 title、URL、date 或 image。解析器对非空 feed 预期读取 title、link 或 id、published/updated；图片字段是否存在未确认，不假设 arXiv feed 提供文章图片。解析验收待有条目时执行。
- Pagination：五个分类 feed 分别读取后按 canonical URL 去重；未发现或配置额外分页参数。周末无条目符合 feed 的 skipDays 声明，不代表采集失败。
- Rate or anti-bot：RSS host robots endpoint 的 404 是未提供 robots 文件的探测结果；本机 fetcher 对 robots 404 按无规则文件处理。classic API 路径被 robots 明确禁止，未请求且未绕过。没有记录 RSS host 的数值限速。
- Fallback：没有 API fallback；该 API 路径受 robots 限制，因此明确不作为候选回退。当前来源依赖官方分类 RSS。

## 验收状态

### 本机采集器实测（2026-10-03）

使用仓库 `.venv` 中的 Python 3.13.5，执行 `python -m news_pipeline.cli collect --since-hours 168 --dry-run --limit 3`、`python -m news_pipeline.cli health`，随后执行两次 `python -m news_pipeline.cli collect --since-hours 168`（默认每源最多 20 条）。数据源按顺序访问，遵守 robots 规则和主机限速。

表中 7 天条目数、最新时间和图片候选来自首次持久化采集的解析结果（每源上限 20 条）；Health 列来自独立健康检查，该检查先看 7 天、无条目时扩到 30 天，每次每源最多检查 3 条。

| Source | Method | 7 天条目数 | Health | 最新时间（Asia/Shanghai） | 图片候选 |
|---|---|---:|---|---|---|
| OpenAI | Sitemap | 0 | WARN：30 天无符合配置的条目 | — | 否 |
| Anthropic | Sitemap | 2 | PASS | 2026-10-03 07:01 | 是 |
| Google DeepMind | Sitemap | 1 | PASS | 2026-09-30 23:00 | 是 |
| Google AI / Google Blog - AI | Sitemap | 9 | PASS | 2026-10-02 08:00 | 是 |
| Meta AI | HTML | 10 | WARN：条目没有可解析发布日期 | — | 是 |
| Microsoft Research | RSS/Atom | 3 | PASS | 2026-10-01 00:00 | 否 |
| NVIDIA Technical Blog | Sitemap | 0 | WARN：7 天无更新；30 天内 2 条，最新 2026-09-16 01:00 | — | 否 |
| Hugging Face Blog | RSS/Atom | 6 | PASS | 2026-10-02 23:19 | 否 |
| Mistral AI News | RSS/Atom | 1 | PASS | 2026-09-28 23:57 | 否 |
| arXiv AI Research | arXiv RSS | 0 | WARN：30 天窗口仍无条目；探测日为周六，feed 声明跳过周末 | — | 否 |

7 天持久化采集首次新增 **32 条**，10 个来源均未抛出采集异常；紧接着用相同参数再次运行，采集器解析到的条目数相同，新增数为 **0**。本机 inbox 和 `seen.jsonl` 各含 32 条，ID 均唯一。

修复重定向逐跳校验后，再次运行全量 7 天 dry-run（每源最多 3 条）和 `health`：10 个来源的 dry-run 均为 PASS，新增数为 0；health 为 6 个 PASS、4 个 WARN、0 个 FAIL。WARN 分别对应 30 天无条目（OpenAI、arXiv）、缺发布日期（Meta）和 7 天无更新但 30 天内有条目（NVIDIA）。

落盘审计覆盖统一 schema 的全部字段，校验 URL SHA-256 截断 ID、UTC `Z` 时间戳及摘要片段一致性：**0 项错误**。UTF-8 JSON 可解码；`content_text` 与来源摘要一致；没有保存全文、下载图片或写入 `_posts/`。图片候选缺失的来源仍正常通过采集。

### Jekyll strict build 门槛

仓库没有系统 Ruby/Bundler。已在忽略目录 `.venv/` 内准备 Ruby 3.4.11 与 MSYS2；Ruby 可执行并报告 `ruby 3.4.11`。本机 `bundle install --jobs 2 --retry 2` 在编译锁定的 `bigdecimal 4.1.3` 原生扩展时失败：MSYS2 GNU Make 启动的 `/bin/sh` 找不到 `rm`（`make: rm: No such file or directory`）。未改动 `Gemfile` 或 `Gemfile.lock`，没有全局安装 Ruby。由于依赖未安装完成，`bundle exec jekyll build --strict_front_matter` **未运行，构建验收仍未验证**。静态检查时 `_site/news_pipeline/` 与 `_site/tests/` 均不存在；这不能代替真实 Jekyll 构建验证。

Jekyll 的 `exclude` 已配置 `news_pipeline/` 和 `tests/`。Netlify Build 配置未修改。
