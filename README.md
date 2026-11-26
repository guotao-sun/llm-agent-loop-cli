# LLM Agent Loop Demo（纯标准库）

和大模型 API 打交道的最小实验：从"一次请求一个回答"走到"多步调工具"，
全程只用 `urllib`，不装 `openai` 这类 SDK，一行一行看清楚线上发生了什么。

## 它做了什么

一次提问不再等于一次请求。模型可以连续多步：先取技能流程，再查档案，
再写文件，最后收尾。每一步都是一次独立的 HTTP 请求，脚本负责执行工具、
把结果拼回 `messages`、再发下一次。

- 三层记忆：`messages` 窗口 / 按天归档 / 结构化档案（同 topic 覆盖留痕）
- 召回决策：每轮先让模型答一次 `{need_recall, level, query}`，需要才查
- 工具调用：8 个工具，模型只出 `name + arguments`，执行在本地
- 技能：`skills/<name>/SKILL.md`，平时只列名字，正文按需 `load_skill`
- 报文日志：每次出网请求存一份到 `logs/`，看得出这轮发了几次

## 目录

```
llm_chat_agent_cli.py            主程序：HTTP、窗口、循环、记忆
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

常见命令：`/help` `/tools` `/skills` `/trace` `/profile` `/fs` `/agent on|off`

## 工具

| 工具 | 作用 |
|---|---|
`get_profile` | 读结构化档案里的生效事实 |
`list_archive` | 列归档日期与段数 |
`recall_archive(query)` | 按字符二元组检索归档片段 |
`read_archive(date, offset)` | 读某天归档原文，可分页 |
`save_fact(content, topic)` | 写一条稳定事实（同 topic 覆盖并留痕） |
`read_file(path, offset, limit)` | 读工作目录内文本；传目录则列清单 |
`write_file(path, content, mode)` | 写工作目录内文件，默认逐次询问 |
`load_skill(name)` | 取某个技能的流程正文 |

## 安全边界（写在代码里，不写在提示词里）

- 文件工具只能碰 `FS_ROOT`（默认脚本同级 `workspace/`），`..`、绝对路径、外指软链一律拒绝
- 配置、主程序、`tools/`、`skills/`、`memory/` 是保护名单：**无论 `FS_ROOT` 怎么配都禁读禁写**
- 写文件默认 `FS_WRITE_MODE=ask`，命令行打印"改哪个文件、多大、新旧开头"，敲 `y` 才写
- 覆盖前备份到 `FS_ROOT/.backups/`，写入走"临时文件 + 原子替换"
- 扩展名白名单，不给可执行文件留口子；没有删除、重命名工具

## 已知代价

- 一轮 4~9 次请求（每步都要重发历史 + 工具 schema）
- 工具轨迹不进下一轮 `history`，模型看不到"上轮查过什么"
- 工作目录内的明文会被读到并在回答里复述，密钥别放进去

## 许可

GNU General Public License v3.0 或更新版本（GPL-3.0-or-later），全文见 `LICENSE`。

分发或修改后再发布时，须同样以 GPL 开源并提供源码；不提供担保。
