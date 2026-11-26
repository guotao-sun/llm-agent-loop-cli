"""工具包：一个工具一个文件，这里只做汇总和分发。

模型不会执行这里的任何代码。它只在响应里给出 name + arguments，
真正去调用 run(store, args, ctx) 的是主脚本里的循环（Agent Loop）。

加一个工具 = 在 tools/ 下新建 xxx.py（写 NAME / DESCRIPTION / PARAMETERS / run），
再把文件名加进下面的 MODULES。
"""
import importlib
import json
import os
import sys

MODULES = [
    "get_profile",
    "list_archive",
    "recall_archive",
    "read_archive",
    "save_fact",
    "read_file",
    "write_file",
    "load_skill",
]


def _import(name):
    # 让本目录的上级目录进 sys.path，这样既能当包导入，也能单独拷出去用
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module("%s.%s" % (os.path.basename(here), name))


def _build():
    tools, impl = [], {}
    for name in MODULES:
        try:
            mod = _import(name)
        except Exception as e:
            # 单个工具写坏了不该拖垮整个程序，跳过并提示
            print("[tools] skip %s: %s" % (name, e))
            continue
        tools.append({"type": "function", "function": {
            "name": mod.NAME,
            "description": mod.DESCRIPTION,
            "parameters": mod.PARAMETERS,
        }})
        impl[mod.NAME] = mod.run
    return tools, impl


TOOLS, TOOL_IMPL = _build()


def run_tool(store, name, args_text, max_chars, ctx=None):
    """执行一次工具调用。任何异常都转成文本回给模型，不让整个循环崩掉。"""
    fn = TOOL_IMPL.get(name)
    if not fn:
        return "[error] unknown tool: %s" % name, "?"
    try:
        args = json.loads(args_text) if (args_text or "").strip() else {}
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except Exception as e:
        return "[error] bad arguments: %s" % e, "?"
    try:
        out = fn(store, args, ctx)
    except Exception as e:
        out = "[error] %s: %s" % (type(e).__name__, e)
    if len(out) > max_chars:
        out = out[:max_chars] + "\n...(truncated, %d chars total)" % len(out)
    return out, json.dumps(args, ensure_ascii=False, sort_keys=True)
