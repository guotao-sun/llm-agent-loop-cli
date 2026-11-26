"""文件工具的公共护栏。

原则：能不能出界、能不能覆盖，由代码判断，跟模型说了什么无关。
所有文件工具都必须先过 resolve()，不允许自己拼路径。
"""
import os

DEFAULT_READ_MAX_BYTES = 262144
DEFAULT_WRITE_MAX_CHARS = 20000
DEFAULT_EXTS = ".md,.txt,.json,.py,.csv,.log,.html,.yml,.yaml"


def cfg_get(ctx, key, default=""):
    cfg = (ctx or {}).get("cfg") or {}
    value = cfg.get(key, "")
    return value if value != "" else default


def cfg_bool(ctx, key, default=False):
    return str(cfg_get(ctx, key, "true" if default else "false")).lower() in (
        "1", "true", "yes", "on")


def fs_root(ctx):
    """工作目录：默认脚本同级 workspace/，也可以用 FS_ROOT 指到别处。"""
    root = (ctx or {}).get("fs_root") or cfg_get(ctx, "FS_ROOT", "") \
        or os.path.join(os.getcwd(), "workspace")
    root = os.path.abspath(root)
    os.makedirs(root, exist_ok=True)
    return os.path.realpath(root)


def check_protected(ctx, full):
    """保护名单：配置、主程序、tools/、skills/、memory/ 一律不许读写。

    这道判定和 FS_ROOT 无关——哪怕用户把 FS_ROOT 设成脚本目录、项目根甚至 C:\\，
    这些路径依然是禁区。没有它，模型只要写一次配置文件就能给自己提权。
    """
    for item in (ctx or {}).get("protected") or []:
        base = os.path.realpath(item)
        if full == base or full.startswith(base + os.sep):
            raise PermissionError("path is protected: %s" % item)


def resolve(ctx, path):
    """解析相对路径，返回 (真实绝对路径, 工作目录)。

    出界判定用 realpath：`..`、绝对路径、指到外面的符号链接，都在这一步被挡掉。
    再叠一层保护名单，挡住"工作目录里恰好放着配置/工具/记忆"的情况。
    """
    root = fs_root(ctx)
    raw = (path or "").strip().replace("\\", "/")
    if not raw:
        raise ValueError("path is empty")
    if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
        full = os.path.realpath(raw)
    else:
        full = os.path.realpath(os.path.join(root, raw))
    if full != root and not full.startswith(root + os.sep):
        raise PermissionError("path escapes workspace: %s" % path)
    check_protected(ctx, full)
    return full, root


def rel(ctx, full):
    """回给模型看的路径一律是相对路径，别暴露本机绝对路径。"""
    return os.path.relpath(full, fs_root(ctx)).replace("\\", "/")
