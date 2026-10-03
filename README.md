# PERSONAL-BLOG

PERSONAL-BLOG 是一个使用 Jekyll 生成的静态个人博客起始项目，保留现有 Material Design 3 界面、导航和博客页面。可在本地预览与构建，也可由 Netlify 自动构建并发布静态文件。

主题基于 ZGQ Inc. 的 Jekyll Blog Theme 修改，并遵循 MIT License；原始归属与许可见 [`LICENSE`](LICENSE) 和站点页脚。

## 功能

- Jekyll 静态页面生成与 Markdown 文章
- 首页、文章、标签、分类、归档、动态、友链和关于页面
- 文章搜索、RSS Feed、Sitemap 与 SEO 元数据
- PWA 安装信息与离线缓存
- Netlify 静态站点构建配置

## 本地预览与构建

需要安装 Ruby 3.4.11（版本记录在 `.ruby-version`）、Bundler 和 Git。在项目目录运行：

```sh
bundle install
bundle exec jekyll serve --livereload
```

然后打开 <http://127.0.0.1:4000>。本地生成正式构建文件可运行：

```sh
bundle exec jekyll build --strict_front_matter
```

构建结果位于 `_site/`。该目录由 Jekyll 生成，无需手动编辑。

## Netlify 发布

将代码仓库连接到 Netlify 并创建站点。仓库中的 `netlify.toml` 已配置构建设置：

- 构建命令：`bundle exec jekyll build --strict_front_matter`
- 发布目录：`_site`
- Production 环境变量：`JEKYLL_ENV=production`

Netlify 会在后续仓库更新时重新构建并发布站点。上线后，请将 `_config.yml` 中的 `url` 改为站点实际使用的 HTTPS 域名，再触发一次构建。

## 个性化

- 在 `_config.yml` 设置站点标题、描述、作者和正式域名；社交账号字段默认为空，可按需填写。
- 在 `_posts/` 添加带有 Jekyll Front Matter 的 Markdown 文章。
- 在 `links.md` 的 `friends` 列表中替换标注为占位示例的友链。
- 在 `updates.md` 编辑站点动态。
- `docs/markdown-reference.md` 是不会发布到站点的 Markdown 语法参考；`_posts/2026-10-03-markdown-showcase.md` 是主题功能样例文章。

站点导航、Jekyll 插件和现有主题配色已保留，可从上述配置和内容文件开始调整。
