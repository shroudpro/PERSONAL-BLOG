# 网站个性化资料简报

> 本文只记录仓库中可核对的现状与后续需要所有者确认的事项。标注“已确认”仅表示当前项目文件中确实如此，不代表其中的个人资料已由本人核实；不会把主题示例或推测当作真实信息。

## 1. 项目概况

- **技术栈与站点类型：已确认。** 当前主站是 Vue 3 + Vite + TypeScript 的静态个人博客与作品集，使用 Vue Router；内容从本地 Markdown 和 TypeScript 数据读取。不是 Jekyll。入口和依赖见 `package.json`、`vite.config.ts`、`src/main.ts`。
- **部署形态：已确认（仓库说明）。** `netlify.toml` 指向 `npm run build` 和 `dist`，并配置 SPA fallback。README 列出 Netlify 地址，但本次未访问外网，因此线上站点是否仍在该地址、当前是否可用，**待确认**。
- **内容目录：已确认。** `src/content/experiences/` 保存经历/成长记录，`src/content/projects/` 保存项目详情，`src/content/notes/` 保存短记录；`src/content/index.ts` 在构建时读取 Markdown、按发布状态过滤并排序。
- **个性化数据与页面：已确认。** `src/data/profile.ts` 保存姓名显示、首页文案、状态、所在地、联系链接和能力标签；`src/data/nav.ts` 保存首页导航；`src/data/achievements.ts` 保存成就。首页区块在 `src/components/sections/`，布局与侧栏在 `src/components/layout/`，静态中英文 UI 文案在 `src/i18n/messages.ts`。
- **视觉资源：已确认。** `src/styles/` 保存 CSS 变量、排版、布局和响应式样式；`public/images/` 有手绘 PNG、纸纹背景、GIF 和 favicon。资源清单中没有被页面引用的个人头像照片。
- **后端目录：已确认（项目说明）。** `backend/` 是历史实验/未来扩展参考，不属于当前静态主线；README 和 `AGENT.md` 均说明当前不需要线上后端、数据库、登录、评论、点赞或访客统计。个性化网站内容通常不需要改它。
- **项目说明文件：已阅读。** 根目录和网站源码主要目录未找到适用于主站的 `AGENTS.md`；仓库提供 `AGENT.md`、`CLAUDE.md`、`README.md` 和 `产品开发文档.md`。另发现并阅读 `.agents/skills/impeccable-main/AGENTS.md`，它属于被忽略的 Impeccable 技能包，不是主站说明。`AGENT.md` 是开发进度说明，不是 `AGENTS.md`。

## 2. 当前网站信息

- **站点名称：待确认。** 当前 `README.md` 与 `index.html` 使用 “Shroud Portfolio”；这只能确认仓库当前用名，是否继续使用由所有者确认。（`README.md:1,12`；`index.html:11`）
- **域名：待确认。** README 写有 `https://shroud-personal-portfolio.netlify.app`；未联网核验是否仍是正式域名，也未发现独立域名配置。（`README.md:18`）
- **标题与 SEO：待确认。** HTML 有固定标题 “Shroud Portfolio”，meta description 为“Shroud 的个人作品集，展示 AI 应用开发、前端工程实践和项目作品。”；未发现标题格式、canonical、Open Graph、社交分享卡片、robots/sitemap 或搜索引擎验证 ID 配置。（`index.html:6-11`；`public/` 文件清单）
- **所有者名称/笔名：待确认。** 当前 Hero 和侧栏品牌文字显示 “Shroud”；代码不能确认这是本人希望公开使用的姓名、笔名还是临时名称。（`src/data/profile.ts:8-10`；`src/components/sections/HeroSection.vue:5-8`；`src/components/layout/SidebarNav.vue:3-5`）
- **首页介绍与 About：待确认。** Hero 标题为 “I build AI ideas into working systems.”；简介称关注 AI 智能应用开发、把想法转为 MVP、前端页面和展示系统。About 文案提到 Agent、产品落地、用户场景、页面流程、技术架构和展示效果。它们是当前文案，不应未经本人确认就视为准确履历。（`src/data/profile.ts:11-17`）
- **状态、所在地与联系资料：待确认公开范围。** 当前资料写有 `BUPT在读,欢迎交流合作`、`China/Beijing`、邮箱 `shroudmail233@Gmail.com`、GitHub `github.com/shroudpro`；简历链接显示“简历待补充”且禁用。请本人确认是否准确、是否继续公开或隐藏。（`src/data/profile.ts:25-45`）
- **Logo 与头像：待确认。** 侧栏显示手绘眼睛图 `eye-logo.png` 和 “Shroud”；配置中另有 `logoText: 'S'`，但目前未被页面引用。页面使用手绘装饰图而非个人头像；`public/favicon.png` 是当前 favicon。（`src/data/profile.ts:8-10`；`src/components/layout/SidebarNav.vue:3-5`；`src/components/sections/HeroSection.vue:12-23`）
- **页面、导航与语言：已确认。** 首页顺序为 Hero、About、Experience、Projects、Achievements、Blog / Notes；侧栏导航对应 Home、About、Experience、Projects、Achievements、Blog。路由另有 `/project/:id`、`/blog`、`/blog/:slug`。UI 支持中英文切换，但 Markdown 正文不自动翻译。（`src/pages/HomePage.vue:1-9`；`src/data/nav.ts:6-13`；`src/router/index.ts:7-28`；`CLAUDE.md:48-52`）
- **栏目、分类与当前内容：已确认仓库值；真实性待确认。** Experience frontmatter 有 `category` 和 `tags`，Project 用 `type`、`stack`，Note 用 `tags`；没有单独的分类页/标签管理配置。当前内容主题包括 AI 应用、前端/产品工程、竞赛与阶段性成长记录。文件里有 13 条已发布 Experience、9 条已发布 Project、1 条已发布 Note；首页只选已发布且 `featured: true` 的项目，当前为 Wardrobe、数学建模 AI 模板、Quartus MCP。所有角色、日期、贡献和成果仍应由本人核实。（`src/content/index.ts:69-112,146-148`；`src/content/experiences/`；`src/content/projects/`；`src/content/notes/`）
- **文章呈现方式：已确认。** `/blog` 先完整展示已发布 Experience，再展示 Notes；首页只显示最近的 3 条成长记录。内容按 Markdown frontmatter 中的发布时间/排序配置管理。（`src/pages/BlogListPage.vue:5-43`；`src/content/index.ts:119-148,172-178`）
- **特别需要核对的日期：待确认。** `Coolearn` 当前展示日期为 `2026-10`；项目开发说明明确指出，现有素材不足以核实实际项目时间，需要本人确认。（`src/content/projects/coolearn.md:2-5`；`src/content/experiences/2026-10-coolearn.md:2-6`；`AGENT.md:95`）
- **成就与统计文案：待确认。** 展示统计值为 `10+`，标签为 “Project Iterations”；另有三条 AI 应用、竞赛项目和工程文档成就。需要确认数字、范围与描述是否可公开且有事实依据。（`src/data/achievements.ts:7-30`）
- **视觉风格：已确认当前实现；是否保留待确认。** 当前是暖白纸感、低饱和棕色/灰色、手绘装饰、固定左侧栏和衬线标题。主要变量包括深色 `#1e1e1c`、棕色 `#8f705f`、纸白 `#fbfaf5` / `#f7f5ee`、强调色 `#d8b6a2`；英文字体栈含 Cormorant Garamond / Playfair Display，中文衬线栈含 Noto Serif SC / Source Han Serif SC / SimSun，手写体栈含 Caveat。（`src/styles/variables.css:1-26`；`src/styles/base.css:11-20`；`AGENT.md:81`）
- **页脚与版权：已确认。** 目前没有独立页尾区块；左侧栏显示 `© 2026 Shroud`。年份写死在组件模板中，网站名称来自 profile。（`src/components/layout/SidebarNav.vue:20-35`）
- **联系、社交与访客功能：已确认当前实现。** About 区展示 Email、GitHub、Resume、状态和所在地；侧栏只显示启用的 GitHub 链接。没有真实联系表单、评论、订阅或访问统计功能。（`src/components/sections/AboutSection.vue:12-27`；`src/components/layout/SidebarNav.vue:20-35`；`AGENT.md:9,55-56`）
- **统计/搜索配置：已确认未配置。** 未发现网站流量分析、搜索引擎验证 ID、评论或邮件订阅的站点配置；当前项目说明也把访问统计列为非目标。（`AGENT.md:9`；`index.html:3-12`）
- **许可证与隐私声明：已确认未补充。** README 表示开源许可证可后续补充；未发现网站隐私声明。（`README.md:359-361`）
- **占位、草稿与陈旧文案：已确认。** 简历是禁用占位；项目草稿 `private-draft.md` 和 Note `private-note.md` 都标记未发布，不进入页面。`profile.ts` 还保留未被使用的 `contactIntro`、`contactNotice`，后者称“静态展示表单”，但当前页面没有该表单，需确认是否删除或改写。（`src/data/profile.ts:22-24,41-45`；`src/content/projects/private-draft.md:2-13`；`src/content/notes/private-note.md:2-9`）
- **目标读者与文章语气：推测。** 文案、项目详情结构和 GitHub 链接呈现出面向项目浏览者/潜在合作方介绍个人能力的倾向；仓库没有明确目标读者或写作风格设定，不能当作所有者选择。（`src/data/profile.ts:11-17`；`src/components/sections/ProjectsSection.vue:20-28`）

## 3. 个性化位置清单

| 个性化项目 | 当前值或现状 | 状态 | 对应文件与位置 | 后续需要做什么 |
|---|---|---|---|---|
| 网站名称、标题与 SEO 简介 | `Shroud Portfolio`；description 介绍 AI 应用、前端工程和项目作品；没有标题模板或社交分享元数据 | 待确认 | `index.html:6-11`；`README.md:1,12` | 确认显示名、浏览器标题格式与 SEO 描述；若需要社交卡片/搜索预览，再补充相应配置 |
| 域名 | README 列出 Netlify 子域名；未核验线上状态 | 待确认 | `README.md:18`；`netlify.toml:1-8` | 确认保留当前域名还是改用自有域名；只有确定域名后才需要据此设置 canonical 等 SEO 项 |
| 所有者名称/笔名与 Hero | `Shroud`；英文 headline 加中文简介 | 待确认 | `src/data/profile.ts:8-17`；`src/components/sections/HeroSection.vue:5-23` | 确认姓名/笔名/隐藏方式，并提供本人认可的职业定位、首页一句话介绍和简介 |
| About、状态与所在地 | 两段 About 文案；状态为在读/欢迎合作；地点为 China/Beijing | 待确认 | `src/data/profile.ts:14-26`；`src/components/sections/AboutSection.vue:7-27` | 核对经历与公开范围；所在地可简化或隐藏，不必提供精确住址 |
| 头像、Logo 与图片 | 有眼睛手绘 Logo、favicon、插画和纸纹；未配置个人肖像 | 待确认 | `public/favicon.png`；`public/images/`；`src/components/layout/SidebarNav.vue:3-5` | 决定沿用手绘视觉，还是提供头像/新 Logo；如不想公开可明确写“不展示” |
| 项目、经历与文章内容 | Markdown 维护；首页当前精选 Wardrobe、数学建模 AI 模板、Quartus MCP；部分经历也用于 Blog | 待确认 | `src/content/projects/*.md`；`src/content/experiences/*.md`；`src/content/notes/*.md`；`src/content/index.ts:69-148` | 确认哪些条目继续公开/置顶，核对本人角色、日期、技术栈、贡献、结果和尚未完成的边界；尤其确认 Coolearn 日期 |
| 成就与项目数字 | `10+ Project Iterations` 及三项文字成就 | 待确认 | `src/data/achievements.ts:7-30` | 提供可验证的数字口径和成果，或改成不含未经核验数字的描述 |
| 导航、栏目、分类与标签 | 固定 Home/About/Experience/Projects/Achievements/Blog；内容类型各有 category/type/tags/stack 字段 | 已确认（现状） | `src/data/nav.ts:6-13`；`src/i18n/messages.ts:4-25,69-89`；各 Markdown frontmatter | 若栏目仍合适无需改；新增/删改栏目需同步导航、区块和锚点；只有希望增加筛选时才需要另做功能 |
| 文章主题、读者与语气 | 当前主题集中于 AI 应用、前端工程、产品和竞赛；未配置读者/语气规则 | 推测 | `src/data/profile.ts:47-63`；`src/content/` | 确认希望突出的话题、目标读者、长短文比例与表达风格；不要把推测当作用户画像 |
| 配色、字体与布局 | 暖白纸感、衬线标题、手写点缀、固定左侧导航 | 已确认（现状） | `src/styles/variables.css:1-52`；`src/styles/typography.css`；`src/styles/layout.css`；`AGENT.md:81` | 若沿用则无需调整；若换色/字体/布局，先确认固定侧栏和响应式阅读体验是否也要改变 |
| 联系方式与社交链接 | `shroudmail233@Gmail.com`、`github.com/shroudpro` 已启用；Resume disabled；无其他社交链接 | 待确认 | `src/data/profile.ts:27-46`；`src/components/sections/AboutSection.vue:12-27` | 确认哪些链接可公开，提供最新地址或写“不展示”；简历仅在有实际文件/链接时启用 |
| 页尾与版权 | 左侧栏写 `© 2026 Shroud`，没有独立 footer | 待确认 | `src/components/layout/SidebarNav.vue:20-35` | 确认版权署名；后续如持续维护，建议决定年份是否动态更新 |
| 分析、搜索验证、评论、订阅 | 当前均未接入；无需填写 ID 或密钥 | 已确认（当前无需配置） | `AGENT.md:9`；`index.html:3-12`；仓库没有对应配置文件 | 若未来确实要启用，再确认服务和非敏感站点 ID；不要把密钥写入前端或资料文档 |
| 许可证/隐私说明 | README 说许可证可后续补充；未发现隐私声明 | 已确认（尚未配置） | `README.md:359-361` | 所有者决定是否为代码仓库选择许可证；只有收集访客数据或新增相关功能时再确定隐私说明 |
| 过期占位与隐藏草稿 | 简历、联系说明存在占位；两个 Markdown 草稿被 `isPublished: false` 隐藏 | 已确认 | `src/data/profile.ts:22-24,41-45`；`src/content/projects/private-draft.md:13`；`src/content/notes/private-note.md:9` | 决定移除/替换简历占位和未使用联系文案；逐条确认草稿不应意外发布 |

## 4. 需要网站所有者补充的信息

### 必须提供

- **网站显示名称、所有者公开署名与一句话定位**
  - 用途：替换站点标题、侧栏品牌、Hero 标题和 SEO 文案中的当前名称/介绍。
  - 可填写：`网站显示名称：[请填写]；作者显示：[真实姓名 / 笔名 / 不显示，请选择]；一句话定位：[请填写]`
  - 仅公开你选定的署名；不需要提供身份证件上的姓名。
- **本人认可的简介和公开资料范围**
  - 用途：填充首页 Hero、About、状态和所在地，确保网站介绍准确且符合公开意愿。
  - 可填写：`职业/身份：[请填写]；个人简介：[请填写]；状态：[请填写或“不展示”]；所在地：[请填写或“不展示”]`
  - 可只写公开显示的城市/地区，也可保持隐藏；不要提供精确住址或其他无关个人信息。
- **已发布项目、经历、文章和成就的核验结果**
  - 用途：决定公开内容、首页精选项及履历/项目详情的准确性。
  - 可填写：`保留公开：[标题列表]；修改：[标题 + 正确信息]；下线：[标题列表]；首页精选：[最多希望展示的项目]；成就数字/口径：[请填写或删除数字]`
  - 尤其请核实项目角色、时间、成果、部署/测试状态，以及 Coolearn 的实际时间。
- **当前联系方式是否继续公开**
  - 用途：更新 About 中的 Email、GitHub、Resume、状态和所在地链接。
  - 可填写：`邮箱：[保留当前 / 新邮箱 / 不展示]；GitHub：[保留当前 / 新链接 / 不展示]；简历：[文件路径或链接 / 不展示]`
  - 联系方式可以全部隐藏；不需要补充私人电话或家庭地址。
- **网站简介/SEO 描述**
  - 用途：设置搜索结果摘要和浏览器标签页呈现的站点身份。
  - 可填写：`SEO 简介：[用 1–2 句话说明网站展示什么、面向谁]`

### 建议提供

- **域名与标题格式**
  - 用途：README 已列出 Netlify 地址；若采用自有域名，后续可据此完善站点元数据。
  - 可填写：`最终域名：[当前 Netlify 域名 / 自有域名 / 尚未决定]；标题格式：[网站名｜页面名等，或保持固定标题]`
- **文章主题、目标读者和个人写作风格**
  - 用途：使 Blog/Notes 和项目介绍更像本人，而不是泛化的作品集文案。
  - 可填写：`重点主题：[请填写关键词]；目标读者：[请填写]；风格关键词：[请填写几个词]；不希望出现的表达：[可选]`
- **语言偏好与分类方式**
  - 用途：当前只有 UI 中英文切换，Markdown 内容不会自动翻译；栏目与标签由本地数据控制。
  - 可填写：`文章主要语言：[中文 / 英文 / 双语]；希望保留/调整的栏目：[请填写]；分类或标签规则：[请填写或沿用现状]`

### 可选

- **头像、Logo、简历或其他公开链接**
  - 用途：替换现有插画品牌，或启用真实简历和额外社交入口。
  - 可填写：`头像：[文件路径 / 暂不提供 / 不展示]；Logo：[文件路径 / 沿用手绘眼睛 / 暂不提供]；简历：[文件路径或公开链接 / 不展示]；其他链接：[请填写或“不适用”]`
- **视觉偏好**
  - 用途：决定是否保留现有暖白纸感、手绘插画、衬线标题和固定侧栏。
  - 可填写：`保留现有视觉：[是 / 否]；关键词：[请填写几个关键词]；希望调整的颜色/字体/布局：[请填写或“不调整”]`
- **版权、许可证或隐私声明**
  - 用途：补齐 README 已注明可后续添加的许可证，或在实际需要时说明数据处理方式。
  - 可填写：`版权署名：[请填写]；仓库许可证：[许可证名称 / 暂不设置]；隐私说明：[公开文本路径 / 暂不需要]`
  - 目前没有评论、订阅、联系表单或统计，不需要为这些未启用功能提供密钥、令牌或配置值。

## 5. 可复制填写区

```yaml
site:
  display_name: 待填写
  domain: 待填写
  title_format: 待填写
  seo_description: 待填写
owner:
  display_name_or_pseudonym: 待填写
  role_or_headline: 待填写
  hero_intro: 待填写
  about_bio: 待填写
  status_display: 待填写
  location_display: 待填写
  avatar_file_or_visibility: 待填写
contact:
  email_or_visibility: 待填写
  github_url_or_visibility: 待填写
  resume_file_or_visibility: 待填写
  other_public_links: 不适用
content:
  items_to_keep_public: 待填写
  items_to_correct_or_hide: 待填写
  featured_projects: 待填写
  achievement_metric_and_basis: 待填写
  topics: 待填写
  target_readers: 待填写
  writing_style: 待填写
  primary_content_language: 待填写
design:
  keep_current_style: 待填写
  style_keywords: 待填写
  logo_file_or_preference: 待填写
site_policies:
  copyright_display: 待填写
  repository_license: 待填写
  privacy_notice: 不适用
```

## 6. 后续个性化实施说明

- 文案和公开个人资料优先改 `src/data/profile.ts`；站点标题、description 和 favicon 在 `index.html`；侧栏品牌文字与版权在 `src/components/layout/SidebarNav.vue`。侧栏名称目前直接写在模板里，因此只改 `profile.name` 不会自动替换品牌文字。
- 项目、经历与文章正文分别改 `src/content/projects/`、`src/content/experiences/`、`src/content/notes/` 的 Markdown frontmatter 和正文；`isPublished` 控制是否进入网站，`featured` 控制首页精选项目，日期和 `sortOrder` 会影响顺序。成就改 `src/data/achievements.ts`。
- 栏目名称和静态 UI 中英文文案改 `src/data/nav.ts` 与 `src/i18n/messages.ts`。改动栏目结构时需要同步首页区块、导航锚点和路由；现有语言切换不会翻译文章正文。
- 若保留暖白纸感，只需沿用 `src/styles/variables.css` 和现有 PNG；更换配色或字体会影响全站组件。调整侧栏宽度、页面分栏、标题字号或 section 数量可能影响桌面布局和响应式断点，应一并检查 `layout.css`、`responsive.css` 及对应组件。
- 头像、Logo、favicon 和项目封面资源放入 `public/` 后，还需更新引用它们的 Vue 组件或 Markdown frontmatter。换掉眼睛图可能同时影响侧栏、Hero 的加载失败回退和 favicon 观感。
- 目前没有独立页脚，版权写在侧栏；新增页脚、统计、表单、评论、订阅或搜索验证属于布局/功能改动，不是简单换文案。只有所有者明确需要时，才需要调整对应组件与部署/隐私说明。
- 当前静态站从本地 Markdown/TypeScript 取内容。除非未来决定启用后端，不需要改 `backend/`、数据库或 API 写入配置。

## 7. 不确定项与跳过项

- `Shroud` 是否是所有者最终选定的笔名、BUPT/所在地资料是否准确及是否愿意公开，仓库无法独立验证。
- 项目/经历中的日期、本人承担的角色、成果成熟度、成就数字与内容发布授权需要所有者逐条确认；Coolearn 时间在 `AGENT.md:95` 明确标为待本人核实。
- README 中的线上域名只作为仓库文本记录；本次未访问外网，未确认域名归属、线上内容或部署状态。
- 目标读者、个人写作语气、头像/Logo 偏好、最终域名、许可证选择和隐私声明均未由仓库明确指定。
- 未读取 `.env` 或其他可能保存本地凭据的文件。项目文档提及 `GITHUB_TOKEN`、`DATABASE_URL`、`API_WRITE_TOKEN` 等配置项名称，代码还读取 `VITE_API_BASE_URL`；仅记录名称，没有读取或复制任何实际值。发现敏感配置，已跳过。
- 本次仅检查项目说明、网站源文件、Markdown 内容、样式和公开资源路径；没有联网、安装依赖、运行构建或测试，也没有修改网站代码和其他现有文件。


