"""save_fact：把一条稳定事实写进长期档案（L3）。"""

NAME = "save_fact"
DESCRIPTION = ("把一条'关于用户本人、跨任务可复用'的稳定事实写进长期档案。"
               "topic 要从固定槽位里选（职业 / 技术栈 / 回复语言 / 回复风格 / 文件操作 / 饮食 /"
               "项目路径 / 健康 / 学习 / 设备 / 家庭），同槽位的新事实覆盖旧事实并留痕；"
               "字面只差否定词的两条也算冲突，以新的一条为准。"
               "只在用户明确表态过时才写，用户提问或你在建议方案时不要写。")
PARAMETERS = {
    "type": "object",
    "properties": {
        "content": {"type": "string",
                    "description": "一句完整陈述句（带主语），如"
                                   "'用户主力使用 C 和 Python'；不要只写名词片段；"
                                   "否定要保留否定词，不要改写成肯定"},
        "topic": {"type": "string", "description": "固定槽位名，如 职业 / 技术栈 / 文件操作"},
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
