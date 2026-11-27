#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2026 guotao-sun
# 本程序按 GNU GPL v3.0 或更新版本发布，全文见 LICENSE；无任何担保。
"""
离线自检：确认"单步请求"和"Agent Loop"走的是同一条上下文装配链。

为什么要这个脚本：
    之前 Agent 模式自己拼 messages，绕过了 build_messages 里的档案 + 召回，
    功能都在，但不接线。光看代码很难发现，跑一次对话也要烧 token。

这里不联网：decide_recall 和流式请求全部换成假函数，只检查装配结果。
覆盖 4 件事：
    1. Agent 模式确实调用了一次召回决策
    2. 召回片段确实写进了发给模型的 user 内容
    3. AGENT_AUTO_RECALL=false 时确实一次决策都不发
    4. 上一轮的召回不会串到下一轮（need_recall=false 时必须清空）

用法：
    python -X utf8 selftest-pipeline.py
    退出码 0 = 全部通过，1 = 有用例失败
"""

import copy
import importlib.util
import json
import os
import shutil
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_NAME = "selftest-pipeline_config.txt"
CONFIG_PATH = os.path.join(SCRIPT_DIR, CONFIG_NAME)

DEFAULT_CONFIG = """# self-test config, empty value = default
# repo to check (empty = the folder this script sits in)
REPO_DIR=
# keep the temp memory dir after the run (true helps debugging, false cleans up)
KEEP_TEMP=false
"""


def ensure_config():
    if os.path.exists(CONFIG_PATH):
        return
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG)
    print("[config] template created:", CONFIG_PATH)
    print("[config] defaults are usable, this run continues")


def load_config():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                cfg[key.strip()] = value.strip()
    return cfg


def load_module(repo_dir):
    path = os.path.join(repo_dir, "llm_chat_agent_cli.py")
    if not os.path.exists(path):
        raise SystemExit("[error] main script not found: %s" % path)
    spec = importlib.util.spec_from_file_location("llm_chat_agent_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- 测试脚手架

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    print("[%s] %s%s" % ("PASS" if cond else "FAIL", name,
                        ("  (%s)" % detail) if detail and not cond else ""))


class Recorder(object):
    """记下这次自检里发生了什么：决策了几次、发出去的 body 长什么样。"""

    def __init__(self):
        self.decide_calls = 0
        self.bodies = []
        self.replies = []


def make_chat(mod, rec, agent_mode=True, auto_recall=True, decision=None):
    tmp = tempfile.mkdtemp(prefix="agent-loop-selftest-")
    cfg = {
        "MEMORY_DIR": tmp,
        "FS_ROOT": tmp,
        "MODEL": "fake-model",
        "EXTRACT_MODEL": "fake-model",
        "SHOW_USAGE": "false",
        "PACKET_LOG": "false",
        "EXTRACT_MEMORY": "false",
        "AGENT_MODE": "true" if agent_mode else "false",
        "AGENT_AUTO_RECALL": "true" if auto_recall else "false",
        "RECALL_MODE": "auto",
    }
    store = mod.MemoryStore(cfg)
    # 预置一条归档，让召回有东西可命中
    store.append_turn("RK3568 烧录固件总是失败", "先确认串口和波特率，再查启动日志")

    tools = [{"type": "function",
              "function": {"name": "recall_archive", "description": "fake tool",
                           "parameters": {"type": "object", "properties": {}}}}]
    chat = mod.Chat(cfg, "fake-key", store, tools,
                    lambda *a: ("[fake tool]", "?"), [], tmp, [])

    # 把召回决策换成假的，记录调用次数
    default = {"need_recall": True, "level": "L2", "query": "RK3568 烧录",
               "reason": "selftest"}

    def fake_decide(cfg_, key, question, profile_text, digest):
        rec.decide_calls += 1
        return (decision if decision is not None else default), {}

    mod.decide_recall = fake_decide

    # 把出网请求换成假的，只把 body 存下来。
    # 必须深拷贝：body["messages"] 就是循环里那份 msgs，轮内刷新 system 会就地改它，
    # 存引用会把"改之前"的历史一起改掉，断言就失真了。
    def fake_step(body):
        rec.bodies.append(copy.deepcopy(body))
        return "ok", []

    def fake_stream(body):
        rec.bodies.append(copy.deepcopy(body))
        return "ok"

    chat._stream_step = fake_step
    chat._stream = fake_stream
    return tmp, chat, store, rec


def last_user_content(body):
    for msg in reversed(body["messages"]):
        if msg["role"] == "user":
            return msg["content"]
    return ""


def run_case(mod, name, agent_mode=True, auto_recall=True, question="where did we fail"):
    rec = Recorder()
    tmp, chat, store, _ = make_chat(mod, rec, agent_mode, auto_recall)
    try:
        chat.send_turn(question)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check("%s: decide called once" % name, rec.decide_calls == 1,
          "decide_calls=%d" % rec.decide_calls)
    body = rec.bodies[-1] if rec.bodies else {"messages": []}
    user = last_user_content(body)
    check("%s: recall injected into user message" % name,
          "【历史片段参考】" in user, "user=%r" % user[:80])
    check("%s: recall content reaches model" % name, "RK3568" in user,
          "user=%r" % user[:80])
    return chat


def main():
    ensure_config()
    cfg = load_config()
    repo_dir = cfg.get("REPO_DIR") or SCRIPT_DIR
    keep_temp = str(cfg.get("KEEP_TEMP", "false")).lower() in ("1", "true", "yes", "on")

    print("[selftest] repo:", repo_dir)
    mod = load_module(repo_dir)

    # 1) Agent 模式必须走召回
    run_case(mod, "agent", agent_mode=True, auto_recall=True,
             question="RK3568 烧录那次是怎么解决的")

    # 2) 单步模式作为基准，行为应一致
    run_case(mod, "single", agent_mode=False, auto_recall=False,
             question="RK3568 烧录那次是怎么解决的")

    # 3) 显式关掉时，一次决策都不该发
    rec = Recorder()
    tmp, chat, store, _ = make_chat(mod, rec, agent_mode=True, auto_recall=False)
    try:
        chat.send_turn("RK3568 烧录那次是怎么解决的")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check("agent-off: no decide request", rec.decide_calls == 0,
          "decide_calls=%d" % rec.decide_calls)
    body = rec.bodies[-1] if rec.bodies else {"messages": []}
    user = last_user_content(body)
    check("agent-off: no recall block", "【历史片段参考】" not in user)

    # 4) 上一轮的召回不能串到下一轮
    rec = Recorder()
    tmp, chat, store, rec2 = make_chat(mod, rec, agent_mode=True, auto_recall=True)
    state = {"n": 0}

    def fake_decide2(cfg_, key, question, profile_text, digest):
        state["n"] += 1
        if state["n"] == 1:
            return ({"need_recall": True, "level": "L2", "query": "RK3568 烧录",
                     "reason": "selftest"}, {})
        return ({"need_recall": False, "level": "L2", "query": "",
                 "reason": "no history needed"}, {})

    # 必须在第一轮之前替换，否则第一轮用的还是 make_chat 里的默认假函数
    mod.decide_recall = fake_decide2
    try:
        chat.send_turn("RK3568 烧录那次是怎么解决的")
        first_recall = chat.last_recall
        # 第二轮换成明确不需要召回的问题
        chat.send_turn("1 加 1 等于几")
        body = rec.bodies[-1]
        user = last_user_content(body)
        check("no-carry-over: last_recall cleared", chat.last_recall == "",
              "last_recall=%r" % chat.last_recall[:60])
        check("no-carry-over: first turn did recall", bool(first_recall))
        check("no-carry-over: second user has no recall block",
              "【历史片段参考】" not in user)
    finally:
        if keep_temp:
            print("[selftest] temp kept:", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    # 5) 轮内写过档案，下一步的 system 必须刷新
    rec = Recorder()
    tmp, chat, store, rec2 = make_chat(mod, rec, agent_mode=True, auto_recall=False)

    def real_save(store_, name, args, cap, ctx):
        if name == "save_fact":
            data = json.loads(args)
            outcome = store_.add_fact(data.get("content", ""), topic=data.get("topic", ""),
                                      confidence=0.9, source="selftest")
            return "[save] %s (%s)" % (data.get("content", ""), outcome), "?"
        return "[fake tool]", "?"

    chat.run_tool = real_save

    steps = {"n": 0}

    def scripted_step(body):
        rec.bodies.append(copy.deepcopy(body))
        steps["n"] += 1
        if steps["n"] == 1:
            # 第一步：模型决定写一条事实
            return "", [{"id": "c1", "name": "save_fact",
                         "args": json.dumps({"content": "用户主力使用 RK3568",
                                             "topic": "设备", "confidence": 0.9},
                                            ensure_ascii=False)}]
        return "done", []

    chat._stream_step = scripted_step
    try:
        chat.send_turn("记住我用 RK3568")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    first_system = rec.bodies[0]["messages"][0]["content"]
    second_system = rec.bodies[1]["messages"][0]["content"]
    check("mid-turn refresh: first step has no fact",
          "用户主力使用 RK3568" not in first_system)
    check("mid-turn refresh: second step sees new fact",
          "用户主力使用 RK3568" in second_system)

    failed = [c for c in CHECKS if not c[1]]
    print("-" * 60)
    print("[selftest] %d passed, %d failed" % (len(CHECKS) - len(failed), len(failed)))
    for name, _, detail in failed:
        print("[selftest] FAILED:", name, detail)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
