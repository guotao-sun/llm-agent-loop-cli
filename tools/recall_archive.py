"""recall_archive：按关键词从归档里检索最相关的几段原文。"""

NAME = "recall_archive"
DESCRIPTION = ("按关键词从归档里检索最相关的几段原文。适合找'上次说过什么'。"
               "检索是字面匹配，query 用具体名词（如 RK3568 烧录），不要整句。")
PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "2~4 个具体名词，别写整句"},
        "max_blocks": {"type": "integer", "description": "最多返回几段，默认 2"},
    },
    "required": ["query"],
    "additionalProperties": False,
}


def run(store, args, ctx=None):
    query = (args.get("query") or "").strip()
    if not query:
        return "[error] query is empty"
    blocks = int(args.get("max_blocks") or 2)
    out = store.recall(query, max_blocks=blocks, max_chars=600, min_score=0.35)
    return out or "(no block above threshold for %r)" % query
