"""技能包：把"流程性知识"写成 markdown，按需加载。

和 tools/ 的分工：
- tools/   → 原子动作（函数）。模型用 function calling 点单，脚本执行，返回数据。
- skills/  → 做事的方法（步骤、检查项、坑）。目录里只放名字+一句话说明，
             模型觉得需要时用 load_skill 取正文，正文只在这时候才进上下文。

目录约定：skills/<技能名>/SKILL.md，文件开头用 --- 包一段元信息。
"""
import os

META_KEYS = ("name", "description")


def _parse(path):
    """拆出 --- 之间的元信息和正文。没有元信息就把整个文件当正文，名字用目录名。"""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    meta, body = {}, text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                if key.strip() in META_KEYS:
                    meta[key.strip()] = value.strip()
            body = parts[2].lstrip("\n")
    return meta, body


def load_skills(skills_dir):
    """扫一遍目录，返回 [{name, description, body, path}]。坏文件跳过，不拖垮主程序。"""
    if not os.path.isdir(skills_dir):
        return []
    found = []
    for entry in sorted(os.listdir(skills_dir)):
        path = os.path.join(skills_dir, entry)
        if os.path.isdir(path):
            path = os.path.join(path, "SKILL.md")
        if not path.endswith(".md") or not os.path.isfile(path):
            continue
        try:
            meta, body = _parse(path)
        except Exception as e:
            print("[skills] skip %s: %s" % (entry, e))
            continue
        if os.path.basename(path) == "SKILL.md":
            default_name = os.path.basename(os.path.dirname(path))   # skills/<名>/SKILL.md
        else:
            default_name = os.path.splitext(entry)[0]                 # skills/<名>.md
        name = meta.get("name") or default_name
        found.append({
            "name": name,
            "description": meta.get("description", ""),
            "body": body,
            "path": path,
        })
    return found
