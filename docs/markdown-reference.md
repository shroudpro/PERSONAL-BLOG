# Markdown 写作参考

本文只作为写作语法参考，`docs/` 已从 Jekyll 输出中排除。

## 文本与链接

支持 **粗体**、*斜体*、~~删除线~~、`行内代码` 和 [站内链接](/about/)。

## 列表

- 无序列表
  - 嵌套列表
- [x] 已完成事项
- [ ] 待办事项

1. 有序列表第一项
2. 有序列表第二项

## 引用与提醒

> 这是一段引用。

> [!TIP]
> 使用 GitHub 风格提示块表达补充说明。

## 代码

```ruby
def greeting(name)
  "你好，#{name}！"
end
```

## 表格

| 功能 | 示例 | 用途 |
| --- | --- | --- |
| Markdown | `**文字**` | 格式化内容 |
| Jekyll | Front Matter | 站点生成 |

## 图片与隐藏内容

![PERSONAL-BLOG 图标](/logo.png)

点击可显示隐藏内容：||这是折叠的提示文字||

## 数学公式

行内公式：$a^2 + b^2 = c^2$

$$
\int_0^1 x^2\,dx = \frac{1}{3}
$$

## Mermaid

```mermaid
flowchart LR
  Write[编写 Markdown] --> Build[Jekyll 构建]
  Build --> Publish[发布静态页面]
```

## 脚注

这是脚注示例[^note]。

[^note]: 脚注内容会显示在文章末尾。
