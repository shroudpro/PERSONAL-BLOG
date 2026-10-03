---
layout: post
title: Markdown 功能示例
date: 2026-10-03 09:00:00 +0800
categories:
  - 示例
tags:
  - Markdown
  - Jekyll
image: /logo.png
summary: 通过一篇短文检查常见 Markdown 功能与静态页面组件。
toc: true
---

本文是主题功能样例，用来检查 Markdown 解析、代码高亮、数学公式、Mermaid、图片延迟加载和通用隐藏内容效果。

# H1 标题示例

## 目录

* 目录
{:toc}

## 文本格式

### H3 标题示例

#### H4 标题示例

支持 **粗体**、*斜体*、~~删除线~~、`行内代码`，以及链接到[关于页面](/about/)的站内链接和[Markdown 指南](https://www.markdownguide.org/)外部链接。

## 列表与任务项

- 无序列表
  - 嵌套项目
- [x] Jekyll 生成页面
- [ ] 配置正式域名

1. 有序列表第一项
2. 有序列表第二项

## 引用与提示块

> 这是一段引用文本，可以用于摘录或补充说明。

> [!NOTE]
> GitHub 风格提示块由站点插件转换为带样式的提示卡片。

## 代码高亮

下面的 Ruby 示例用于检查 Rouge 语法高亮：

```ruby
def greet(name)
  "你好，#{name}！"
end

puts greet("世界")
```

## 表格

| 检查项 | 预期内容 | 状态 |
| :--- | :--- | :---: |
| 文章页面 | 标题、日期和正文 | 保留 |
| 图片 | 本地主题 Logo | 保留 |
| 搜索和归档 | 使用文章 Front Matter | 保留 |

## 图片与隐藏内容

![博客主题图标](/logo.png)

点击下方内容可显示：||这是一个通用的 Markdown 隐藏内容示例。||

## 数学公式

行内公式：$E = mc^2$。

块级公式：

$$
\int_0^1 x^2\,dx = \frac{1}{3}
$$

## Mermaid 流程图

```mermaid
flowchart LR
  Draft[撰写 Markdown] --> Build[Jekyll 构建]
  Build --> Static[生成静态页面]
  Static --> Host[Netlify 发布]
```

## 脚注与分隔线

这是一个脚注引用[^example]。

---

[^example]: 脚注内容显示在文章末尾。
