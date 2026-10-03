# HANDOFF：PERSONAL-BLOG 的 Jekyll / Netlify 静态化

更新时间：2026-10-03（Asia/Shanghai）

## 1. 项目目标与边界

这是一个基于 Jekyll 和 Material Design 3 主题的个人博客。目标是把它整理成可由 GitHub 持续部署到 Netlify 的静态站点，移除 Cloudflare Worker 等后端基础设施，关闭 Telegram 评论与通知集成，并保留静态前端功能（搜索、标签、分类、归档、主题切换、PWA、RSS、Sitemap、代码高亮、数学公式、Mermaid 等）。

用户明确要求：

- 项目/站点使用中性名称 PERSONAL-BLOG。
- 项目只用 Netlify，清理 Cloudflare 基础设施文件。
- 优化 .gitignore，但 Gemfile.lock 必须可被 Git 跟踪，以便 Netlify 使用锁定依赖。
- 用户选择“不用隔离”；后续不要自行创建 worktree。
- 之前的实施约束是只改本地、不推送、不合并、不操作 Netlify 账号。
- 用户授权删除的 Cloudflare/Worker 文件仅限下文列出的 11 个路径。其他历史文章、图片、赞助页面、Telegram Instant View 文件尚未获单独确认。
- 用户最后询问了 Netlify Build settings 的填写方式；目前没有证据表明 Netlify 已完成首次部署。

执行方案的来源是仓库根目录迁移计划及用户“PLEASE IMPLEMENT THIS PLAN”的请求。文档中的清理建议仍需遵守用户提供的 AGENTS 规则：批量删除前列出精确路径并取得确认；媒体文件须先确认无引用。MIT 许可证和原主题归属说明必须保留。文章中出现 Cloudflare 或 Telegram 字样不等于运行时集成，不能只凭全文搜索就删文章。

## 2. Git 与工作区现状

本次核对时：

- 当前分支：codex/netlify-static。
- HEAD：be73b57（提交说明 UPDATE）。
- HEAD 与 origin/codex/netlify-static 指向同一提交；origin/main 为 88eda8c（first commit）。
- 这与先前“只在本地、不推送”的约束存在表面冲突：Git 目前显示该分支提交已在远端跟踪分支上。不要据此继续推送、合并、重置或改写历史；如需处理远端状态，先向用户说明并确认。
- 本次核对时，工作区还显示：
  - 删除：jekyll_blog_netlify_static_migration_plan.md（根目录的已跟踪文件）
  - 未跟踪：docs/PERSONALIZATION_BRIEF.md
  - 未跟踪：docs/jekyll_blog_netlify_static_migration_plan.md
- 上述删除和未跟踪文件可能是用户正在整理/移动的资料。必须按当前状态保留，不要运行 git clean、checkout、restore、reset 等会覆盖或移除它们的命令。先比较内容并问清楚再处理。
- HANDOFF.md 是本次新建文件；_config.yml 仅增加了 HANDOFF.md 到 Jekyll exclude，避免交接内容发布到博客。
- Gemfile.lock 存在且已被 Git 跟踪。物理存在的 .bundle/、vendor/ 目录已由 .gitignore 排除；不要顺手删除。
- 本仓库没有检测到 Ruby、Bundler 或 Jekyll 命令；严格构建尚未验证。

## 3. 已完成

### Cloudflare / Worker 后端文件

用户确认后，分支提交中已删除以下 11 个路径：

- .env.example
- .github/workflows/deploy-worker.yml
- .github/workflows/deploy.yml（原 Telegram 通知流程）
- scripts/init-cloudflare.bat
- scripts/init-cloudflare.sh
- worker/package-lock.json
- worker/package.json
- worker/schema.sql
- worker/src/index.ts
- worker/tsconfig.json
- worker/wrangler.toml

当前 Git 相对 origin/main 的差异确认这 11 个路径均为删除状态。

### Netlify 与站点基础配置

- netlify.toml 的构建命令为 **bundle exec jekyll build --strict_front_matter**，发布目录为 **_site**，生产环境变量为 **JEKYLL_ENV=production**。
- .ruby-version 固定为 **3.4.11**。
- Gemfile.lock 已跟踪；.gitignore 注释明确保留它。
- .gitignore 忽略 Jekyll 构建输出、Netlify CLI 状态、Bundler/vendor 本地目录、密钥、本地缓存、Node/Python 缓存、编辑器和操作系统文件、日志与临时文件。
- _config.yml 的站点标题/描述、作者、README、About、manifest 和示例文章等已部分换成 PERSONAL-BLOG / 通用占位信息。
- .gitignore 和站点元数据的变更已包含在 be73b57 中。

### 文章分享

_layouts/post.html 当前已使用通用分享和复制链接按钮。该模板扫描中没有发现 Worker API 请求或 Telegram 评论脚本；但这还不等于完成了整个源码和生成站点的全量验收。

## 4. 尚未完成 / 已知遗留

迁移不能视为完成，也不能声称构建或页面验收通过。

### 旧集成与代码

源码中仍能看到：

- _includes/telegram.html：Telegram 帖子嵌入 iframe 和 Telegram 链接。它是内容嵌入，不应与 Telegram 评论脚本混为一谈。
- _plugins/telegram_spoiler.rb：Telegram 命名的剧透插件仍在；计划要求确认并统一到通用实现。
- _plugins/spoiler.rb 与 telegram_spoiler.rb 同时存在，需要先比对用途与文章语法，避免删错或破坏剧透渲染。
- _plugins/link_preview.rb：仍会在构建时请求 Pixiv、e621 等第三方预览数据；旧网络请求和缓存逻辑尚未移除。
- _plugins/image_lqip.rb、scripts/generate_lqip.py：LQIP 生成逻辑仍在；按方案应移除生成流程，同时保留并验证图片懒加载。
- _includes/head.html 仍含原仓库链接 https://github.com/ZGQ-inc/jekyll-blog。这是原主题归属说明的一部分；按方案保留 MIT 和原作者/主题归属，不要为清除旧字符串而删掉许可说明。可核对链接是否应改成原主题的规范仓库地址，但不可删掉归属。
- _includes/telegram.html 和历史文章里出现 Telegram，不能仅按关键字批量删除。

### 内容和文件清理尚未批准

- _posts/ 中仍有大量原作者历史文章；其中有 Telegram 分类/内容，也有把 Cloudflare 当作文章主题讨论的文字。
- instantview/ 仍包含 Telegram Instant View 规则和说明。
- sponsor/ 仍有赞助页面。
- 友链、动态、图片和媒体尚未完成逐项引用审查与清理。
- 用户明确确认的只有上述 11 个 Cloudflare/Worker 文件。对其他批量删除，先形成精确路径清单并请求确认；删除媒体前先扫描引用。
- 扫描命中文章内容、主题归属或迁移计划时，先区分“历史文字/许可说明”与“运行时集成”，不能直接全局替换或删除。

### 构建与验收

- 在当前环境执行命令检测时，ruby、bundle、jekyll 均未找到。
- Gemfile.lock 已存在并受 Git 跟踪，但不能据此声称依赖已在本机安装或构建可用。
- 目前没有严格 Front Matter 构建成功证据，没有生成并审查 _site，也没有完成浏览器功能验收。
- 应尝试在工作区可控范围内准备 Ruby 3.4.11/Bundler；不得全局安装。若网络或权限阻止，记录具体错误并停止，不要伪称验证通过。
- _config.yml 的 url 仍是 https://your-site.netlify.app 占位域名。用户应在取得实际 Netlify 域名后更新，并重新构建。
- 全文搜索 Cloudflare/Telegram 会命中迁移文档和文章内容；验收需针对运行时代码、模板和生成文件做范围化扫描，并对剩余历史文字做人工分类。

## 5. Netlify 页面进度

用户提供的 Build settings 截图中：

- Branch to deploy：codex/netlify-static
- Base directory：空白
- Build command：bundle exec jekyll build --strict_front_matter
- Publish directory：_site
- Functions directory：netlify/functions（默认值）
- Git repository：PERSONAL-BLOG
- Netlify Project name：shroud-blog

推荐保持分支、空白 Base directory、构建命令和发布目录的当前值。项目没有后端 Functions；默认路径无需配置或添加函数。Production 环境变量已写入 netlify.toml，一般无需在页面重复填写。

GitHub 推送到配置的生产分支会触发 Netlify 构建；PR/分支预览可用于检查变更。Netlify 只从 GitHub 拉取代码，不会把 Netlify 页面设置反向同步提交到 GitHub。Netlify Project name 的 shroud-blog 与 GitHub 仓库名 PERSONAL-BLOG 分开管理；如需统一，在 Netlify 项目设置中改显示名。尚未确认用户是否已点击部署，也尚未验证首次部署结果。

## 6. 建议接手顺序

1. 先读取 git status --short --branch、git diff、git diff --cached，并单独查看本地未跟踪文件；完整保留根迁移方案删除状态及 docs 下两份未跟踪资料。
2. 以用户确认的 11 个删除文件为已完成范围，整理迁移剩余项。对历史文章、赞助页、Instant View 和媒体生成精确待删列表；媒体列表要带引用扫描结果，然后等用户确认。
3. 继续检查文章布局和所有 include 中的评论/通知/Worker 调用，把评论功能保持关闭，并保留已经存在的通用分享/复制链接。
4. 移除 link preview 外部抓取和 LQIP 生成流程；清理插件命名时比对两个 spoiler 插件及文章语法。保留方案要求的图片懒加载、GitHub Alerts、文章 ID、时区等仍在使用的功能。
5. 完成 README、About、友链、动态、PWA 名称、作者/域名占位内容；保留 MIT 与原主题归属。
6. 在不做全局安装的前提下准备 Ruby 3.4.11/Bundler；运行 **bundle exec jekyll build --strict_front_matter**。构建失败时先定位 Front Matter、依赖或插件根因。
7. 构建通过后检查资源引用和生成文件；验证首页、文章、搜索、标签、分类、归档、主题切换、PWA、RSS、Sitemap、语法高亮、数学公式和 Mermaid。
8. 对运行时代码和 _site 搜索 Worker URL、Cloudflare 服务配置、Telegram 评论脚本与旧域名；历史文章和归属说明分开处理。
9. 汇报验证证据及限制。除非用户更新授权，不要 push、merge、部署、修改 Netlify 账号设置或做新的批量删除。

## 7. 绝对不要踩的坑

- 不要运行 git clean、git reset --hard、批量 restore、强制推送或其他会覆盖工作区/远端历史的操作。
- 不要删除、覆盖或“清理”当前 docs 下未跟踪的迁移方案和 PERSONALIZATION_BRIEF.md；也不要擅自恢复根目录迁移方案。
- 不要把 Gemfile.lock 加进 .gitignore。
- 不要把 Netlify Functions、API、Cloudflare Worker 或 Telegram 评论作为新的后端方案加回来。
- 不要因文章提到 Cloudflare/Telegram 或主题归属链接包含旧仓库名，就全局替换/批量删除。
- 批量删除前必须提供确切路径清单并取得确认；图片与媒体必须先检查引用。
- 不要声称严格构建、站点部署或页面功能已通过，除非实际运行并记录结果。
- 不要从 Build settings 截图推断 Netlify 已经部署成功；截图仅证明用户当时处于配置页面。
- 不要未经用户再次授权执行 push、merge 或 Netlify 账号操作。
