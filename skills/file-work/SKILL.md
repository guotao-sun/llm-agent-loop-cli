---
name: file-work
description: 文件读写流程：先探路再读片段、写前先看原文、写后回读校验
---

# 文件读写

用在"把某段内容存成文件""看看工作目录里有什么""改一下这个文件"这类任务上。

## 一、先探路，别猜文件名

1. `read_file(".")` 列工作目录。
2. 需要子目录就 `read_file("src/")`，它在目录上一律返回清单而不是内容。
3. 没有目标文件才谈"新建"；有同名文件就别新建，改。

## 二、读大文件要分页

`read_file(path, offset, limit)` 默认只给 2000 字。先看返回头部的 `chars a-b of total`：

- `total` 小于 2000：一次读完。
- `total` 几万：按 offset 往后翻，只取和任务相关的那段，别把整文件灌进上下文。
- 看到 `file larger than ... only head kept`：文件超了 `FS_READ_MAX_BYTES`，后面的部分这次读不到，得换更小的 path 或让用户拆文件。

## 三、写之前必须先读

覆盖是破坏性操作。`write_file` 前至少做一次：

1. `read_file(path)` 看原内容；
2. 判断是"整体重写"还是"只加一段"；
3. 整体重写用 `mode=overwrite`，加内容用 `mode=append`。

原文件有值、而新内容会丢掉原有信息时，先问用户，不要直接覆盖。

## 四、确认与留痕

- 默认 `FS_WRITE_MODE=ask`：命令行会打印"改哪个文件、多少字、原来多大、新旧开头"，等用户敲 `y` 才写。
- 被拒绝（`[denied]`）就停手，不要换路径重试，也不要把同一内容拆成多次写入来绕过。
- 覆盖会先备份到 `.backups/`，失败时告诉用户备份名。

## 五、写完回读一次

`read_file(path, offset=0, limit=200)` 确认落盘内容正确（尤其编码、行尾）。返回给用户时只报：

```
path=... bytes=... mode=... backup=...
```

## 六、边界（代码已经拦，不要试）

- 只能写 `FS_ROOT` 之内，`..`、绝对路径、指向外面的符号链接会被 `PermissionError` 拒绝。
- 扩展名白名单（默认 md/txt/json/py/csv/log/html/yml/yaml）；`.exe`、`.bat`、`.ps1` 一律拒绝。
- 单次写入有字符上限 `FS_WRITE_MAX_CHARS`；大文件应分段追加而不是一次塞爆。
- 不要读 `memory/` 之外的私有目录，也不要试图用 `read_file` 去读系统文件——出界请求同样是拒绝。
