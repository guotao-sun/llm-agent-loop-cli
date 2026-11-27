# LLM Agent Loop Demo（纯标准库）

和大模型 API 打交道的最小实验：从"一次请求一个回答"走到"多步调工具"，
全程只用 `urllib`，不装 `openai` 这类 SDK，一行一行看清楚线上发生了什么。

## 它做了什么

一次提问不再等于一次请求。模型可以连续多步：先取技能流程，再查档案，
再写文件，最后收尾。每一步都是一次独立的 HTTP 请求，脚本负责执行工具、
把结果拼回 `messages`、再发下一次。

- 三层记忆：`messages` 窗口 / 按天归档 / 结构化档案（同槽位覆盖留痕）
- 档案冲突防护：主题词归一 + 正反翻转检测，别让"要询问"和"不需要询问"同时生效
- 召回决策：每轮先让模型答一次 `{need_recall, level, query}`，需要才查
- **单步请求和 Agent Loop 共用同一个装配入口**，Agent 模式不会绕过召回
- 工具调用：8 个工具，模型只出 `name + arguments`，执行在本地
- 技能：`skills/<name>/SKILL.md`，平时只列名字，正文按需 `load_skill`
- 报文日志：每次出网请求存一份到 `logs/`，看得出这轮发了几次

## 目录

```
llm_chat_agent_cli.py            主程序：HTTP、窗口、循环、记忆
selftest-pipeline.py             离线自检：两条路径是不是都走了召回
tools/                           一个工具一个 .py
  _fs_guard.py                   文件工具的公共护栏（出界判定 + 保护名单）
skills/                          一个技能一个目录 + SKILL.md
  memory-audit/                  记忆巡检流程
  file-work/                     文件读写流程
```

## 跑起来

1. `python -X utf8 llm_chat_agent_cli.py`（Python 3.8+，无第三方依赖）
2. **首次运行会自动生成 `llm_chat_agent_cli_config.txt`**：里面有全部可调项和默认值，但 `API_KEY` 还是空的，程序会停下并提示填 key
3. 把 key 填进 `API_KEY=`（或改用环境变量 `DASHSCOPE_API_KEY`），再运行一次就能对话
4. 配置文件不进仓库：`.gitignore` 已经把 `*_config.txt` 排除掉
5. `python -X utf8 selftest-pipeline.py` 跑离线自检：不联网、不烧 token，只验装配链

常见命令：`/help` `/tools` `/skills` `/trace` `/profile` `/fs` `/agent on|off`

## 工具

| 工具 | 作用 |
|---|---|
`get_profile` | 读结构化档案里的生效事实
`list_archive` | 列归档日期与段数
`recall_archive(query)` | 按字符二元组检索归档片段
`read_archive(date, offset)` | 读某天归档原文，可分页
`save_fact(content, topic)` | 写一条稳定事实（同槽位覆盖并留痕）
`read_file(path, offset, limit)` | 读工作目录内文本；传目录则列清单
`write_file(path, content, mode)` | 写工作目录内文件，默认逐次询问
`load_skill(name)` | 取某个技能的流程正文

## 档案为什么不会自相矛盾

冲突检测原来只认 `topic` 一致，模型把同一个意思换个主题词，正反两条就会同时生效。
现在有这三层：

1. **主题词归一**（`TOPIC_CANON`）：`文件操作偏好` / `文件` / `写文件` 都收敛到 `文件操作`，
   槽位是封闭集合，抽取 prompt 里也只给这张表；`偏好`、`偏好设置` 这类垃圾桶词按内容反推槽位
2. **正反翻转**（`POLARITY_CHECK` + `POLARITY_SIMILARITY`）：剥掉否定词后字面几乎相同、
   极性相反的两条，不论 topic 是否对齐都算冲突，以 `updated_at` 晚的一条为准
3. **抽取口径**：只记用户明确表态过的稳定事实；用户提问、列举备选、助手的建议方案一律不记，
   否定式不许改写成肯定句

排查历史数据用 `/profile check`，会列出生效条目里涉嫌正反冲突的对子，再 `/profile del <id>` 停用。

## 上下文装配只有一条路

曾经有一个坑：Agent 模式自己拼 `messages`，档案和召回都在 `build_messages` 里，
于是"单步有召回、Agent 没有"，功能都写了但没接线，只看代码很难发现。

现在两条路径都调 `Chat.assemble_context()`，顺序固定：

1. L3 档案块（进 system，同时作为召回决策的输入）
2. L2 召回（`fixed` 直接查；`auto` 先让模型答一次决策）
3. system 拼装（顺便告诉模型"这轮已经注入过片段"）
4. 本轮 user 正文（召回片段包在里面，不写进 L1 历史）

`AGENT_AUTO_RECALL=true`（默认）时 Agent 模式和单步模式一视同仁。
关掉（或 `/agent recall off`）就只剩模型自己调 `recall_archive`，少一次决策请求，
代价是"模型没想到就不会查"。`/trace` 会打出本轮召回来源：`auto` / `fixed` / `skip` / `agent-off`。

## 安全边界（写在代码里，不写在提示词里）

- 文件工具只能碰 `FS_ROOT`（默认脚本同级 `workspace/`），`..`、绝对路径、外指软链一律拒绝
- 配置、主程序、`tools/`、`skills/`、`memory/` 是保护名单：**无论 `FS_ROOT` 怎么配都禁读禁写**
- 写文件默认 `FS_WRITE_MODE=ask`，命令行打印"改哪个文件、多大、新旧开头"，敲 `y` 才写
- 覆盖前备份到 `FS_ROOT/.backups/`，写入走"临时文件 + 原子替换"
- 扩展名白名单，不给可执行文件留口子；没有删除、重命名工具

## 已知代价

- 一轮 4~9 次请求（每步都要重发历史 + 工具 schema）；Agent 模式还要多一次召回决策
- 工具轨迹不进下一轮 `history`，模型看不到"上轮查过什么"（本轮内 tool 消息是完整的）
- 自动召回 + 模型再调 `recall_archive` 可能拿到重复片段，system 里已提示不必重复检索
- 工作目录内的明文会被读到并在回答里复述，密钥别放进去

## 许可

GNU General Public License v3.0 或更新版本（GPL-3.0-or-later），全文见 `LICENSE`。

分发或修改后再发布时，须同样以 GPL 开源并提供源码；不提供担保。
