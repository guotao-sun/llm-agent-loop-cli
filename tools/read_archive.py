"""read_archive：读某一天归档的原文，支持 offset 分页。"""
import os
import time

NAME = "read_archive"
DESCRIPTION = "读取某一天归档的原文（可分页）。recall 命中但信息不全时，再用它看上下文。"
PARAMETERS = {
    "type": "object",
    "properties": {
        "date": {"type": "string", "description": "YYYY-MM-DD，默认今天"},
        "offset": {"type": "integer", "description": "从第几个字符开始，默认 0"},
    },
    "required": [],
    "additionalProperties": False,
}


def run(store, args, ctx=None):
    date = (args.get("date") or "").strip() or time.strftime("%Y-%m-%d")
    offset = max(0, int(args.get("offset") or 0))
    path = os.path.join(store.archive_dir, "%s.md" % date)
    if not os.path.exists(path):
        avail = [n[:-3] for n in sorted(os.listdir(store.archive_dir), reverse=True)
                 if n.endswith(".md")][:10]
        return "(no archive for %s; available: %s)" % (date, ", ".join(avail) or "none")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    piece = text[offset:]
    if not piece:
        return "(end of %s, total %d chars)" % (date, len(text))
    return "[%s chars %d-%d of %d]\n%s" % (date, offset, offset + len(piece), len(text), piece)
