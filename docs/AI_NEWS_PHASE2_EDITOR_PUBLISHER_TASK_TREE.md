# PERSONAL-BLOG：Phase 2 AI Editor + Jekyll Publisher MVP

> 当前前提：Phase 1 Collector 已完成，10 个高质量 AI 数据源可采集，`news_pipeline/storage/inbox/` 已有本地资讯；Jekyll / Netlify 构建链已验证可用。  
> 本阶段目标：**从 inbox 中筛选 5～10 条高价值资讯，生成真实 Jekyll 文章，完成本地构建与页面验收。**  
> 本阶段不要自动 `git push`，不要创建定时任务，不要无人值守发布。

## 总任务

你正在维护 PERSONAL-BLOG，一个使用 Jekyll + GitHub + Netlify 的静态 AI 资讯网站。

Phase 1 已完成 Collector。现在进入 Phase 2，建立：

```text
Collector
→ AI Editor
→ Jekyll Publisher
→ Human Review
```

本阶段只验证 5～10 篇真实资讯文章的闭环，不追求全自动。

## T0：读取现有实现

先扫描：

```text
news_pipeline/
_posts/
_layouts/post.html
_includes/post-list.html
_config.yml
```

读取：

```text
news_pipeline/storage/inbox/*.json
news_pipeline/state/seen.jsonl
```

根据当前项目实际支持的 Front Matter 字段生成文章，不要凭经验假设。

## T1：建立 Editor

新增：

```text
news_pipeline/editor/
├── __init__.py
├── selector.py
├── article.py
├── taxonomy.py
└── validator.py
```

`selector.py` 从 inbox 中筛选候选资讯。

筛选维度：

```text
来源权威性
时效性
AI 领域相关性
信息增量
对技术读者的价值
与其他资讯的重复程度
```

优先：

```text
重大模型发布
重要产品更新
重要研究结果
主流开源模型 / 框架
AI Infra 更新
值得关注的安全研究
```

降低优先级：

```text
纯营销
招聘
活动预告
重复公告
缺乏实质信息的品牌内容
```

第一轮只选 **5～10 条**。

输出：

```text
news_pipeline/reports/editor_selection.md
```

记录每条资讯：

```text
选择 / 放弃
理由
来源
原始标题
URL
```

## T2：固定分类体系

第一版主分类只允许：

```text
模型发布
产品更新
研究进展
开源项目
AI 工具
AI 基础设施
安全与治理
行业动态
```

每篇文章：

```text
1 个主分类
2～5 个 tags
```

不要生成大量同义标签。

## T3：生成中文资讯正文

每篇文章基于：

```text
inbox metadata
+
原始官方来源
```

生成中文内容。

推荐结构：

```markdown
## 发生了什么

用 1～2 段讲清核心事件。

## 关键更新

提炼 3～5 个真正重要的变化。

## 为什么值得关注

解释对 AI 开发者、研究者或行业的实际意义。

## 来源

给出官方原文链接。
```

建议长度：

```text
400～1000 中文字
```

要求：

- 不复制原文大段内容。
- 不编造原文没有的信息。
- 不把推测写成事实。
- 数字、模型名称、发布日期等关键事实必须能从来源核验。
- 原来源信息不足时宁可写短。
- 明确区分“官方宣布”和编辑性解释。
- 必须保留原始来源链接。

## T4：标题规则

标题要求：

```text
准确
简短
信息密度高
不标题党
```

禁止使用：

```text
震惊
史诗级
AI 圈炸了
彻底改变世界
```

除非它们本身就是正式引用内容。

## T5：生成 Front Matter

先检查现有模板实际字段。

统一生成类似：

```yaml
---
layout: post
title: "..."
date: 2026-10-03 20:30:00 +0800
summary: "..."
categories:
  - 模型发布
tags:
  - Anthropic
  - Claude
  - LLM
source_name: "Anthropic"
source_url: "https://..."
source_published_at: "..."
ai_generated: true
reviewed: false
toc: true
---
```

如果现有项目字段命名不同，以项目实际实现为准。

## T6：文件命名

统一：

```text
_posts/YYYY-MM-DD-source-short-slug.md
```

例如：

```text
_posts/2026-10-03-anthropic-claude-update.md
```

要求：

- slug 只用 ASCII。
- 小写。
- 单词用 `-`。
- 不用中文文件名。
- 不产生重复 slug。

## T7：图片 MVP

本阶段优先版权安全。

优先级：

```text
1. 官方明确提供的 press / media asset
2. 明确允许使用的官方图片
3. 自己生成的统一新闻封面
4. 无图
```

禁止：

- 默认下载新闻网站配图。
- 把 `og:image` 自动视为可转载。
- 批量下载 inbox 中所有 image_url。

如果无法确认图片使用条件，先留空。

## T8：建立 Publisher

新增：

```text
news_pipeline/publisher/
├── __init__.py
└── jekyll.py
```

职责：

```text
EditorArticle
→ Validator
→ Markdown
→ _posts/
```

Publisher 不负责：

```text
git commit
git push
Netlify
```

## T9：Validator

写入 `_posts` 前检查：

```text
title 非空
date 合法
summary 非空
category 合法
tags 数量合理
source_name 非空
source_url 合法
正文非空
不存在重复 source_url
不存在重复 slug
```

失败时：

```text
不写入 _posts
记录错误
```

## T10：扩展 CLI

至少支持：

```bash
python -m news_pipeline.cli edit --limit 10
python -m news_pipeline.cli edit --dry-run
python -m news_pipeline.cli publish --limit 5 --dry-run
python -m news_pipeline.cli publish --limit 5
```

推荐流程：

```text
collect
↓
edit --dry-run
↓
查看 selection report
↓
publish --dry-run
↓
检查 Markdown
↓
publish
```

本阶段禁止：

```text
publish --push
auto-deploy
```

## T11：生成第一批真实文章

从当前 inbox 中选择：

```text
5～10 条
```

要求：

```text
至少来自 3 个不同来源
尽量覆盖 3 个以上分类或主题
```

不要一次性把所有 inbox 都发布。

## T12：构建验证

执行：

```bash
bundle exec jekyll build --strict_front_matter
```

必须通过。

## T13：页面验收

检查：

```text
首页出现文章
文章计数正确
文章卡片正常
摘要正常
详情页正常
分类计数变化
标签计数变化
归档出现文章
搜索能搜索到新文章
来源 URL 可点击
深色模式正常
移动端正常
```

## T14：发布状态记录

不要删除 inbox 原始数据。

建立：

```text
news_pipeline/state/publications.jsonl
```

每条记录：

```json
{
  "news_id": "...",
  "post_path": "_posts/...",
  "source_url": "...",
  "published_local_at": "..."
}
```

确保同一资讯以后不会再次生成文章。

## T15：停止点

满足以下条件后停止：

```text
5～10 篇真实 Jekyll AI 资讯文章已生成
Jekyll strict build 成功
首页可以显示文章
标签 / 分类 / 搜索正常
来源信息可追溯
重复新闻不会再次生成
```

不要继续：

```text
git commit
git push
Netlify 部署
定时任务
无人审核发布
```

## 最终交付报告

完成后输出：

```text
1. 实际读取多少条 inbox
2. 选择了哪 5～10 条
3. 每条选择理由
4. 主要放弃候选及原因
5. 新生成的 _posts 文件
6. 分类和标签统计
7. 图片采用情况
8. Validator 结果
9. Jekyll build 结果
10. 页面验收结果
11. 是否发现重复新闻
12. 当前已知问题
13. 下一阶段自动化建议
```

必须给真实命令结果和可复核证据。

## 核心边界

本阶段只证明：

```text
高质量来源
→ Collector
→ inbox
→ AI Editor
→ Jekyll Markdown
→ 本地页面
```

这条链路能够稳定产出质量可控的 AI 资讯。

只有闭环稳定后，下一阶段才进入：

```text
Codex Scheduled Task
→ 定时 collect
→ 定时 edit
→ 自动生成待审核文章
→ Git 提交策略
→ Netlify 自动更新
```
