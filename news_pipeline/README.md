# AI News Collector

本目录包含 PERSONAL-BLOG 的本地资讯采集器。采集结果写入 `storage/inbox/`，去重状态写入 `state/seen.jsonl`；采集器不会生成 Jekyll 文章或下载图片。

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
.\.venv\Scripts\python.exe -m pytest tests\news_pipeline -q
```

`--limit` 是每个来源的上限，默认 20。`--dry-run` 会展示新条目数量，但不会创建 inbox 或修改去重状态。每个来源按顺序访问，遵守 `robots.txt`，并对同一主机限速。

## 采集边界

- 只保存来源提供的摘要片段和图片候选 URL、alt、来源信息，不下载图片或保存文章全文。
- arXiv 使用公开 RSS 分类 feed；RSS 可能在周末没有新条目。
- 原始响应调试缓存位于 `storage/raw/`，默认不生成。
- 采集器不参与 Netlify Build，也不修改 `_posts/`。
