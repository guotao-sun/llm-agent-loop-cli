"""list_archive：看归档（L2）有哪些日期、每天几段。"""
import os

NAME = "list_archive"
DESCRIPTION = "列出归档里有哪些日期、每天存了几段对话。不确定该查哪天时先调它。"
PARAMETERS = {"type": "object", "properties": {}, "additionalProperties": False}


def run(store, args, ctx=None):
    if not os.path.isdir(store.archive_dir):
        return "(archive empty)"
    rows = []
    for name in sorted(os.listdir(store.archive_dir), reverse=True):
        if not name.endswith(".md"):
            continue
        path = os.path.join(store.archive_dir, name)
        with open(path, "r", encoding="utf-8") as f:
            n = f.read().count("### ")
        rows.append("%s  %d block(s)" % (name[:-3], n))
    return "\n".join(rows) or "(archive empty)"
