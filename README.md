# Dot小绿皮书

一本循序渐进教你使用 **ChatGPT Dot** 的开源中文手册。从第一次交代小任务，走到资料连接、持续跟进、任务委派和成果验收。

首版包含 **8 章课程、61 条问答、10 个编辑学习价值 8–9 分的 Dot 用户案例**。

[在线阅读](https://tiee7.github.io/dot-green-book/) · [学习路线](https://tiee7.github.io/dot-green-book/learn/) · [问答手册](https://tiee7.github.io/dot-green-book/faq/) · [Dot 案例](https://tiee7.github.io/dot-green-book/cases/) · [参与共建](CONTRIBUTING.md)

本项目基于 [dot-guide](https://github.com/Tiee7/dot-guide) 的内容主题与公开来源线索重新编写，独立维护。产品事实以 [Dot 官方说明](https://learn.chatgpt.com/docs/dots) 为依据，首版核对日期 **2026-10-01**。这是独立教程，不是 OpenAI 官方项目。

## 先做一件事，再多走一步

| 章节 | 你会做什么 |
| --- | --- |
| 01 认识 Dot 与入口 | 找到自己的 Dot，核对账户与连接范围 |
| 02 第一次小任务 | 用一份材料完成一项可检查的交付 |
| 03 说清责任与验收 | 写明目标、来源、决定权与完成条件 |
| 04 连接资料、电脑与插件 | 辨认实际账户、权限和工作环境 |
| 05 长期跟进与通知 | 核对时间、时区、结束日期和通知条件 |
| 06 跨设备与任务委派 | 交代任务上下文，在 Activity 查看执行 |
| 07 检查、纠错与停止 | 查看成果，分别停止主任务、委派与日程 |
| 08 搭建个人工作流程 | 把一项可验收的小工作变成长期责任 |

每章包含知识说明、操作步骤、可复制指令、验收清单与常见失败情形。问答支持关键词与分类筛选、锚点直达。案例有独立详情页、来源链接、Dot 的作用、结果、证据限制和改编练习。

## 只收 Dot 用户案例

精选库只收录明确来自 **ChatGPT Dot** 的用户公开任务。不收普通 GPT-6.1 生成案例，也不把混合产品演示改称纯 Dot 成果。

“8 分及以上”指本项目的**编辑学习价值评分**：目标清晰、过程可学习、结果具体、证据充分、迁移价值各 0–2 分。分数不是官方评分、用户满意度、准确率或成功率。逐项得分和原始证据均可查看。原帖核对不等于独立复现作者的完整任务。

查看 [案例审查记录](docs/case-review.md) 和网站“关于与共建”页面的评分标准。教程指令与操作步骤是教学改编，尚未替读者执行，不伪装成原作者逐字提示词。

## 本地阅读与开发

需要 **Node.js 20.11+**。没有运行时依赖，不需要 `npm install`、API Key 或后端账户。

```sh
npm run dev
# http://127.0.0.1:4174
```

```sh
npm run build
npm test
# GitHub Pages 的项目路径也需验证
SITE_BASE=/dot-green-book/ npm run build
```

`build` 从内容生成静态页面，并检查数据完整性、Dot 案例资格与评分、路由、内部链接及锚点。它不能证明实际 Dot 账号已完成任何练习。

## 项目结构

```text
content/                课程、问答与Dot精选案例，单一内容来源
scripts/build.mjs       静态页面生成器
scripts/check.mjs       内容与内部链接检查
scripts/serve.mjs       本地预览服务器
site.css / site.js      阅读界面与轻量交互
docs/                   来源、案例审查和验收记录
.github/                Issue模板与GitHub Pages工作流
dist/                   生成站点，不提交到Git
```

所有页面预生成，正文和来源无需 JavaScript 也能阅读。JavaScript 只负责筛选、复制、问答直达和本机阅读进度。没有第三方脚本或分析统计，进度仅存于浏览器，可在学习路线页清除。

## 发布

仓库 `main` 的工作流会生成 `dist/`，使用 GitHub Pages 发布。在仓库 **Settings → Pages → Source** 选择 **GitHub Actions**。项目路径由 `SITE_BASE=/dot-green-book/` 生成，支持章节和案例直接打开。

也可把 `npm run build` 产生的 `dist/` 上传到任意静态主机；如果挂载到子目录，设置对应 `SITE_BASE`。无环境凭据。

## 来源与许可

参见 [来源记录](docs/sources.md) 与 [贡献指南](CONTRIBUTING.md)。代码和原创教程采用 [MIT](LICENSE) 许可。第三方原帖及媒体保留原作者版权；本项目提供来源链接和事实摘要，不转载视频、照片或文章全文。
