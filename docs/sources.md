# 来源与事实边界

首版事实核对日期：2026-10-01。产品事实通过 OpenAI Docs 先搜索再抓取完整文档核对；这属于官方文档核对，不是 Dot 实机功能验收。

## 项目基础

用户指定基础仓库：[Tiee7/dot-guide](https://github.com/Tiee7/dot-guide)。使用 `main` 的 `134f1af17498777ea92e8c27074c0c1957f53779` 作为本次内容参考快照。重新编写学习路线、问答与阅读界面；不复制原仓库 Git 历史、部署元数据、来源本机路径或混合模型案例库。原仓库不修改。

## 一手产品资料

| 来源 | 用途 |
| --- | --- |
| [Meet dots](https://learn.chatgpt.com/docs/dots) | 定义、开放范围、用量与总体能力 |
| [Get started with your dot](https://learn.chatgpt.com/docs/dots/getting-started) | 创建、首个责任和入口 |
| [Control your dot](https://learn.chatgpt.com/docs/dots/controls) | 活动、审批、规则、停止与数据控制 |
| [Connect computers and apps](https://learn.chatgpt.com/docs/dots/computers-and-apps) | 云电脑、本机、插件与网站登录 |
| [Message your dot](https://learn.chatgpt.com/docs/dots/channels) | ChatGPT、语音、Slack和Teams |
| [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory) | 分派、周期任务、事件、记忆与主动研究 |

## 必须持续保留的条件

- Dot 由 GPT-6 Astra 驱动。产品角色与模型性能不是同一件事；普通 GPT-6.1 成果不进入精选库。
- Dot 逐步开放，满足套餐条件不等于入口已经开放；组织还可能需要管理员配置。
- 云工作与本机工作不同。本机访问需电脑联网、ChatGPT App 开着，云浏览器不继承个人浏览器会话。
- 联系方式、插件和本机访问分别连接。加入频道不自动开始监控。
- 对外行动、资料访问与持续授权受具体权限和内置要求限制。
- Pause 只停止当前主任务。委派任务与未来日程要分别停止；已完成的外部动作不会自动回滚。
- Dot 的记忆与主动研究不是全部对话全文。主动研究本身只读，后续行动另受权限约束。
- 每个案例的“作者自述”“直接可见输出”“未独立验证”需保持区别。评分仅表示学习材料价值。

## 更新方法

产品事实变化时重新读取对应官方页面，记录日期、变化与受影响的内容。案例原帖失效、删除或归属有疑问时重新审查，不仅依据上游摘要保留高分。

站点发布方式参照 [GitHub Pages 自定义工作流官方说明](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)，采用构建、上传静态产物和独立部署任务。发布是否成功需另查 Actions 与在线页面。
