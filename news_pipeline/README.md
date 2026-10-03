# AI News Collector

本目录包含 PERSONAL-BLOG 的本地 AI 资讯采集、编辑和发布工具。采集结果写入 `storage/inbox/`，去重状态写入 `state/seen.jsonl`；文章由编辑草稿审核后写入 Jekyll `_posts/`，不会自动调用外部 LLM 或下载图片。

## Windows 本地环境

在仓库根目录使用 PowerShell：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r news_pipeline\requirements.txt
```

如果 `py -3.13` 不可用，也可以使用当前 Python：

```powershell
python -m venv .venv
```

所有命令都显式使用 `.venv` 中的解释器，避免依赖 Anaconda 的全局包：

```powershell
.\.venv\Scripts\python.exe -m news_pipeline.cli collect --since-hours 24
.\.venv\Scripts\python.exe -m news_pipeline.cli collect --source openai --since-hours 168 --dry-run
.\.venv\Scripts\python.exe -m news_pipeline.cli health
.\.venv\Scripts\python.exe -m news_pipeline.cli edit --limit 7 --dry-run
.\.venv\Scripts\python.exe -m news_pipeline.cli publish --limit 7 --dry-run
.\.venv\Scripts\python.exe -m pytest tests\news_pipeline -q
```

`--limit` 是每个来源的上限，默认 20。`--dry-run` 会展示新条目数量，但不会创建 inbox 或修改去重状态。每个来源按顺序访问，遵守 `robots.txt`，并对同一主机限速。

## 编辑与本地发布

`edit` 对 inbox 候选按来源、时效、AI 相关性、信息增量、读者价值和重复度排序，并在 `reports/editor_selection.md` 留下所有候选的筛选理由。可重复使用 `--select NEWS_ID` 指定人工核验后应入选的条目；所有候选仍会出现在报告中。每个入选项会在 `storage/editor_drafts/` 建立 JSON 草稿骨架，编辑者需要核验官方原文并填写中文标题、摘要、分类、2–5 个标签及正文，再运行 Publisher。

```powershell
# 用 --dry-run 查看 32 条 inbox 候选，不写报告或草稿
.\.venv\Scripts\python.exe -m news_pipeline.cli edit --limit 7 --dry-run

# 人工核验并指定本轮选题；重复传入 --select 可选择多条
.\.venv\Scripts\python.exe -m news_pipeline.cli edit --limit 7 `
  --select bfc4355d370530a8 --select 8a18dee8ca8f941c `
  --select c3e5533bd61884fa --select 08aa8115cb5d9c89 `
  --select 7ee79eecb360c6d0 --select 09d1d26fa19dd694 `
  --select e81b1dea7ce0fb42

# 完成 JSON 草稿正文后，先校验预览，再写入 _posts/ 和 publications.jsonl
.\.venv\Scripts\python.exe -m news_pipeline.cli publish --limit 7 --dry-run
.\.venv\Scripts\python.exe -m news_pipeline.cli publish --limit 7
```

Publisher 在整批文章通过校验后才写文件；`state/publications.jsonl` 按 news ID 和来源 URL 记录已生成文章，重复运行会跳过已发布内容。Front Matter 保留 `ai_generated: true` 和 `reviewed: false`，发布命令只生成本地文件，不会部署网站。

## 采集边界

- 只保存来源提供的摘要片段和图片候选 URL、alt、来源信息，不下载图片或保存文章全文。
- arXiv 使用公开 RSS 分类 feed；RSS 可能在周末没有新条目。
- 原始响应调试缓存位于 `storage/raw/`，默认不生成。
- 采集器不参与 Netlify Build，也不修改 `_posts/`。
