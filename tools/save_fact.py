"""save_fact：把一条稳定事实写进长期档案（L3）。"""

NAME = "save_fact"
DESCRIPTION = ("把一条'关于用户本人、跨任务可复用'的稳定事实写进长期档案。"
               "topic 要复用已有分类；同一 topic 的新事实会覆盖旧事实并留痕。")
PARAMETERS = {
    "type": "object",
    "properties": {
        "content": {"type": "string",
                    "description": "一句完整陈述句（带主语），如"
                                   "'用户主力使用 C 和 Python'；不要只写名词片段"},
        "topic": {"type": "string", "description": "2~4 字分类名，如 职业 / 技术栈"},
        "confidence": {"type": "number", "description": "0~1，默认 0.8"},
    },
    "required": ["content", "topic"],
    "additionalProperties": False,
}


def run(store, args, ctx=None):
    content = (args.get("content") or "").strip()
    topic = (args.get("topic") or "").strip()
    if not content:
        return "[error] content is empty"
    result = store.add_fact(content, topic=topic,
                            confidence=float(args.get("confidence") or 0.8),
                            source="agent tool")
    return "[save] %s (%s)" % (content, result)
