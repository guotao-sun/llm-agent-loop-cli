"""write_file：把文本写进工作目录，默认每次写入前要用户点头。"""
import os
import shutil
import time

from . import _fs_guard as guard

NAME = "write_file"
DESCRIPTION = ("把文本写进工作目录里的文件（新建 / 覆盖 / 追加）。只能写工作目录之内，"
               "扩展名受白名单限制，默认每次写入前要用户确认。"
               "覆盖前建议先用 read_file 看一眼原内容，别把别人的东西冲掉。")
PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "相对工作目录的路径，如 notes.md"},
        "content": {"type": "string", "description": "要写入的完整文本"},
        "mode": {"type": "string", "enum": ["overwrite", "append"],
                 "description": "overwrite=整体替换（默认），append=追加到末尾"},
    },
    "required": ["path", "content"],
    "additionalProperties": False,
}


def run(store, args, ctx=None):
    if args.get("content") is None:
        return "[error] content is missing"
    content = str(args.get("content"))
    cap = int(guard.cfg_get(ctx, "FS_WRITE_MAX_CHARS", str(guard.DEFAULT_WRITE_MAX_CHARS)))
    if len(content) > cap:
        return "[error] content too long: %d chars, cap %d (FS_WRITE_MAX_CHARS)" % (len(content), cap)

    mode = (args.get("mode") or "overwrite").strip().lower()
    if mode not in ("overwrite", "append"):
        return "[error] mode must be overwrite or append"

    try:
        full, root = guard.resolve(ctx, args.get("path"))
    except Exception as e:
        return "[error] %s: %s" % (type(e).__name__, e)
    if os.path.isdir(full):
        return "[error] path is a directory: %s" % guard.rel(ctx, full)
    name = guard.rel(ctx, full)

    # 扩展名白名单：防止模型顺手写出 .exe / .bat / .ps1 这类可执行物
    exts = [e.strip().lower() for e in
            guard.cfg_get(ctx, "FS_WRITE_EXTS", guard.DEFAULT_EXTS).split(",") if e.strip()]
    ext = os.path.splitext(full)[1].lower()
    if exts and ext not in exts:
        return "[error] extension %r not allowed (FS_WRITE_EXTS=%s)" % (ext or "(none)", ",".join(exts))

    wmode = guard.cfg_get(ctx, "FS_WRITE_MODE", "ask").strip().lower()
    if wmode == "deny":
        return "[error] writing disabled by config (FS_WRITE_MODE=deny)"

    exists = os.path.isfile(full)
    old_size = os.path.getsize(full) if exists else 0

    # 写入前先让人看一眼：改哪个文件、多大、开头内容
    if wmode == "ask":
        print("[fs] write %s (mode=%s, %d chars, existing %d bytes)"
              % (name, mode, len(content), old_size))
        if exists:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                print("[fs] current head:", f.read(120).replace("\n", " "))
        print("[fs] new head    :", content[:120].replace("\n", " "))
        try:
            answer = input("[fs] confirm write? [y/N] ").strip().lower()
        except EOFError:
            return "[denied] no confirmation available (stdin closed); write refused"
        if answer not in ("y", "yes", "ok"):
            return "[denied] user rejected writing to %s" % name

    # 覆盖前留备份，误写还能捞回来
    backup = ""
    if exists and guard.cfg_bool(ctx, "FS_BACKUP", True):
        bdir = os.path.join(root, ".backups")
        os.makedirs(bdir, exist_ok=True)
        backup = os.path.join(bdir, "%s.%s.bak"
                              % (name.replace("/", "__"), time.strftime("%Y%m%d_%H%M%S")))
        shutil.copy2(full, backup)

    parent = os.path.dirname(full)
    if parent:
        os.makedirs(parent, exist_ok=True)

    data = content.encode("utf-8")
    if mode == "append" and exists:
        with open(full, "ab") as f:
            f.write(data)
    else:
        tmp = full + ".tmp-%d" % os.getpid()
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, full)

    return "[write] ok path=%s mode=%s bytes=%d%s" % (
        name, mode, len(data),
        "; backup=.backups/%s" % os.path.basename(backup) if backup else "")
