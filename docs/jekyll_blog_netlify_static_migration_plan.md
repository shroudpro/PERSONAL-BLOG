# jekyll-blog 纯前端化与 Netlify 部署改造技术方案

> 目标仓库：`ZGQ-inc/jekyll-blog`  
> 目标形态：只保留博客前端与 Jekyll 构建能力；本地修改、预览；通过 Git commit + push 同步到 GitHub；由 Netlify 自动构建并发布。  
> 适用执行者：可以扫描、修改本地仓库并执行命令的 Agent / Codex / 开发者。  
> 基线：基于当前仓库 `main` 分支结构制定。

## 1. 最终目标

改造完成后，系统只保留以下链路：

```text
本地编辑
  ↓
Jekyll 本地预览
  ↓
git commit
  ↓
git push origin main
  ↓
GitHub
  ↓
Netlify 自动检测 push
  ↓
bundle exec jekyll build
  ↓
_site
  ↓
Netlify CDN 发布
```

不再依赖：

- Cloudflare Pages
- Cloudflare Worker
- Cloudflare D1
- Cloudflare R2
- Wrangler
- Telegram Bot
- Telegram Webhook
- Telegram 评论联动
- GitHub Actions 中的 Worker 部署和 Telegram 通知任务

保留：

- Jekyll 页面生成
- Material Design 3 风格 UI
- 响应式布局
- 首页文章列表
- 公告 Banner
- 标签
- 分类
- 归档
- 动态页
- 友链页框架
- About 页面框架
- Fuse.js 前端搜索
- MathJax
- Mermaid
- Three.js 等纯浏览器渲染能力
- PWA
- Service Worker
- 深色模式和多主题色
- Markdown 文章
- SEO / Sitemap / RSS
- 代码高亮
- TOC
- 图片、音视频等静态资源
- 不依赖后端的 Jekyll 自定义插件

## 2. 改造原则

### 2.1 不重写前端

这次不要把项目迁移到 Next.js、Astro、Vue 或 React。现有项目的价值就在 `_layouts`、`_includes`、`_sass`、`assets/js` 和自定义 Jekyll 插件中。保持 Jekyll 可以最大程度保留现有视觉和交互效果，同时把维护复杂度降到最低。

### 2.2 删除后端，不做后端兼容层

不要为了“暂时不报错”而保留假的 Worker URL、假的 Telegram 配置或空的 Cloudflare 环境变量。所有前端中真正依赖这些服务的代码都应直接移除或改造成纯静态逻辑。

### 2.3 Netlify 构建必须可重复

生产构建不应依赖临时访问第三方网站获取内容。所有构建依赖应尽量固定版本；同一个 Git commit 应尽量得到相同的 `_site` 输出。

### 2.4 内容与主题分离

改造后把仓库理解成三层：

```text
内容层
  _posts
  about.html
  links.md
  updates.md
  assets/images 中的个人内容

主题层
  _layouts
  _includes
  _sass
  assets/js
  assets/css
  部分 _plugins

部署层
  Gemfile
  Gemfile.lock
  .ruby-version
  netlify.toml
  .gitignore
```

后续修改文章时尽量只动内容层；改 UI 时再动主题层；部署配置保持稳定。

## 3. 第一阶段：复制仓库并建立自己的 Git 历史

推荐不要长期直接使用原作者仓库作为 `origin`。

### 3.1 获取代码

```bash
git clone https://github.com/ZGQ-inc/jekyll-blog.git
cd jekyll-blog
```

### 3.2 新建自己的 GitHub 仓库

例如：

```text
your-github-name/blog
```

然后将远程仓库切换为自己的：

```bash
git remote rename origin upstream
git remote add origin https://github.com/your-github-name/blog.git
git remote -v
```

推荐保留 `upstream`，原因是未来如果原项目修复了主题 bug，可以人工比较并挑选 commit，而不是彻底失去上游参考。

### 3.3 创建改造分支

```bash
git checkout -b refactor/netlify-static
```

不要一上来直接在 `main` 大规模删文件。先完成本地构建和验收，再合并到 `main`。

## 4. 第二阶段：删除 Cloudflare 和 Telegram 后端

### 4.1 直接删除的目录和文件

删除：

```text
worker/
instantview/
.env.example
scripts/init-cloudflare.bat
scripts/init-cloudflare.sh
.github/workflows/deploy-worker.yml
.github/workflows/deploy.yml
```

原因：

- `worker/` 是 Cloudflare Worker + D1 + R2 + Telegram 后端。
- `instantview/` 是 Telegram Instant View 规则，与纯前端博客无关。
- `.env.example` 主要记录 Telegram、Cloudflare、Worker 相关变量。
- 两个初始化脚本只服务于 Cloudflare。
- 两个 GitHub Actions workflow 一个部署 Worker，一个通知 Telegram，都不应继续运行。

注意：`scripts/` 目录不要整体盲删。仓库还有 `scripts/generate_lqip.py`，是否保留由第 8 节决定。

### 4.2 清理 `_config.yml`

删除以下配置：

```yaml
comments:
  enabled: true
  app_id: "..."

worker_api_url: "..."

telegram_iv_rhash: "..."
```

如果你完全不用 Telegram，同时从 `social` 中删除：

```yaml
telegram:
telegram_channel:
```

保留 GitHub、RSS 和你真正需要的社交链接。

建议将 `_config.yml` 收敛成类似：

```yaml
title: "Your Blog"
description: "Your personal blog"
url: "https://your-domain.example"
baseurl: ""
lang: "zh-CN"
timezone: Asia/Shanghai

author:
  name: "Your Name"
  bio: "Your bio"
  avatar: "/assets/images/avatar.png"
  email: ""

nav_links:
  - title: "首页"
    url: "/"
    icon: "home"
  - title: "文章"
    url: "/posts/"
    icon: "article"
  - title: "标签"
    url: "/tags/"
    icon: "label"
  - title: "分类"
    url: "/categories/"
    icon: "folder"
  - title: "归档"
    url: "/archives/"
    icon: "inventory_2"
  - title: "动态"
    url: "/updates/"
    icon: "dynamic_feed"
  - title: "友链"
    url: "/links/"
    icon: "link"
  - title: "关于"
    url: "/about/"
    icon: "info"

social:
  github: "your-github-name"
  rss: true

markdown: kramdown
highlighter: rouge
future: true

kramdown:
  input: GFM
  hard_wrap: false
  syntax_highlighter: rouge
  syntax_highlighter_opts:
    block:
      line_numbers: true

permalink: /posts/:slug/

plugins:
  - jekyll-feed
  - jekyll-sitemap
  - jekyll-seo-tag

exclude:
  - Gemfile
  - Gemfile.lock
  - vendor/
  - README.md
  - node_modules/
```

`url` 在使用 Netlify 默认域名期间可以设置为：

```yaml
url: "https://your-site.netlify.app"
```

以后绑定自定义域名后再改成正式域名。

## 5. 第三阶段：彻底解除文章页与 Telegram 的耦合

这是整个改造里最重要的一处。

当前 `_layouts/post.html` 包含：

- Telegram Instant View 分享链接
- “分享到 Telegram”逻辑
- Telegram 频道讨论按钮
- `site.worker_api_url`
- `site.social.telegram_channel`
- 请求 `/api/posts/:id/tg`
- 请求评论数据
- 动态注入 `telegram-widget.js`
- Telegram 官方评论 iframe
- 评论刷新逻辑

### 5.1 推荐处理方式

直接删除 Telegram 专用区域，不要留空变量。

应删除或重写大约从以下语义块开始的代码：

```text
Telegram Channel Discussion Button
Fetch TG message ID
Telegram Official Comments Section
```

并删除依赖：

```liquid
site.worker_api_url
site.social.telegram_channel
site.telegram_iv_rhash
```

### 5.2 分享按钮改成通用分享

如果想保留“分享”功能，建议改成浏览器 Web Share API（网页分享接口）：

```html
<button id="shareBtn" type="button">
  <span class="material-symbols-outlined">share</span>
  分享
</button>

<script>
document.getElementById('shareBtn')?.addEventListener('click', async () => {
  const data = {
    title: document.title,
    text: document.querySelector('meta[name="description"]')?.content || '',
    url: location.href
  };

  if (navigator.share) {
    await navigator.share(data);
  } else {
    await navigator.clipboard.writeText(location.href);
  }
});
</script>
```

这样不会依赖任何后端。

### 5.3 评论的第一阶段建议

第一阶段完全关闭评论。

理由不是“评论不重要”，而是迁移过程中应该先确认：

```text
主题正常
文章正常
搜索正常
PWA 正常
Netlify 正常
```

再增加新的评论系统。

如果后续确实需要评论，优先选择 Giscus（基于 GitHub Discussions 的评论系统），因为它仍符合“无自建后端”的目标。

## 6. 第四阶段：清理作者硬编码

全仓库执行文本搜索：

```text
ZGQ
ZGQ-inc
ZGQinc
zgqinc
zgqinc.gq
blog.zgqinc.gq
api.zgqinc.gq
assets.zgqinc.gq
domain.zgqinc.gq
CopyRightZGQInc
Cloudflare
Telegram
telegram
WORKER_API_URL
worker_api_url
TELEGRAM_
CF_
wrangler
```

不要只搜索 `_config.yml`。

### 6.1 `_includes/head.html`

需要修改：

```text
Theme: ZGQ Inc's Jekyll Blog Theme
Author: ZGQ Inc.
Contact: ...
Repository: ...
```

许可证注释可以保留原作者署名，不要伪装成自己原创。建议改成：

```html
<!--
  Based on ZGQ Inc's Jekyll Blog Theme
  Original repository: https://github.com/ZGQ-inc/jekyll-blog
  License: MIT
  Customized for this site.
-->
```

同时把浏览器本地存储键：

```javascript
zgq-blog-theme
```

改成：

```javascript
personal-blog-theme
```

这样彻底去掉品牌耦合。

### 6.2 `_layouts/default.html`

当前页脚写死：

```text
Hosted on Cloudflare Pages
```

改成 Netlify，或者更推荐做成与平台无关：

```html
<p>
  © {{ site.time | date: "%Y" }} {{ site.author.name }}
  · Built with Jekyll
</p>
```

平台无关的页脚未来迁移托管商时不用再改。

### 6.3 `about.html`

当前文件包含原作者：

- 导航域名
- Telegram 链接
- Cloudflare Pages 描述
- Worker + D1 + R2 描述
- GitHub Actions + Telegram Bot 描述

建议不要逐行替换，而是保留布局，重写内容。

新的“关于本站”技术栈应描述为：

```text
Jekyll
Material Design 3
GitHub
Netlify
```

不要再出现 Worker、D1、R2、Wrangler 或 Telegram 自动发布。

### 6.4 `links.md`

原文件包含大量原作者友链和 Telegram 群组数据。

推荐：

- 保留 Front Matter（页面头部元数据）结构和页面布局格式。
- 删除全部原作者友链条目。
- 添加自己的测试友链一条。
- 后续自行维护。

### 6.5 `updates.md`

布局 `_layouts/updates.html` 本身是纯静态的，可以保留。

只清掉原作者时间线，替换成你的记录，例如：

```yaml
updates:
  - date: "2026年10月"
    content: "博客迁移到 Netlify，完成纯静态化。"
```

## 7. 第五阶段：处理原作者文章和媒体

### 7.1 `_posts`

推荐删除原作者全部文章。

不要保留多年文章再“以后慢慢删”，因为这些文章中有大量：

- 原作者身份信息
- 原作者 Telegram 分类
- 原作者外链
- 原作者 R2 资源链接
- 与原作者内容绑定的标签和分类
- 可能不属于程序 MIT License 范围的文章和媒体内容

可以临时保留 `2026-07-31-demo.md` 作为语法参考，但建议：

1. 复制成 `docs/markdown-demo-reference.md`。
2. 删除原文章中的作者特定内容。
3. 正式上线前不要把演示文章作为公开文章。

### 7.2 `assets/images`

不要直接整个删除，因为主题需要：

```text
avatar.png
Logo
PWA icon
页面 UI 使用的静态资源
```

正确流程：

1. 扫描所有 HTML、Liquid、SCSS、JS 对图片文件的引用。
2. 建立 `used_assets` 集合。
3. 删除没有引用且明显属于原作者文章的图片。
4. 替换头像、Logo、favicon。
5. 再执行一次 broken reference（失效引用）扫描。

### 7.3 音频和视频

如果：

```text
assets/audios/
assets/videos/
```

只是原作者文章媒体，建议删除内容，只保留空目录所需的 `.gitkeep`，或者直接删除目录。

## 8. 第六阶段：精简 `_plugins`

当前自定义插件建议按下面处理。

| 插件 | 建议 | 原因 |
| --- | --- | --- |
| `any_name_posts.rb` | 可删除 | 标准化文章命名后不需要允许任意文件名 |
| `custom_size.rb` | 保留 | 纯构建期文本转换，无网络依赖 |
| `github_alerts.rb` | 保留 | 支持 GitHub 风格 NOTE/TIP/WARNING |
| `image_lqip.rb` | 建议重构 | 当前会依赖 `scripts/generate_lqip.py` 和 `_data/lqip.json` |
| `link_preview.rb` | 第一阶段删除 | 构建时会主动请求第三方网页，不利于 Netlify 稳定构建 |
| `post_id.rb` | 可保留 | 如果希望文章之间通过自定义 ID 互链，很实用 |
| `telegram_spoiler.rb` | 重命名后保留 | 本质只是 `||文本||` 剧透语法，不依赖 Telegram |
| `timezone_utc8.rb` | 保留或简化 | 如果文章时间统一使用 UTC+8，可继续用 |

### 8.1 `any_name_posts.rb`

建议制定统一文章命名：

```text
YYYY-MM-DD-slug.md
```

例如：

```text
2026-10-03-first-post.md
```

然后删除 `any_name_posts.rb`。

这样更符合标准 Jekyll 行为，减少隐式逻辑。

### 8.2 `link_preview.rb`

建议第一版直接删除。

它会在构建阶段访问：

- 普通网页 Open Graph
- Pixiv
- e621 / e926
- 其他第三方 URL

这会导致：

- Netlify 构建受外网状态影响
- 构建时间变长
- 第三方限流时输出变化
- 同一 commit 的生成结果不完全稳定

保留 `_sass/components/_link_card.scss` 没问题，它只是样式。

以后如果需要链接卡片，推荐：

- 手写 Front Matter 数据
- 或本地脚本预生成 metadata 后提交到 Git
- 不要在 Netlify 生产构建阶段动态抓取

### 8.3 `image_lqip.rb`

这里有两个逻辑：

1. LQIP（低质量图片占位符）生成与读取。
2. 自动给文章图片添加 `loading="lazy"` 和 `decoding="async"`。

建议拆分。

第一阶段可以删除 LQIP 生成逻辑，但保留 lazy loading。

新建：

```text
_plugins/image_lazy.rb
```

只保留文章图片懒加载相关 hook。

这样就可以删除：

```text
_data/lqip.json
scripts/generate_lqip.py
_plugins/image_lqip.rb
```

以后如果确实想恢复 LQIP，再作为独立前端性能优化任务做。

### 8.4 `telegram_spoiler.rb`

虽然名字带 Telegram，但代码没有任何 Telegram API 依赖。

建议：

```text
telegram_spoiler.rb
↓
spoiler.rb
```

内部注释同步改成通用名称。

继续支持：

```text
||这里是剧透||
```

这种语法。

### 8.5 `timezone_utc8.rb`

如果你希望博客统一显示东八区时间，可以保留。

如果希望尽量减少自定义插件，也可以后续验证仅依赖：

```yaml
timezone: Asia/Shanghai
```

是否已经满足要求，再决定删除。

第一阶段不要同时改太多日期逻辑，建议先保留。

## 9. 第七阶段：整理 Gem 依赖

当前 `Gemfile` 应继续保留：

```ruby
gem "jekyll", "~> 4.3"

group :jekyll_plugins do
  gem "jekyll-feed", "~> 0.17"
  gem "jekyll-sitemap"
  gem "jekyll-seo-tag", "~> 2.8"
end

gem "rouge", "~> 4.2"
gem "kramdown-parser-gfm"
gem "nokogiri"
```

`nokogiri` 仍被 `github_alerts.rb` 使用，所以不要因为删除 `link_preview.rb` 就顺手删掉。

### 9.1 生成 `Gemfile.lock`

本地执行：

```bash
bundle install
```

然后必须提交：

```text
Gemfile.lock
```

目的：固定依赖解析结果，让本地和 Netlify 尽可能一致。

### 9.2 固定 Ruby 版本

在本地选择一个能够成功完成：

```bash
bundle exec jekyll build --strict_front_matter
```

的 Ruby 版本。

然后根目录新增：

```text
.ruby-version
```

内容示例：

```text
3.3.0
```

这里的版本号不要机械照抄示例，应该填写你本地已经验证成功的版本。

## 10. 第八阶段：新增 Netlify 配置

根目录新增：

```text
netlify.toml
```

推荐内容：

```toml
[build]
  command = "bundle exec jekyll build --strict_front_matter"
  publish = "_site"

[build.environment]
  JEKYLL_ENV = "production"
```

不要把 `_site` 提交到 GitHub。

Netlify 应该自己根据源码构建 `_site`。

### 10.1 `.gitignore`

确认至少包含：

```gitignore
_site/
.sass-cache/
.jekyll-cache/
.jekyll-metadata
.bundle/
vendor/
```

如果本地使用 IDE 或操作系统生成其他缓存，再按需追加。

## 11. 第九阶段：PWA 和 Service Worker 品牌清理

### 11.1 `manifest.json`

修改：

```json
{
  "name": "Your Blog",
  "short_name": "Your Blog",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#FDFCFF",
  "theme_color": "#FDFCFF",
  "icons": [
    {
      "src": "/logo.png",
      "sizes": "192x192 512x512",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/logo-monochrome.png",
      "sizes": "192x192 512x512",
      "type": "image/png",
      "purpose": "monochrome"
    }
  ]
}
```

### 11.2 `sw.js`

把：

```javascript
zgq-blog-cache
```

改成自己的命名，例如：

```javascript
personal-blog-cache
```

现有缓存策略可以第一阶段保留。

### 11.3 必须替换的品牌资源

替换：

```text
favicon.ico
logo.png
logo-monochrome.png
assets/images/avatar.png
```

同时检查 PNG 实际尺寸是否和 `manifest.json` 声明一致。当前 manifest 把同一个文件声明为兼容 192 和 512，最好实际准备标准 PWA 图标。

## 12. 第十阶段：重建个人内容

建议第一版至少准备以下内容：

```text
_posts/2026-10-03-hello-world.md
about.html
links.md
updates.md
```

测试文章 Front Matter：

```yaml
---
layout: post
title: "Hello World"
date: 2026-10-03 18:00:00
summary: "博客迁移后的第一篇测试文章。"
categories: [随笔]
tags: [Jekyll, Blog]
toc: true
---
```

正文应覆盖以下测试项目：

- H1 到 H4 标题
- 普通段落
- 加粗
- 行内代码
- fenced code block（围栏代码块）
- 引用
- GitHub Alert
- 图片
- 外链
- 内链
- Markdown 表格
- 数学公式
- Mermaid
- 剧透语法
- TOC

不要只用一篇只有两段文字的 Hello World 做验收，否则很多主题功能实际上没有被测试。

## 13. 本地开发流程

推荐在 WSL2 或原生 Ruby 环境中开发。

首次：

```bash
bundle install
bundle exec jekyll serve --livereload
```

访问：

```text
http://127.0.0.1:4000
```

正式提交前必须执行：

```bash
bundle exec jekyll build --strict_front_matter
```

只有构建通过才允许 commit。

推荐再加一个简单检查脚本，例如：

```text
scripts/check.sh
```

执行：

```bash
bundle exec jekyll build --strict_front_matter
```

再扫描生成页面中的：

```text
zgqinc
api.zgqinc.gq
assets.zgqinc.gq
Cloudflare Worker
Telegram 频道
```

一旦发现旧品牌或旧后端引用就失败。

## 14. Git 提交流程

建议将改造拆成多个 commit，不要一个 commit 删除几千个文件再同时重写 UI。

推荐顺序：

```text
chore: remove cloudflare worker and telegram automation

refactor: remove telegram discussion integration

chore: remove original posts and media

refactor: simplify jekyll plugins for static build

chore: add ruby lockfile and netlify config

feat: personalize site metadata and branding

content: add initial personal pages and first post
```

好处：

- 出问题容易定位。
- 可以逐 commit 回退。
- 以后查看历史能知道哪些是上游代码，哪些是自己的改造。

## 15. Netlify 首次部署

### 15.1 推送 GitHub

改造分支本地通过后：

```bash
git add .
git commit -m "refactor: convert blog to static netlify deployment"
git push -u origin refactor/netlify-static
```

可以先让 Netlify 用 branch deploy（分支部署）测试。

确认无误后再合并：

```bash
git checkout main
git merge refactor/netlify-static
git push origin main
```

### 15.2 Netlify 配置

在 Netlify 中：

```text
Add new project
→ Import an existing project
→ GitHub
→ 选择自己的 blog 仓库
```

生产分支：

```text
main
```

由于仓库已有 `netlify.toml`，应自动识别：

```text
Build command:
bundle exec jekyll build --strict_front_matter

Publish directory:
_site
```

第一阶段不要配置任何：

```text
CF_API_TOKEN
CF_ACCOUNT_ID
WORKER_API_URL
TELEGRAM_BOT_TOKEN
NOTIFY_SECRET
WEBHOOK_SECRET
```

如果 Netlify 项目里出现这些变量，说明迁移还没有真正完成。

## 16. 以后日常更新流程

以后写博客的常规流程应固定为：

```bash
git pull
```

编辑：

```text
_posts/YYYY-MM-DD-slug.md
```

本地预览：

```bash
bundle exec jekyll serve --livereload
```

正式检查：

```bash
bundle exec jekyll build --strict_front_matter
```

提交：

```bash
git add .
git commit -m "post: add xxx"
git push
```

之后：

```text
GitHub 收到 push
↓
Netlify 自动构建
↓
构建成功
↓
新版本上线
```

你不需要登录 Netlify 手动 Deploy。

## 17. 不推荐的做法

### 17.1 不要把 `_site` 提交到 GitHub

`_site` 是构建产物，不是源代码。

### 17.2 不要保留 Worker 代码“以后可能会用”

如果未来要增加动态能力，可以重新建立独立后端。现在保留只会增加认知负担和安全配置风险。

### 17.3 不要继续使用原作者 Worker URL

尤其不能让你自己的页面请求：

```text
api.zgqinc.gq
```

否则你的网站功能依赖于别人控制的服务。

### 17.4 不要只替换站名

必须进行全仓库硬编码扫描，否则 About、PWA、页脚、文章模板、历史内容里仍会残留作者信息。

### 17.5 不要让生产构建动态抓第三方元数据

因此第一阶段应删除 `link_preview.rb`。

### 17.6 不要一次性重写整个主题

先完成“架构脱钩”，再做视觉个性化。否则遇到问题时无法判断是迁移问题还是 UI 修改造成的问题。

## 18. 推荐的最终目录

```text
blog/
├── .gitignore
├── .ruby-version
├── Gemfile
├── Gemfile.lock
├── LICENSE
├── README.md
├── _config.yml
├── netlify.toml
│
├── _data/
│
├── _includes/
│   ├── banner-carousel.html
│   ├── bottom-island.html
│   ├── calendar-dialog.html
│   ├── embed.html
│   ├── head.html
│   ├── post-list.html
│   ├── pwa.html
│   └── sidebar.html
│
├── _layouts/
│   ├── default.html
│   ├── links.html
│   ├── post.html
│   └── updates.html
│
├── _plugins/
│   ├── custom_size.rb
│   ├── github_alerts.rb
│   ├── image_lazy.rb
│   ├── post_id.rb
│   ├── spoiler.rb
│   └── timezone_utc8.rb
│
├── _posts/
│   └── 2026-10-03-hello-world.md
│
├── _sass/
│
├── assets/
│   ├── css/
│   ├── images/
│   └── js/
│
├── 404.html
├── about.html
├── archives.html
├── categories.html
├── favicon.ico
├── index.html
├── links.md
├── logo-monochrome.png
├── logo.png
├── manifest.json
├── offline.html
├── posts.html
├── search.json
├── sw.js
├── tags.html
└── updates.md
```

注意：这里是目标结构，不要求机械删除未列出的每个 include。Agent 应先做引用扫描；某个 `_includes` 文件只要仍被模板引用，就应保留。

## 19. Agent 执行顺序

给本地 Agent 时，要求严格按以下顺序：

1. 创建新分支。
2. 保存当前可构建基线。
3. 删除 Cloudflare / Telegram 后端文件。
4. 修改 `_config.yml`。
5. 重构 `_layouts/post.html`，彻底移除 Worker / Telegram 评论依赖。
6. 清理 `default.html`、`head.html`、`about.html`。
7. 清空原作者文章和友链内容。
8. 清理原作者媒体。
9. 精简 `_plugins`。
10. 生成 `Gemfile.lock`。
11. 固定 `.ruby-version`。
12. 创建 `netlify.toml`。
13. 替换 Logo、favicon、avatar、PWA 名称。
14. 创建完整功能测试文章。
15. 执行本地构建。
16. 全仓库搜索旧域名和旧品牌。
17. 检查 `_site` 中是否还有旧域名或后端请求。
18. 本地浏览器人工验收。
19. 推送 GitHub 分支。
20. Netlify Branch Deploy 验收。
21. 合并到 `main`。
22. 验证 `main` push 能自动触发 Production Deploy（生产部署）。

## 20. 必须完成的自动扫描

改造结束后执行全文搜索。

### 20.1 源码扫描

源码中不应再出现：

```text
api.zgqinc.gq
assets.zgqinc.gq
blog.zgqinc.gq
domain.zgqinc.gq
worker_api_url
WORKER_API_URL
TELEGRAM_BOT_TOKEN
WEBHOOK_SECRET
NOTIFY_SECRET
CF_API_TOKEN
CF_ACCOUNT_ID
wrangler deploy
```

`ZGQ Inc` 可以只在 MIT 许可证、原主题归属说明中保留。

### 20.2 构建产物扫描

构建完成后扫描 `_site`。

不应存在：

```text
api.zgqinc.gq
worker_api_url
telegram-widget.js
Cloudflare Worker
```

如果仍然存在，说明还有模板耦合没有拆干净。

## 21. 功能验收矩阵

| 项目 | 验收要求 |
| --- | --- |
| 首页 | 正常展示最新文章 |
| 公告 | 有公告时 Banner 正常，无公告时不报错 |
| 文章 | 正文、图片、代码、表格正常 |
| TOC | 桌面端和移动端正常 |
| 标签 | 标签页能列出文章 |
| 分类 | 分类页正常 |
| 归档 | archive 逻辑正常 |
| 搜索 | Fuse.js 搜索能找到标题和正文 |
| 主题 | 深色、浅色、主题色切换正常 |
| 本地存储 | 主题配置刷新后保留 |
| PWA | manifest 可加载 |
| Service Worker | HTTPS 下注册成功 |
| 404 | Netlify 访问不存在地址时行为正常 |
| SEO | canonical、Open Graph、SEO tag 正常 |
| RSS | feed.xml 可生成 |
| Sitemap | sitemap.xml 可生成 |
| GitHub Alert | NOTE/TIP/WARNING 正常渲染 |
| 数学公式 | MathJax 正常 |
| Mermaid | 图表正常 |
| 图片 | 本地静态图正常，无旧图床依赖 |
| 手机端 | 侧边栏、导航、正文宽度正常 |
| 构建 | `bundle exec jekyll build --strict_front_matter` 无错误 |
| Netlify | push `main` 后自动上线 |
| 后端脱钩 | 浏览器 Network 不请求原 Worker |

## 22. 回归风险

### 风险 A：删掉 `link_preview.rb` 后旧文章无法构建

如果旧文章仍大量依赖链接预览语法，这是因为原作者内容没有清理干净。不要为了兼容原文章重新引入插件，优先清理旧文章。

### 风险 B：删除 LQIP 后部分模板引用 `image_lqip`

执行全文搜索：

```text
image_lqip
site.data.lqip
```

如果模板里有依赖，先做空值兼容或一起删掉对应占位逻辑。

### 风险 C：Netlify Ruby 与本地 Ruby 不一致

用 `.ruby-version` 固定，并提交 `Gemfile.lock`。

### 风险 D：PWA 缓存旧版本

改造期间可能出现 Service Worker 继续缓存旧 CSS/JS 的假象。测试时应：

- DevTools → Application → Service Workers
- Unregister
- Clear site data
- 强制刷新

不要把缓存问题误判成代码没有生效。

### 风险 E：根路径和自定义域名

当前 `baseurl: ""` 适合部署在域名根路径，例如：

```text
https://xxx.netlify.app/
https://blog.example.com/
```

不要把站点部署到 `/blog/` 子路径后仍保持该配置。

## 23. 推荐实施范围

### 第一阶段：必须完成

- 删除 Cloudflare / Telegram 后端。
- 清理文章模板中的 Worker 和 Telegram。
- 删除原作者内容。
- 修改站点信息。
- 固定 Ruby 和 Gems。
- 增加 Netlify 配置。
- GitHub → Netlify 自动部署跑通。

### 第二阶段：个性化

- 修改主题色。
- 修改 Logo。
- 修改首页布局。
- 重写 About。
- 重写友链。
- 调整字体。
- 调整文章卡片。
- 调整导航。
- 添加自己的页脚和社交链接。

### 第三阶段：可选增强

- Giscus 评论。
- 自定义域名。
- Netlify Analytics 或其他统计。
- 图片 CDN。
- 本地链接卡片预生成器。
- 自动压缩图片。
- Lighthouse 性能优化。
- GitHub Actions 做只读 CI 检查，但不负责部署。

## 24. 推荐最终架构

```text
Local
  │
  ├─ Markdown
  ├─ HTML / Liquid
  ├─ SCSS
  └─ JavaScript
  │
  ▼
Jekyll
  │
  ▼
Git
  │
  ▼
GitHub main
  │
  ▼
Netlify Build
  │
  ├─ Ruby
  ├─ Bundler
  └─ Jekyll
  │
  ▼
_site
  │
  ▼
Netlify CDN
```

没有应用服务器，没有数据库，没有容器，没有长期运行进程。

## 25. 完成定义

只有同时满足以下条件，才算迁移完成：

- 本地 `bundle exec jekyll build --strict_front_matter` 成功。
- 本地 `bundle exec jekyll serve` 页面功能正常。
- 源码中没有原作者 Worker / Cloudflare 私有配置。
- `_site` 中没有对 `api.zgqinc.gq` 的请求。
- 原作者文章、友链和个人媒体已清理。
- 主题 attribution（归属说明）和 MIT License 保留。
- `Gemfile.lock` 已提交。
- `.ruby-version` 已提交。
- `netlify.toml` 已提交。
- `_site` 未提交。
- GitHub `main` 每次 push 后 Netlify 自动触发新部署。
- 新文章只需本地编辑、commit、push 即可上线。

## 26. 给 Agent 的核心任务描述

可以把下面这段直接作为本地 Agent 的总任务：

```text
将当前 ZGQ-inc/jekyll-blog 项目改造成纯静态 Jekyll 个人博客。保留现有 Material Design 3 前端、布局、SCSS、JavaScript、搜索、标签、分类、归档、PWA、Service Worker、MathJax、Mermaid、代码高亮和其他不依赖后端的 UI 功能。彻底删除 Cloudflare Worker、D1、R2、Wrangler、Telegram Bot、Telegram Webhook、Telegram 评论和 GitHub Actions 中与上述服务有关的自动化。清理所有原作者文章、友链、个人媒体、域名和配置，但保留 MIT License 和合理的原主题归属说明。精简 Jekyll 自定义插件，删除生产构建时主动访问第三方网站的 link_preview 插件，将 telegram_spoiler 重命名为通用 spoiler；将 image_lqip 拆成不依赖 Python 和缓存文件的纯图片 lazy-loading 插件。固定 Ruby 和 Gem 依赖，生成 Gemfile.lock、.ruby-version 和 netlify.toml。最终要求本地通过 bundle exec jekyll build --strict_front_matter，并实现 GitHub main push 后由 Netlify 自动构建 _site 并发布。不要提交 _site，不要新增服务器、数据库或容器。
```
