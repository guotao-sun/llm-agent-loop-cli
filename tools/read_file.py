"""read_file：读工作目录里的文本文件，支持分页；传目录则列清单。"""
import os

from . import _fs_guard as guard

NAME = "read_file"
DESCRIPTION = ("读取工作目录里的一个文本文件（可分页）。path 只写相对路径，如 notes.md；"
               "传目录则列出里面有哪些文件。只读工作目录之内，出界会被拒绝。"
               "文件大时先看长度再用 offset/limit 取片段，不要整文件读。")
PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "相对工作目录的路径，如 notes.md 或 src/"},
        "offset": {"type": "integer", "description": "从第几个字符开始，默认 0"},
        "limit": {"type": "integer", "description": "本次最多返回多少字符，默认 2000"},
    },
    "required": ["path"],
    "additionalProperties": False,
}


def run(store, args, ctx=None):
    try:
        full, _root = guard.resolve(ctx, args.get("path"))
    except Exception as e:
        return "[error] %s: %s" % (type(e).__name__, e)

    # 目录 → 列清单（模型先探路再读，比盲猜文件名强）
    if os.path.isdir(full):
        rows = []
        for name in sorted(os.listdir(full)):
            sub = os.path.join(full, name)
            if os.path.isdir(sub):
                rows.append("%s/  (dir)" % name)
            else:
                rows.append("%s  %d bytes" % (name, os.path.getsize(sub)))
        return "[dir %s] %d entrie(s)\n%s" % (
            guard.rel(ctx, full) or ".", len(rows), "\n".join(rows[:200]) or "(empty)")

    if not os.path.isfile(full):
        return "(no file: %s)" % guard.rel(ctx, full)

    cap = int(guard.cfg_get(ctx, "FS_READ_MAX_BYTES", str(guard.DEFAULT_READ_MAX_BYTES)))
    with open(full, "rb") as f:
        raw = f.read(cap + 1)
    if b"\x00" in raw:
        return "[error] binary file, not supported"
    bigger = len(raw) > cap
    text = raw[:cap].decode("utf-8", "replace")
    offset = max(0, int(args.get("offset") or 0))
    limit = max(1, int(args.get("limit") or 2000))
    piece = text[offset:offset + limit]
    name = guard.rel(ctx, full)
    if not piece:
        return "(end of %s; %d chars read)" % (name, len(text))
    note = "; file larger than %d bytes, only head kept" % cap if bigger else ""
    return "[%s chars %d-%d of %d%s]\n%s" % (
        name, offset, offset + len(piece), len(text), note, piece)
