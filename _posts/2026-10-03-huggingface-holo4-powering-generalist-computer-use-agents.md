---
layout: post
title: Holo4 发布：一个模型跨 GUI、代码、MCP 与 API 操作
date: 2026-10-03 23:24:34 +0800
summary: Hcompany 发布 Holo4 两种模型规格，面向桌面、网页、Android、代码沙箱和业务 API 等工作流，并公开模型权重与评测轨迹。
categories:
- 开源项目
tags:
- Hcompany
- Holo4
- 开源权重
- Computer Use
image: ''
source_name: Hugging Face Blog
source_url: https://huggingface.co/blog/Hcompany/holo4
source_published_at: '2026-09-28T09:44:05Z'
ai_generated: true
reviewed: false
toc: true
---

## 发生了什么

Hcompany 发布 Holo4 系列通用操作模型，包含 27B dense 和 35B-A3B Mixture of Experts 两种规格，并同时更新 Holotron4 Nano。Holo4 面向需要在软件界面之间完成任务的场景：同一个模型可以点击和输入图形界面、编写并运行代码，也可以调用 MCP（Model Context Protocol）或 API 工具。

## 多种操作界面与公开材料

发布页称，模型可用于桌面、网页、Android、代码沙箱和业务 API，不必按平台切换不同模型。Hcompany 公开了模型集合中的多种权重格式，并提供公开基准的操作轨迹，便于查看模型每一步如何完成任务。公司披露的 OSWorld 2.0 结果中，Holo4 27B 为 61.7%，Holo4 35B-A3B 为 30.9%；其文章也提醒不同模型的发布版本、运行框架和成本统计方法并不完全相同，因此这些对照适合参考，不能简单视为同条件排名。

## 为什么值得关注

企业软件工作往往横跨界面、脚本和服务接口。能够在这些方式之间切换的操作模型，可能减少为每一种应用单独集成代理的工作量；同时，长流程任务需要可靠的错误恢复、权限边界和过程审计。公开权重和执行轨迹让研究者更容易复现与检查，但真实业务部署仍需要结合自身环境评估。

## 来源

[Hcompany 官方发布文章（Hugging Face）](https://huggingface.co/blog/Hcompany/holo4)
